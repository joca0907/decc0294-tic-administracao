"""
Modelo de Machine Learning supervisionado - Rentabilidade de Filmes (versão simplificada)
DECC0294 - TIC Aplicada à Administração (UFMA)

Algoritmo: Regressão Logística Binária com pesos de classe, validação cruzada estratificada
e ajuste de limiar por F1.

Melhorias desta versão:
- Features simplificadas e pré-lançamento (menos risco de vazamento).
- Split estratificado + validação cruzada estratificada (k=5).
- Pesos de classe para lidar com desbalanceamento.
- Limiar recomendado escolhido por melhor F1 médio na CV.
- Métricas: acurácia, precisão, recall, F1, Brier score, matriz de confusão.
- Gera relatório Markdown e dashboard HTML.

Uso:
  py modelo_filmes_ml.py treinar
  py modelo_filmes_ml.py prever '{"genero_principal":"Acao","orcamento_milhoes":90,"franquia":1,"diretor_score_historico":7.8,"elenco_score_historico":7.5,"mes_lancamento":7,"competicao_janela":"Media","trailer_views_milhoes":30}'
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
K_FOLD = 5
LR = 0.08
EPOCAS = 2000
L2 = 0.02
BASE_PADRAO = os.path.join("dados", "filmes_simulados.csv")
PASTA_SAIDA = "modelo"
PASTA_DASH = "saidas"
ARQUIVO_RESULTADO = os.path.join(PASTA_SAIDA, "resultado-filmes-ml.md")
ARQUIVO_MODELO = os.path.join(PASTA_SAIDA, "modelo_filmes.json")
ARQUIVO_DASH = os.path.join(PASTA_DASH, "modelo-filmes-ml-dashboard.html")

ALVO = "rentavel"
# Simplificado: apenas sinais pré-lançamento claros, sem variáveis de decisão do estúdio
CAMPOS_CATEGORICOS = ["genero_principal", "competicao_janela"]
CAMPOS_NUMERICOS = [
    "orcamento_milhoes",
    "franquia",
    "diretor_score_historico",
    "elenco_score_historico",
    "mes_lancamento",
    "trailer_views_milhoes",
]


def detectar_separador(caminho: str) -> str:
    with open(caminho, "r", encoding="utf-8-sig", errors="replace") as f:
        amostra = f.read(4096)
    contagens = {s: amostra.count(s) for s in [";", ",", "\t", "|"]}
    return max(contagens, key=contagens.get) or ","


def ler_csv(caminho: str) -> list[dict]:
    sep = detectar_separador(caminho)
    with open(caminho, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        return [dict(l) for l in csv.DictReader(f, delimiter=sep)]


def para_numero(valor):
    if valor is None:
        return None
    t = str(valor).strip().replace(",", ".")
    if t in ("", "NA", "N/A", "nan", "None"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def preparar_linhas(linhas: list[dict]) -> list[dict]:
    base = []
    for l in linhas:
        y = para_numero(l.get(ALVO))
        if y not in (0, 1, 0.0, 1.0):
            continue
        item = {}
        ok = True
        for c in CAMPOS_CATEGORICOS:
            v = str(l.get(c, "")).strip()
            if v == "":
                ok = False
                break
            item[c] = v
        for c in CAMPOS_NUMERICOS:
            n = para_numero(l.get(c))
            if n is None:
                ok = False
                break
            item[c] = float(n)
        if not ok:
            continue
        item[ALVO] = int(y)
        base.append(item)
    return base


def construir_encoder(base: list[dict]) -> dict:
    categorias = {}
    for campo in CAMPOS_CATEGORICOS:
        vals = sorted({str(l[campo]) for l in base})
        categorias[campo] = {v: i for i, v in enumerate(vals)}
    stats = {}
    for campo in CAMPOS_NUMERICOS:
        vals = [float(l[campo]) for l in base]
        media = sum(vals) / len(vals)
        var = sum((v - media) ** 2 for v in vals) / max(1, len(vals))
        desvio = math.sqrt(var) or 1.0
        stats[campo] = {"media": media, "desvio": desvio}
    return {"categorias": categorias, "stats": stats, "campos_cat": CAMPOS_CATEGORICOS, "campos_num": CAMPOS_NUMERICOS}


def vetorizar(item: dict, enc: dict) -> list[float]:
    x = [1.0]
    for campo in enc["campos_cat"]:
        mapa = enc["categorias"][campo]
        onehot = [0.0] * len(mapa)
        val = str(item.get(campo, "")).strip()
        if val in mapa:
            onehot[mapa[val]] = 1.0
        x.extend(onehot)
    for campo in enc["campos_num"]:
        n = para_numero(item.get(campo))
        if n is None:
            n = enc["stats"][campo]["media"]
        x.append((float(n) - enc["stats"][campo]["media"]) / enc["stats"][campo]["desvio"])
    return x


def sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def prever_prob(x: list[float], pesos: list[float]) -> float:
    return sigmoid(sum(wj * xj for wj, xj in zip(pesos, x)))


def treinar_logistica(X: list[list[float]], y: list[int], class_weight=None) -> list[float]:
    n, d = len(X), len(X[0])
    pesos = [0.0] * d
    if class_weight is None:
        counts = Counter(y)
        total = len(y)
        class_weight = {c: total / (2 * counts[c]) for c in counts}
    for ep in range(EPOCAS):
        grad = [0.0] * d
        for xi, yi in zip(X, y):
            p = prever_prob(xi, pesos)
            w = class_weight.get(yi, 1.0)
            err = (w * (p - yi)) / n
            for j in range(d):
                grad[j] += err * xi[j]
        lr = LR * (0.995 ** (ep // 100))
        for j in range(d):
            reg = L2 * pesos[j] if j != 0 else 0.0
            pesos[j] -= lr * (grad[j] + reg)
    return pesos


def split_estratificado(base: list[dict], prop_treino=PROPORCAO_TREINO, seed=SEMENTE):
    rnd = random.Random(seed)
    por_classe = {}
    for i, l in enumerate(base):
        por_classe.setdefault(int(l[ALVO]), []).append(i)
    treino_idx, teste_idx = [], []
    for c, idxs in por_classe.items():
        rnd.shuffle(idxs)
        corte = int(len(idxs) * prop_treino)
        if len(idxs) > 1 and corte == len(idxs):
            corte -= 1
        treino_idx.extend(idxs[:corte])
        teste_idx.extend(idxs[corte:])
    rnd.shuffle(treino_idx)
    rnd.shuffle(teste_idx)
    return [base[i] for i in treino_idx], [base[i] for i in teste_idx]


def kfold_estratificado(base: list[dict], k=K_FOLD, seed=SEMENTE):
    rnd = random.Random(seed)
    por_classe = {}
    for i, l in enumerate(base):
        por_classe.setdefault(int(l[ALVO]), []).append(i)
    folds = [[] for _ in range(k)]
    for c, idxs in por_classe.items():
        rnd.shuffle(idxs)
        for j, idx in enumerate(idxs):
            folds[j % k].append(idx)
    for f in folds:
        rnd.shuffle(f)
    result = []
    for i in range(k):
        teste_idx = set(folds[i])
        treino = [base[j] for j in range(len(base)) if j not in teste_idx]
        teste = [base[j] for j in folds[i]]
        result.append((treino, teste))
    return result


def metricas(y_true: list[int], y_pred: list[int], probs: list[float] | None = None) -> dict:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    total = max(1, len(y_true))
    acc = (tp + tn) / total
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    brier = sum((p - t) ** 2 for t, p in zip(y_true, probs)) / total if probs else None
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "acuracia": acc, "precisao": prec, "recall": rec, "f1": f1, "brier": brier}


def fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def avaliar(pesos, enc, teste, limiar=0.5):
    X = [vetorizar(l, enc) for l in teste]
    y_true = [int(l[ALVO]) for l in teste]
    probs = [prever_prob(x, pesos) for x in X]
    y_pred = [1 if p >= limiar else 0 for p in probs]
    return y_true, y_pred, probs


def baseline_majoritaria(treino, teste):
    maj = Counter(int(l[ALVO]) for l in treino).most_common(1)[0][0]
    y_true = [int(l[ALVO]) for l in teste]
    y_pred = [maj] * len(teste)
    probs = [float(maj) for _ in teste]
    return maj, y_true, y_pred, probs


def melhor_limiar_cv(base):
    limiares = [i / 100 for i in range(20, 81)]
    scores = {t: [] for t in limiares}
    for treino, teste in kfold_estratificado(base, K_FOLD, SEMENTE):
        enc = construir_encoder(treino)
        Xtr = [vetorizar(l, enc) for l in treino]
        ytr = [int(l[ALVO]) for l in treino]
        pesos = treinar_logistica(Xtr, ytr)
        y_true, _, probs = avaliar(pesos, enc, teste, 0.5)
        for t in limiares:
            y_pred = [1 if p >= t else 0 for p in probs]
            scores[t].append(metricas(y_true, y_pred, probs)["f1"])
    medias = {t: sum(v) / len(v) for t, v in scores.items()}
    # escolhe maior F1; desempate pelo limiar mais próximo de 0.5
    melhor = max(limiares, key=lambda t: (medias[t], -abs(t - 0.5)))
    return melhor, medias


def cv_resumo(base):
    folds = kfold_estratificado(base, K_FOLD, SEMENTE)
    ms = []
    for treino, teste in folds:
        enc = construir_encoder(treino)
        Xtr = [vetorizar(l, enc) for l in treino]
        ytr = [int(l[ALVO]) for l in treino]
        pesos = treinar_logistica(Xtr, ytr)
        y_true, y_pred, probs = avaliar(pesos, enc, teste, 0.5)
        ms.append(metricas(y_true, y_pred, probs))
    def agg(k):
        vals = [m[k] for m in ms if m[k] is not None]
        return sum(vals) / len(vals), (max(vals) - min(vals))
    return {k: agg(k) for k in ["acuracia", "precisao", "recall", "f1", "brier"]}, ms


def importancia_features(pesos, enc):
    nomes = ["intercepto"]
    for campo in enc["campos_cat"]:
        for val in enc["categorias"][campo].keys():
            nomes.append(f"{campo}={val}")
    for campo in enc["campos_num"]:
        nomes.append(campo)
    pares = list(zip(nomes, pesos))
    pares.sort(key=lambda x: abs(x[1]), reverse=True)
    return pares


def salvar_modelo(pesos, enc, meta):
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    with open(ARQUIVO_MODELO, "w", encoding="utf-8") as f:
        json.dump({"enc": enc, "pesos": pesos, "meta": meta}, f, ensure_ascii=False)


def carregar_modelo():
    with open(ARQUIVO_MODELO, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj["pesos"], obj["enc"], obj.get("meta", {})


def curva_limiar(y_true, probs):
    pontos = []
    for i in range(0, 101, 5):
        t = i / 100
        y_pred = [1 if p >= t else 0 for p in probs]
        m = metricas(y_true, y_pred, probs)
        pontos.append({"t": t, "acc": m["acuracia"], "prec": m["precisao"], "rec": m["recall"], "f1": m["f1"]})
    return pontos


def gerar_dashboard(meta, m, mb, m_t, imp, curva, cvm):
    os.makedirs(PASTA_DASH, exist_ok=True)
    curve_json = json.dumps(curva, ensure_ascii=False)
    imp_json = json.dumps([{"name": n, "value": v} for n, v in imp[:10]], ensure_ascii=False)
    limiar = meta["limiar_recomendado"]
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard ML - Rentabilidade de Filmes</title>
  <style>
    :root{{--bg:#f4f6fb;--card:#fff;--text:#1f2937;--muted:#6b7280;--primary:#1d4ed8;--ok:#059669;--warn:#d97706;--bad:#dc2626;--border:#e5e7eb;--shadow:0 8px 24px rgba(15,23,42,.06)}}
    *{{box-sizing:border-box}} body{{margin:0;font-family:"Segoe UI",Arial,sans-serif;background:linear-gradient(180deg,#eef4ff 0%,var(--bg) 180px);color:var(--text)}}
    .wrap{{max-width:1200px;margin:0 auto;padding:32px 20px 48px}} .eyebrow{{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--primary);background:#dbeafe;padding:6px 10px;border-radius:999px}}
    h1{{margin:12px 0 8px;font-size:clamp(28px,4vw,42px);line-height:1.15}} .lead{{margin:0 0 24px;max-width:900px;color:#374151;line-height:1.6}}
    .grid{{display:grid;gap:16px}} .kpis{{grid-template-columns:repeat(5,minmax(0,1fr));margin-bottom:16px}} .two{{grid-template-columns:1.1fr .9fr;margin-bottom:16px}} .two-eq{{grid-template-columns:1fr 1fr;margin-bottom:16px}}
    .card{{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;box-shadow:var(--shadow)}} .card h2{{margin:0 0 4px;font-size:18px}} .sub{{margin:0 0 16px;color:var(--muted);font-size:14px;line-height:1.5}}
    .kpi .label{{color:var(--muted);font-size:13px;font-weight:600}} .kpi .value{{font-size:30px;font-weight:800;margin:8px 0 4px}} .kpi .delta{{font-size:13px;color:var(--muted)}} .good{{color:var(--ok)}} .bad{{color:var(--bad)}}
    .track{{height:12px;background:#e5e7eb;border-radius:999px;overflow:hidden;margin-bottom:6px}} .fill{{height:100%;border-radius:999px}}
    .bar-row{{margin-bottom:12px}} .bar-head{{display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px;gap:12px}} .bar-name{{font-weight:600}} .bar-val{{color:var(--muted);white-space:nowrap}}
    .cm{{display:grid;grid-template-columns:140px 1fr 1fr;gap:8px}} .cm .head,.cm .rowh{{font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;display:flex;align-items:center;justify-content:center;text-align:center;padding:8px}} .cm .rowh{{justify-content:flex-start;text-align:left}}
    .cell{{border-radius:12px;padding:16px;text-align:center;border:1px solid var(--border)}} .cell .n{{font-size:34px;font-weight:800}} .cell .t{{font-size:12px;color:var(--muted);margin-top:6px}}
    .tn{{background:#ecfdf5}} .tp{{background:#eff6ff}} .fp{{background:#fff7ed}} .fn{{background:#fef2f2}}
    .legend{{display:flex;flex-wrap:wrap;gap:12px;margin-top:14px;font-size:13px}} .dot{{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:6px;vertical-align:middle}}
    svg.line-chart{{width:100%;height:auto;display:block}} .note{{background:#fffbeb;border:1px solid #fde68a;color:#92400e;padding:14px 16px;border-radius:12px;font-size:14px;line-height:1.6}}
    table{{width:100%;border-collapse:collapse;font-size:14px}} th,td{{padding:10px 8px;border-bottom:1px solid var(--border);text-align:left}} th{{font-size:12px;color:var(--muted);text-transform:uppercase}} td.num{{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}}
    .pill{{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;background:#dbeafe;color:#1d4ed8}} code{{background:#f3f4f6;padding:2px 6px;border-radius:6px}}
    @media(max-width:980px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.two,.two-eq{{grid-template-columns:1fr}}}} @media(max-width:560px){{.kpis{{grid-template-columns:1fr}}}}
  </style>
</head>
<body><div class="wrap">
  <span class="eyebrow">Aprendizagem Supervisionada • Versão simplificada</span>
  <h1>Dashboard ML: Rentabilidade de Filmes</h1>
  <p class="lead">Modelo simplificado para prever rentabilidade antes do lançamento. Usa poucas features pré-lançamento, validação cruzada estratificada, pesos de classe e limiar recomendado por F1.</p>

  <section class="grid kpis">
    <div class="card kpi"><div class="label">Acurácia (teste)</div><div class="value">{fmt_pct(m['acuracia'])}</div><div class="delta good">Baseline: {fmt_pct(mb['acuracia'])}</div></div>
    <div class="card kpi"><div class="label">F1 (teste)</div><div class="value">{fmt_pct(m['f1'])}</div><div class="delta">Limiar {limiar:.2f}</div></div>
    <div class="card kpi"><div class="label">Precisão (teste)</div><div class="value">{fmt_pct(m['precisao'])}</div><div class="delta">Custo de FP</div></div>
    <div class="card kpi"><div class="label">Recall (teste)</div><div class="value">{fmt_pct(m['recall'])}</div><div class="delta">Custo de FN</div></div>
    <div class="card kpi"><div class="label">Brier score</div><div class="value">{m['brier']:.3f}</div><div class="delta">Menor = melhor calibração</div></div>
  </section>

  <section class="card" style="margin-bottom:16px">
    <h2>Métricas por limiar de decisão (gráfico de linhas)</h2>
    <p class="sub">Ajustar o limiar muda o trade-off entre precisão e recall. Linha pontilhada = limiar recomendado ({limiar:.2f}).</p>
    <svg id="threshold-chart" class="line-chart" viewBox="0 0 980 360"></svg>
    <div class="legend" id="line-legend"></div>
  </section>

  <section class="grid two">
    <div class="card"><h2>Comparação com baseline</h2><p class="sub">Baseline majoritária no conjunto de teste.</p><div id="metrics-bars"></div>
      <div class="legend"><span><span class="dot" style="background:#1d4ed8"></span>Modelo</span><span><span class="dot" style="background:#94a3b8"></span>Baseline</span></div></div>
    <div class="card"><h2>Matriz de confusão (limiar {limiar:.2f})</h2><p class="sub">Teste hold-out.</p>
      <div class="cm">
        <div></div><div class="head">Previsto: 0</div><div class="head">Previsto: 1</div>
        <div class="rowh">Real: 0</div><div class="cell tn"><div class="n">{m_t['tn']}</div><div class="t">TN</div></div><div class="cell fp"><div class="n">{m_t['fp']}</div><div class="t">FP</div></div>
        <div class="rowh">Real: 1</div><div class="cell fn"><div class="n">{m_t['fn']}</div><div class="t">FN</div></div><div class="cell tp"><div class="n">{m_t['tp']}</div><div class="t">TP</div></div>
      </div>
      <div class="note" style="margin-top:14px"><strong>Custo do erro:</strong> FP = investir em filme não rentável; FN = perder oportunidade. Ajuste o limiar conforme o negócio.</div>
    </div>
  </section>

  <section class="grid two-eq">
    <div class="card"><h2>Coeficientes principais</h2><p class="sub">Regressão logística: sinal indica direção da associação no modelo.</p><div id="coef-bars"></div></div>
    <div class="card"><h2>Validação e formulação</h2><p class="sub">Resumo técnico.</p>
      <table>
        <tr><th>Item</th><th>Valor</th></tr>
        <tr><td>Algoritmo</td><td><span class="pill">Regressão Logística</span></td></tr>
        <tr><td>Features</td><td>{', '.join(CAMPOS_CATEGORICOS + CAMPOS_NUMERICOS)}</td></tr>
        <tr><td>Validação</td><td>Split estratificado 70/30 + CV estratificada k={K_FOLD}</td></tr>
        <tr><td>F1 médio CV (limiar 0,5)</td><td>{fmt_pct(cvm['f1'][0])}</td></tr>
        <tr><td>Brier médio CV</td><td>{cvm['brier'][0]:.3f}</td></tr>
        <tr><td>Limiar recomendado</td><td>{limiar:.2f} (max F1 na CV)</td></tr>
        <tr><td>Classes de peso</td><td>Balanceadas automaticamente</td></tr>
      </table>
      <div class="note" style="margin-top:14px"><strong>Limitação:</strong> dados simulados para protótipo. Para uso real: dados históricos auditados, validação temporal e monitoramento.</div>
    </div>
  </section>
</div>
<script>
const metrics=[{{label:'Acurácia',model:{m['acuracia']*100:.1f},base:{mb['acuracia']*100:.1f}}},{{label:'Precisão',model:{m['precisao']*100:.1f},base:{mb['precisao']*100:.1f}}},{{label:'Recall',model:{m['recall']*100:.1f},base:{mb['recall']*100:.1f}}},{{label:'F1',model:{m['f1']*100:.1f},base:{mb['f1']*100:.1f}}}];
const thresholdCurve={curve_json};
const coefs={imp_json};
const recLimiar={limiar};
function pct(v){{return v.toFixed(1).replace('.',',')+'%'}}
function renderLineChart(){{const svg=document.getElementById('threshold-chart');const W=980,H=360,pad={{l:58,r:24,t:20,b:44}};const iw=W-pad.l-pad.r,ih=H-pad.t-pad.b;const x=t=>pad.l+t*iw;const y=v=>pad.t+(1-v)*ih;
const series=[{{key:'acc',label:'Acurácia',color:'#1d4ed8'}},{{key:'prec',label:'Precisão',color:'#059669'}},{{key:'rec',label:'Recall',color:'#d97706'}},{{key:'f1',label:'F1',color:'#7c3aed'}}];
let out=`<rect x="0" y="0" width="${{W}}" height="${{H}}" fill="#fff"/>`;
for(let g=0;g<=5;g++){{const gv=g/5,yy=y(gv);out+=`<line x1="${{pad.l}}" y1="${{yy}}" x2="${{W-pad.r}}" y2="${{yy}}" stroke="#e5e7eb"/>`;out+=`<text x="${{pad.l-10}}" y="${{yy+4}}" text-anchor="end" font-size="12" fill="#6b7280">${{Math.round(gv*100)}}%</text>`;}}
for(let g=0;g<=10;g++){{const gv=g/10,xx=x(gv);out+=`<line x1="${{xx}}" y1="${{pad.t}}" x2="${{xx}}" y2="${{H-pad.b}}" stroke="#f3f4f6"/>`;out+=`<text x="${{xx}}" y="${{H-14}}" text-anchor="middle" font-size="12" fill="#6b7280">${{gv.toFixed(1).replace('.',',')}}</text>`;}}
out+=`<line x1="${{x(recLimiar)}}" y1="${{pad.t}}" x2="${{x(recLimiar)}}" y2="${{H-pad.b}}" stroke="#111827" stroke-width="1.5" stroke-dasharray="6 5" opacity="0.5"/>`;
out+=`<text x="${{x(recLimiar)+6}}" y="${{pad.t+14}}" font-size="12" fill="#374151">limiar ${{recLimiar.toFixed(2).replace('.',',')}}</text>`;
series.forEach(s=>{{const pts=thresholdCurve.map(d=>`${{x(d.t)}},${{y(Math.max(0,Math.min(1,d[s.key])))}}`).join(' ');out+=`<polyline fill="none" stroke="${{s.color}}" stroke-width="3" points="${{pts}}"/>`;
thresholdCurve.forEach(d=>{{const val=d[s.key];out+=`<circle cx="${{x(d.t)}}" cy="${{y(Math.max(0,Math.min(1,val)))}}" r="3" fill="${{s.color}}"><title>${{s.label}} | limiar ${{d.t.toFixed(2)}} | ${{(val*100).toFixed(1)}}%</title></circle>`;}});}});
out+=`<text x="${{pad.l+iw/2}}" y="${{H-2}}" text-anchor="middle" font-size="13" fill="#374151">Limiar de probabilidade</text>`;
out+=`<text x="16" y="${{pad.t+ih/2}}" text-anchor="middle" font-size="13" fill="#374151" transform="rotate(-90 16 ${{pad.t+ih/2}})">Métrica</text>`;
svg.innerHTML=out;document.getElementById('line-legend').innerHTML=series.map(s=>`<span><span class="dot" style="background:${{s.color}}"></span>${{s.label}}</span>`).join('');}}
renderLineChart();
const mb=document.getElementById('metrics-bars');metrics.forEach(m=>{{const row=document.createElement('div');row.className='bar-row';row.innerHTML=`<div class="bar-head"><span class="bar-name">${{m.label}}</span><span class="bar-val">Modelo ${{pct(m.model)}} • Baseline ${{pct(m.base)}}</span></div><div class="track"><div class="fill" style="width:${{m.model}}%;background:linear-gradient(90deg,#1d4ed8,#0ea5e9)"></div></div><div class="track"><div class="fill" style="width:${{m.base}}%;background:#94a3b8"></div></div>`;mb.appendChild(row);}});
const cb=document.getElementById('coef-bars');const maxAbs=Math.max(...coefs.map(c=>Math.abs(c.value)));coefs.forEach(c=>{{const w=(Math.abs(c.value)/maxAbs)*100;const pos=c.value>=0;const row=document.createElement('div');row.className='bar-row';row.innerHTML=`<div class="bar-head"><span class="bar-name">${{c.name}}</span><span class="bar-val" style="color:${{pos?'#059669':'#dc2626'}}">${{(c.value>=0?'+':'')+c.value.toFixed(4).replace('.',',')}}</span></div><div class="track"><div class="fill" style="width:${{w}}%;background:${{pos?'linear-gradient(90deg,#059669,#34d399)':'linear-gradient(90deg,#dc2626,#f87171)'}}"></div></div>`;cb.appendChild(row);}});
</script></body></html>"""
    with open(ARQUIVO_DASH, "w", encoding="utf-8") as f:
        f.write(html)


def relatorio_md(caminho, base, treino, teste, m, mb, m_t, limiar, cvm, imp):
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    linhas = []
    a = linhas.append
    a("# Resultado — Modelo Supervisionado (Simplificado) de Rentabilidade de Filmes")
    a("")
    a("## Problema")
    a("Prever se um filme tende a ser rentável antes do lançamento, para apoiar decisões de marketing e distribuição.")
    a("")
    a("## Formulação")
    a(f"- Base: `{caminho}` | Registros: **{len(base)}** (treino={len(treino)}, teste={len(teste)})")
    a("- Alvo: `rentavel` (1 = receita_mundial_milhoes >= 1.8 * orcamento_milhoes)")
    a("- Algoritmo: **Regressão Logística Binária** com pesos de classe (balanceado)")
    a("- Validação: split estratificado 70/30 + CV estratificada k=5")
    a(f"- Limiar recomendado: **{limiar:.2f}** (maximiza F1 médio na CV)")
    a("")
    a("## Features (simplificadas, pré-lançamento)")
    a(f"- Categóricas: {', '.join(CAMPOS_CATEGORICOS)}")
    a(f"- Numéricas: {', '.join(CAMPOS_NUMERICOS)}")
    a("- Removidas para simplificar/evitar vazamento: `receita_mundial_milhoes` (vira alvo), `marketing_milhoes`, `salas_estreia_planejadas`, `duracao_min`, `classificacao_indicativa`.")
    a("")
    a("## Desempenho no teste (limiar recomendado)")
    a("")
    a("| Métrica | Modelo | Baseline (majoritária) |")
    a("|---|---:|---:|")
    a(f"| Acurácia | {fmt_pct(m_t['acuracia'])} | {fmt_pct(mb['acuracia'])} |")
    a(f"| Precisão | {fmt_pct(m_t['precisao'])} | {fmt_pct(mb['precisao'])} |")
    a(f"| Recall | {fmt_pct(m_t['recall'])} | {fmt_pct(mb['recall'])} |")
    a(f"| F1 | {fmt_pct(m_t['f1'])} | {fmt_pct(mb['f1'])} |")
    a(f"| Brier score | {m_t['brier']:.4f} | {mb['brier']:.4f} |")
    a("")
    a("## Validação cruzada (k=5, limiar 0,5)")
    a("")
    a("| Métrica | Média | Amplitude |")
    a("|---|---:|---:|")
    for k, label in [("acuracia","Acurácia"),("precisao","Precisão"),("recall","Recall"),("f1","F1"),("brier","Brier")]:
        media, amp = cvm[k]
        if k == "brier":
            a(f"| {label} | {media:.4f} | {amp:.4f} |")
        else:
            a(f"| {label} | {fmt_pct(media)} | {fmt_pct(amp)} |")
    a("")
    a("## Matriz de confusão (teste, limiar recomendado)")
    a("")
    a("| real \\ previsto | 0 | 1 |")
    a("|---|---:|---:|")
    a(f"| 0 | {m_t['tn']} | {m_t['fp']} |")
    a(f"| 1 | {m_t['fn']} | {m_t['tp']} |")
    a("")
    a("## Coeficientes principais")
    a("")
    a("| Feature | Coeficiente |")
    a("|---|---:|")
    for nome, coef in imp[:10]:
        a(f"| {nome} | {coef:.4f} |")
    a("")
    a("## Leitura")
    a("- O modelo é um protótipo simplificado: bom para demonstração do fluxo supervisionado, não para decisão real de investimento.")
    a("- O limiar recomendado equilibra FP/FN conforme F1 na CV; o negócio pode ajustar conforme custo.")
    a("- Brier score avalia qualidade das probabilidades (quanto menor, melhor).")
    a("- Limitações: dados simulados, sem validação temporal, sem fatores externos de mercado.")
    a("")
    with open(ARQUIVO_RESULTADO, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


def cmd_treinar(args):
    caminho = args[0] if args else BASE_PADRAO
    if not os.path.exists(caminho):
        print(f"Arquivo não encontrado: {caminho}")
        sys.exit(1)
    base = preparar_linhas(ler_csv(caminho))
    if len(base) < 30:
        print(f"Base insuficiente: {len(base)}")
        sys.exit(1)
    classes = Counter(int(l[ALVO]) for l in base)
    if len(classes) < 2:
        print(f"Alvo com uma classe: {classes}")
        sys.exit(1)

    treino, teste = split_estratificado(base)
    enc = construir_encoder(treino)
    Xtr = [vetorizar(l, enc) for l in treino]
    ytr = [int(l[ALVO]) for l in treino]
    pesos = treinar_logistica(Xtr, ytr)

    # avaliação em limiar 0.5 e limiar recomendado
    y_true, y_pred, probs = avaliar(pesos, enc, teste, 0.5)
    m = metricas(y_true, y_pred, probs)
    maj, yb_true, yb_pred, yb_probs = baseline_majoritaria(treino, teste)
    mb = metricas(yb_true, yb_pred, yb_probs)

    limiar, _ = melhor_limiar_cv(base)
    y_pred_t = [1 if p >= limiar else 0 for p in probs]
    m_t = metricas(y_true, y_pred_t, probs)

    cvm, _ = cv_resumo(base)
    imp = importancia_features(pesos, enc)
    curva = curva_limiar(y_true, probs)

    relatorio_md(caminho, base, treino, teste, m, mb, m_t, limiar, cvm, imp)
    meta = {"base": caminho, "n_treino": len(treino), "n_teste": len(teste), "limiar_recomendado": limiar,
            "acuracia": m_t["acuracia"], "f1": m_t["f1"], "brier": m_t["brier"], "cv_f1_media": cvm["f1"][0]}
    salvar_modelo(pesos, enc, meta)
    gerar_dashboard(meta, m, mb, m_t, imp, curva, cvm)

    print("=" * 72)
    print("MODELO SIMPLIFICADO TREINADO - RENTABILIDADE DE FILMES")
    print("=" * 72)
    print(f"Base: {caminho} | Registros: {len(base)} (treino={len(treino)}, teste={len(teste)}) | Classes: {dict(classes)}")
    print(f"Algoritmo: Regressão Logística Binária (pesos de classe, L2)")
    print(f"CV k={K_FOLD} (limiar 0,5): F1 médio={fmt_pct(cvm['f1'][0])} | Brier médio={cvm['brier'][0]:.4f}")
    print(f"Limiar recomendado (max F1 CV): {limiar:.2f}")
    print()
    print(f"Teste @ limiar {limiar:.2f}: Acc={fmt_pct(m_t['acuracia'])} Prec={fmt_pct(m_t['precisao'])} Rec={fmt_pct(m_t['recall'])} F1={fmt_pct(m_t['f1'])} Brier={m_t['brier']:.4f}")
    print(f"Baseline:               Acc={fmt_pct(mb['acuracia'])} Prec={fmt_pct(mb['precisao'])} Rec={fmt_pct(mb['recall'])} F1={fmt_pct(mb['f1'])}")
    print(f"Matriz confusão: TN={m_t['tn']} FP={m_t['fp']} FN={m_t['fn']} TP={m_t['tp']}")
    print()
    print(f"Relatório: {ARQUIVO_RESULTADO}")
    print(f"Modelo:    {ARQUIVO_MODELO}")
    print(f"Dashboard: {ARQUIVO_DASH}")


def cmd_prever(args):
    if not args:
        print("Uso: py modelo_filmes_ml.py prever '{...json...}'")
        sys.exit(1)
    if not os.path.exists(ARQUIVO_MODELO):
        print("Modelo não encontrado. Rode: py modelo_filmes_ml.py treinar")
        sys.exit(1)
    pesos, enc, meta = carregar_modelo()
    try:
        item = json.loads(args[0])
    except json.JSONDecodeError as e:
        print(f"JSON inválido: {e}")
        sys.exit(1)
    x = vetorizar(item, enc)
    p = prever_prob(x, pesos)
    limiar = float(meta.get("limiar_recomendado", 0.5))
    classe = 1 if p >= limiar else 0
    print("Previsão de rentabilidade (pré-lançamento):")
    print(f"  Probabilidade rentável (1):    {fmt_pct(p)}")
    print(f"  Probabilidade não rentável (0): {fmt_pct(1-p)}")
    print(f"  Limiar recomendado: {limiar:.2f}")
    print(f"  Classe prevista: {classe} ({'rentável' if classe==1 else 'não rentável'})")
    print("Observação: protótipo com dados simulados; usar como apoio, não decisão automática.")


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
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
    except KeyboardInterrupt:
        print("\nInterrompido.")
