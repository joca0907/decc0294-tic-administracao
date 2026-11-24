"""
Modelo de Machine Learning para análise de turnover (RH)
DECC0294 - TIC Aplicada à Administração (UFMA)

O que faz:
- Lê a base de turnover em CSV (padrão: dados/rh_turnover_ficticio_2025_ptBR.csv)
- Filtra desligamentos com classificação funcional conhecida
- Treina uma regressão logística multinomial (gradiente descendente, stdlib)
- Separa treino/teste, compara com baseline e gera matriz de confusão
- Salva relatório em modelo/resultado-turnover-ml.md

Uso:
  py modelo_turnover_ml.py treinar
  py modelo_turnover_ml.py treinar dados/rh_turnover_ficticio_2025_ptBR.csv
  py modelo_turnover_ml.py prever '{"area":"Comercial","cargo":"Vendedor","gestor":"G_COM_01","unidade":"SLZ","vinculo":"CLT","tempo_casa_meses":4,"desempenho_avaliacao":"baixo"}'

Sem dependências externas. Reprodutível com semente fixa.
"""

from __future__ import annotations

import csv
import json
import math
import os
import random
import sys
from collections import Counter

SEMENTE = 42
PROPORCAO_TREINO = 0.7
LR = 0.15
EPOCAS = 1200
L2 = 0.01
BASE_PADRAO = os.path.join("dados", "rh_turnover_ficticio_2025_ptBR.csv")
PASTA_SAIDA = "modelo"
ARQUIVO_RESULTADO = os.path.join(PASTA_SAIDA, "resultado-turnover-ml.md")
ARQUIVO_MODELO = os.path.join(PASTA_SAIDA, "modelo_turnover.json")

CAMPOS_CATEGORICOS = ["area", "cargo", "gestor", "unidade", "vinculo", "desempenho_avaliacao"]
CAMPO_NUMERICO = "tempo_casa_meses"
ALVO = "classificacao_funcional"
CLASSES = ["disfuncional", "neutro", "funcional"]  # ordem fixa para relatório


def detectar_separador(caminho: str) -> str:
    with open(caminho, "r", encoding="utf-8-sig", errors="replace") as f:
        amostra = f.read(4096)
    contagens = {s: amostra.count(s) for s in [";", ",", "\t", "|"]}
    return max(contagens, key=contagens.get) or ","


def ler_csv(caminho: str) -> list[dict]:
    sep = detectar_separador(caminho)
    with open(caminho, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        return [dict(l) for l in csv.DictReader(f, delimiter=sep)]


def para_numero(valor) -> float | None:
    if valor is None:
        return None
    t = str(valor).strip().replace(",", ".")
    if t in ("", "NA", "N/A"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def preparar_linhas(linhas: list[dict]) -> list[dict]:
    base = []
    for l in linhas:
        if str(l.get("tipo_movimentacao", "")).strip().lower() != "desligamento":
            continue
        classe = str(l.get(ALVO, "")).strip().lower()
        if classe not in CLASSES:
            continue
        n = para_numero(l.get(CAMPO_NUMERICO))
        if n is None:
            continue
        item = {k: str(l.get(k, "")).strip() for k in CAMPOS_CATEGORICOS}
        item[CAMPO_NUMERICO] = float(n)
        item[ALVO] = classe
        base.append(item)
    return base


def construir_encoder(base: list[dict]) -> dict:
    categorias = {}
    for campo in CAMPOS_CATEGORICOS:
        vals = sorted({str(l[campo]) for l in base})
        categorias[campo] = {v: i for i, v in enumerate(vals)}
    tempos = [l[CAMPO_NUMERICO] for l in base]
    media = sum(tempos) / len(tempos)
    var = sum((t - media) ** 2 for t in tempos) / max(1, len(tempos))
    desvio = math.sqrt(var) or 1.0
    return {"categorias": categorias, "tempo_media": media, "tempo_desvio": desvio, "classes": CLASSES}


def vetorizar(item: dict, enc: dict) -> list[float]:
    x = [1.0]  # bias
    for campo in CAMPOS_CATEGORICOS:
        mapa = enc["categorias"][campo]
        onehot = [0.0] * len(mapa)
        val = str(item.get(campo, "")).strip()
        if val in mapa:
            onehot[mapa[val]] = 1.0
        x.extend(onehot)
    t = para_numero(item.get(CAMPO_NUMERICO))
    if t is None:
        t = enc["tempo_media"]
    x.append((t - enc["tempo_media"]) / enc["tempo_desvio"])
    return x


def softmax(logits: list[float]) -> list[float]:
    m = max(logits)
    exps = [math.exp(v - m) for v in logits]
    s = sum(exps)
    return [e / s for e in exps]


def prever_probs(x: list[float], pesos: list[list[float]]) -> list[float]:
    logits = [sum(wj * xj for wj, xj in zip(w, x)) for w in pesos]
    return softmax(logits)


def treinar_modelo(X: list[list[float]], y: list[int], n_classes: int) -> list[list[float]]:
    n, d = len(X), len(X[0])
    pesos = [[0.0] * d for _ in range(n_classes)]
    for ep in range(EPOCAS):
        # gradiente batch completo (base pequena, stdlib)
        grad = [[0.0] * d for _ in range(n_classes)]
        for xi, yi in zip(X, y):
            probs = prever_probs(xi, pesos)
            for k in range(n_classes):
                delta = (probs[k] - (1.0 if k == yi else 0.0)) / n
                gk = grad[k]
                for j in range(d):
                    gk[j] += delta * xi[j]
        lr = LR * (0.995 ** (ep // 50))
        for k in range(n_classes):
            for j in range(d):
                reg = L2 * pesos[k][j] if j != 0 else 0.0
                pesos[k][j] -= lr * (grad[k][j] + reg)
    return pesos


def acuracia(y_true: list[int], y_pred: list[int]) -> float:
    return sum(1 for a, b in zip(y_true, y_pred) if a == b) / max(1, len(y_true))


def matriz_confusao(y_true: list[int], y_pred: list[int], n: int) -> list[list[int]]:
    m = [[0] * n for _ in range(n)]
    for t, p in zip(y_true, y_pred):
        m[t][p] += 1
    return m


def macro_f1(y_true: list[int], y_pred: list[int], n: int) -> float:
    f1s = []
    for k in range(n):
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == k and p == k)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != k and p == k)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == k and p != k)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) else 0.0)
    return sum(f1s) / len(f1s)


def fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def split_treino_teste(base: list[dict]):
    rnd = random.Random(SEMENTE)
    idx = list(range(len(base)))
    rnd.shuffle(idx)
    corte = int(len(idx) * PROPORCAO_TREINO)
    treino = [base[i] for i in idx[:corte]]
    teste = [base[i] for i in idx[corte:]]
    # garante que teste não fique vazio
    if not teste and len(treino) > 1:
        teste = [treino.pop()]
    return treino, teste


def avaliar(pesos, enc, teste: list[dict]):
    X = [vetorizar(l, enc) for l in teste]
    y_true = [CLASSES.index(l[ALVO]) for l in teste]
    probs = [prever_probs(x, pesos) for x in X]
    y_pred = [max(range(len(p)), key=lambda i: p[i]) for p in probs]
    return y_true, y_pred, probs


def baseline_majoritaria(treino: list[dict], teste: list[dict]):
    maj = Counter(l[ALVO] for l in treino).most_common(1)[0][0]
    y_true = [CLASSES.index(l[ALVO]) for l in teste]
    y_pred = [CLASSES.index(maj)] * len(teste)
    return maj, y_true, y_pred


def salvar_modelo(pesos, enc, meta):
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    obj = {"enc": enc, "pesos": pesos, "meta": meta}
    with open(ARQUIVO_MODELO, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def carregar_modelo():
    with open(ARQUIVO_MODELO, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj["pesos"], obj["enc"], obj.get("meta", {})


def relatorio_md(caminho, enc, treino, teste, y_true, y_pred, maj, yb_true, yb_pred):
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    acc = acuracia(y_true, y_pred)
    acc_b = acuracia(yb_true, yb_pred)
    f1 = macro_f1(y_true, y_pred, len(CLASSES))
    f1_b = macro_f1(yb_true, yb_pred, len(CLASSES))
    cm = matriz_confusao(y_true, y_pred, len(CLASSES))
    ganho = acc - acc_b

    linhas = []
    a = linhas.append
    a("# Resultado — Modelo de ML para Turnover")
    a("")
    a("## Contexto")
    a(f"- Base: `{caminho}`")
    a(f"- Registros de desligamento usados: **{len(treino) + len(teste)}** (treino={len(treino)}, teste={len(teste)})")
    a(f"- Alvo: `{ALVO}` (classes: {', '.join(CLASSES)})")
    a(f"- Preditoras categóricas: {', '.join(CAMPOS_CATEGORICOS)}")
    a(f"- Preditora numérica: `{CAMPO_NUMERICO}` (padronizada por z-score)")
    a(f"- Modelo: regressão logística multinomial, gradiente descendente, L2={L2}, épocas={EPOCAS}, semente={SEMENTE}")
    a("")
    a("## Desempenho no teste")
    a("")
    a("| Métrica | Modelo | Baseline (classe majoritária) |")
    a("|---|---:|---:|")
    a(f"| Acurácia | {fmt_pct(acc)} | {fmt_pct(acc_b)} |")
    a(f"| Macro-F1 | {fmt_pct(f1)} | {fmt_pct(f1_b)} |")
    a(f"| Classe baseline | - | {maj} |")
    a("")
    a(f"**Ganho de acurácia sobre baseline:** {fmt_pct(ganho)}")
    a("")
    a("## Matriz de confusão (linha=real, coluna=previsto)")
    a("")
    header = "| real \\ previsto | " + " | ".join(CLASSES) + " |"
    sep = "|" + "|".join(["---"] * (len(CLASSES) + 1)) + "|"
    a(header)
    a(sep)
    for i, cls in enumerate(CLASSES):
        a("| " + cls + " | " + " | ".join(str(cm[i][j]) for j in range(len(CLASSES))) + " |")
    a("")
    a("## Leitura gerencial")
    a("")
    if ganho <= 0:
        a("- O modelo **não superou** o baseline. Com esta base pequena, isso indica sinal fraco ou variáveis insuficientes; usar previsão apenas como apoio exploratório.")
    elif ganho < 0.10:
        a("- O modelo superou o baseline por margem pequena. Há sinal, mas a incerteza é alta para decisão individual.")
    else:
        a("- O modelo superou o baseline por margem relevante para base pequena; ainda assim, decisões de RH exigem validação humana e política clara.")
    a("- A base tem apenas desligamentos rotulados e volume reduzido; resultados são **exploratórios**, não causais.")
    a("- Variáveis ausentes (salário, clima, liderança, absenteísmo) podem explicar grande parte do turnover.")
    a("- Antes de uso real: ampliar dados, validar temporalmente, avaliar viés por área/gestor e definir governança LGPD.")
    a("")
    a("## Limitações")
    a("- Base fictícia/pequena; sem validação externa.")
    a("- Classes possivelmente desbalanceadas; métricas podem variar por semente/split.")
    a("- Regressão logística captura relações lineares no espaço de features; não modela interações complexas sem engenharia de atributos.")
    a("")
    with open(ARQUIVO_RESULTADO, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    return acc, acc_b, f1, f1_b, ganho


def cmd_treinar(args):
    caminho = args[0] if args else BASE_PADRAO
    if not os.path.exists(caminho):
        print(f"Arquivo não encontrado: {caminho}")
        sys.exit(1)
    linhas = ler_csv(caminho)
    base = preparar_linhas(linhas)
    if len(base) < 12:
        print(f"Base insuficiente após filtro: {len(base)} registros. Preciso de desligamentos com {ALVO} válido.")
        sys.exit(1)
    faltantes = [c for c in CLASSES if c not in {l[ALVO] for l in base}]
    if faltantes:
        print(f"Classes ausentes na base filtrada: {faltantes}")
        sys.exit(1)

    treino, teste = split_treino_teste(base)
    enc = construir_encoder(treino)
    Xtr = [vetorizar(l, enc) for l in treino]
    ytr = [CLASSES.index(l[ALVO]) for l in treino]
    pesos = treinar_modelo(Xtr, ytr, len(CLASSES))

    y_true, y_pred, _ = avaliar(pesos, enc, teste)
    maj, yb_true, yb_pred = baseline_majoritaria(treino, teste)
    acc, acc_b, f1, f1_b, ganho = relatorio_md(caminho, enc, treino, teste, y_true, y_pred, maj, yb_true, yb_pred)

    meta = {
        "base": caminho, "n_treino": len(treino), "n_teste": len(teste),
        "acuracia": acc, "acuracia_baseline": acc_b, "macro_f1": f1, "ganho": ganho,
    }
    salvar_modelo(pesos, enc, meta)

    print("=" * 64)
    print("MODELO DE TURNOVER TREINADO")
    print("=" * 64)
    print(f"Base: {caminho}")
    print(f"Registros usados: {len(base)} (treino={len(treino)}, teste={len(teste)})")
    print(f"Classes: {', '.join(CLASSES)}")
    print()
    print(f"Acurácia modelo:   {fmt_pct(acc)}")
    print(f"Acurácia baseline: {fmt_pct(acc_b)} (sempre '{maj}')")
    print(f"Macro-F1 modelo:   {fmt_pct(f1)}")
    print(f"Ganho vs baseline: {fmt_pct(ganho)}")
    print()
    print(f"Relatório: {ARQUIVO_RESULTADO}")
    print(f"Modelo salvo: {ARQUIVO_MODELO}")
    if ganho <= 0:
        print("\nATENÇÃO: modelo não superou baseline. Tratar como exploratório.")


def cmd_prever(args):
    if not args:
        print("Uso: py modelo_turnover_ml.py prever '{...json...}'")
        sys.exit(1)
    if not os.path.exists(ARQUIVO_MODELO):
        print("Modelo não encontrado. Rode primeiro: py modelo_turnover_ml.py treinar")
        sys.exit(1)
    pesos, enc, meta = carregar_modelo()
    try:
        item = json.loads(args[0])
    except json.JSONDecodeError as e:
        print(f"JSON inválido: {e}")
        sys.exit(1)
    x = vetorizar(item, enc)
    probs = prever_probs(x, pesos)
    ordem = sorted(range(len(CLASSES)), key=lambda i: probs[i], reverse=True)
    print("Previsão de classificação funcional (desligamento):")
    for i in ordem:
        print(f"  {CLASSES[i]:<13} {fmt_pct(probs[i])}")
    print(f"\nClasse prevista: {CLASSES[ordem[0]]}")
    print("Observação: previsão probabilística baseada em base pequena; usar como apoio, não como decisão automática.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1].lower().strip()
    if cmd == "treinar":
        cmd_treinar(sys.argv[2:])
    elif cmd == "prever":
        cmd_prever(sys.argv[2:])
    else:
        print(f"Comando desconhecido: {cmd}")
        print("Comandos: treinar, prever")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
    except KeyboardInterrupt:
        print("\nInterrompido.")
