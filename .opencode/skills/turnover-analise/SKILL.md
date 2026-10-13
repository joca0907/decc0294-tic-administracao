---
name: turnover-analise
description: Analisa turnover e rotatividade de pessoal com calculo e relatorio em 7 passos. Use when usuario pedir analise de turnover, calculo de rotatividade, relatorio de RH ou diagnostico de retencao.
license: MIT
compatibility: opencode
metadata:
  audience: estudantes
  workflow: rh-analise
---

# Turnover Analise

Fonte-metodo: https://www.sesamehr.com.br/blog/relatorios-de-rh/relatorio-de-turnover-como-transformar-dados-em-estrategias-de-retencao/

## What I do
- Calculo turnover geral, voluntario, involuntario, funcional e disfuncional
- Segmento por area, cargo, gestor, tempo de casa e unidade
- Cruzo com contexto qualitativo e estimo impacto financeiro
- Entrego relatorio com plano de acao com responsavel e prazo

## When to use me
Use ONLY when o usuario pedir turnover, rotatividade, retencao, desligamentos, ou relatorio de RH. Nao usar para recrutamento geral ou folha de pagamento.

## Steps
1. Definir objetivo e periodo
   - Perguntar: por que analisar? Qual periodo? mensal, trimestral, anual?
   - Sem objetivo, nao continuar. Ex: reduzir rotatividade em area critica.
2. Levantar e qualificar dados
   - Pedir: admissoes, desligamentos, headcount inicio, headcount fim
   - Qualificar cada saida: tipo voluntario/involuntario, area/cargo, tempo de casa, gestor, motivo
   - Padronizar: definir o que entra (estagiario? temporario? transferencia interna nao conta)
   - Se faltar dado, pedir e nao inventar. Respeitar LGPD: anonimizar nomes
3. Calcular indicadores-chave
   - Headcount medio = (HC inicio + HC fim) / 2
   - Turnover geral (%) = desligamentos / headcount medio x 100
   - Turnover movimentacao (%) = ((admissoes + desligamentos) / 2) / headcount medio x 100
   - Separar: voluntario, involuntario, funcional (saida baixo desempenho), disfuncional (perda talento-chave)
   - No Excel: F2=MÉDIA(D2;E2), G2=(((B2+C2)/2)/F2)*100
4. Cruzar e identificar padroes
   - Segmentar por area, cargo, gestor, localidade, tempo de casa (0-90d, 3-6m, 6-12m, 1a+)
   - Procurar concentracao: 70% das saidas em poucos recortes? Pico apos bonus/avaliacao/troca lideranca?
   - Adaptacao IF/-publico: usar exoneracao a pedido, redistribuicao, remocao, tempo medio por setor
5. Trazer contexto qualitativo
   - Pedir: entrevista desligamento, clima/eNPS, avaliacao desempenho
   - Explicar o porque: lideranca, carreira, remuneracao, carga, cultura
6. Estimar impacto no negocio
   - Custo por saida = rescisao + recrutamento + treinamento + perda produtividade (vacancia + rampagem)
   - Apontar risco: perda conhecimento, atraso SLA/projeto
   - Nunca apresentar numero sem fonte. Se estimar, escrever ESTIMATIVA
7. Transformar em plano de acao
   - Saida obrigatoria no formato:
     Definicao / Exemplo brasileiro / Limitacao
     Achado (onde) / Causa provavel (porque) / Acao (o que fazer) + Responsavel + Prazo + Meta
   - Versao diretoria: estrategica + custo. Versao gestor: tatica por time
   - Sugerir dashboard continuo e gatilho: se area > 1,5x media empresa, iniciar diagnostico

## Exemplo de saida
 turnover 19% anual (38 media / 200 HC). Concentrado: Comercial 35% voluntario 0-9m.
 Causa: onboarding fraco + meta sem clareza. Custo est. R$ X (Fonte: dados RH).
 Acao: onboarding 90d + 1:1 semanal - Resp: Gestora Comercial - Prazo 30d - Meta: 35% para 20% em 6m.
 Limitacao: base com <20 saidas por recorte nao e conclusiva.
