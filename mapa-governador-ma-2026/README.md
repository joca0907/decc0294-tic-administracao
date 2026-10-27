# Mapa coroplético — Votação para Governador no Maranhão (Eleição 2026, 1º turno)

## Arquivos

| Arquivo | Descrição |
|---|---|
| `mapa_governador_ma_2026.html` | **Mapa interativo (abrir este arquivo no navegador).** Autocontido: Leaflet embutido, funciona offline (os tiles de fundo são os únicos recursos externos, opcionais). |
| `dados_resultados_ma_governador_2026.json` | Resultados por município extraídos da API do TSE (217 municípios, verificação de integridade: soma = total estadual). |
| `resumo_estadual.json` | Resultado estadual consolidado do cargo. |
| `malha_municipios_ma_ibge.geojson` | Malha municipal do Maranhão (IBGE, via geodata-br, coordenadas arredondadas a 4 decimais). |

## Resultado

**Eleito no 1º turno: Eduardo Braide (PSD)** — 2.104.122 votos nominais, **54,02%** dos nominais apurados.
2º colocado: **Orleans Brandão (MDB)** — 1.354.044 votos, 34,76%. Felipe Camarão (PT) 9,60%.

- Municípios ganhos por partido do vencedor: **PSD 130**, **MDB 87** (217 no total).

## Fonte de dados (API oficial do TSE)

Portal de resultados: `https://resultados.tse.jus.br/oficial/app/index.html`

1. Config de eleições: `https://resultados.tse.jus.br/oficial/comum/config/ele-c.jws`
   → Eleição Ordinária Estadual 2026, 1º turno: **código 6259**; cargo Governador: **código 3**.
2. Config de municípios (códigos TSE, IBGE e nomes): `https://resultados.tse.jus.br/oficial/ele2026/6259/config/mun-e006259-cm.json`
3. Resultado por município (217 arquivos `.jws`, JSON assinado — payload em base64url):
   `https://resultados.tse.jus.br/oficial/ele2026/6259/dados/ma/ma<COD_TSE>-c0003-e006259-u.jws`
4. Malha dos municípios: `https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-21-mun.json`
   (junção pelo código IBGE `cdi` presente na config do TSE — não houve casamento por nome.)

## Critério de percentual

Percentuais seguem o critério do próprio TSE: votos do candidato ÷ **nominais apurados** (válidos + anulados sub judice).
Os 48.924 votos de Roberto Rocha (PRTB) estão **anulados sub judice** — aparecem nos totais e nos tooltips com asterisco, mas não definem vencedor em nenhum município (o vencedor em todos os 217 é Braide ou Brandão).

## Modos de visualização

1. **Candidato vencedor** — cor por partido do mais votado (PSD âmbar, MDB verde).
2. **% de votos do vencedor** — escala sequencial (laranja) em faixas de 0–30% até ≥80%.
3. **Vantagem sobre o 2º (p.p.)** — escala sequencial (azul) em faixas de 0–5 até ≥70 pontos percentuais.

## Painel lateral de resultados

À direita do mapa, painel com:
- **Ranking completo dos 8 candidatos** (nome, partido, coligação, %, votos absolutos e barra proporcional), com selo *ELEITO* e destaque vermelho para os votos anulados sub judice;
- **Municípios ganhos** por partido do vencedor (PSD 130 · MDB 87);
- **Participação**: eleitorado apto, comparecimento, abstenção, brancos, nulos e anulados;
- Botão **“Ocultar painel »”** recolhe o painel e expande o mapa (Leaflet recalcula o tamanho).

Mapa-base: Esri World Light Gray (sem necessidade de chave de API; se estiver offline, o mapa continua funcional sobre fundo cinza-claro).

## Observações

- Dados totalizados e oficiais (`"f": "o"`, `"tf": "s"`), atualizados em 05/10/2026 02:01:55.
- O governador foi decidido no 1º turno (Braide > 50%), portanto não houve 2º turno para o cargo.
- Os percentuais do mapa batem com os divulgados pelo TSE (verificação: São Luís 75,92% Braide; Açailândia 47,39%).
