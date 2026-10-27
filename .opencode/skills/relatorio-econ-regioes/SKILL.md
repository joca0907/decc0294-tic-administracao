# Skill: relatorio-econ-regioes

Fonte-metodo: API oficial IBGE - SIDRA (apisidra.ibge.gov.br) e API de geografia do IBGE
(servicodados.ibge.gov.br: localidades e malhas GeoJSON). IDH: Atlas do Desenvolvimento
Humano do Brasil (atlasbrasil.org.br, dados PNUD/Ipea/FJP). Periodicidade do IDH e
edicoes disponiveis devem ser verificados no site no momento do relatorio, nao de memoria.

## What I do
- Estruturar relatorio dinamico (pagina HTML interativa) da evolucao economica do Brasil por regiao: N, NE, CO, SE, S
- Puxar os dados em tempo de exibicao de API oficial (o artefato consulta a API ao abrir no navegador)
- Narrar cada regiao no formato-padrao abaixo, com fonte e limitacao declaradas
- Nunca inventar numero: todo valor exibido vem da API ou de arquivo citado; sem dado verificado, marcar "A VERIFICAR"

## When to use me
Use SOMENTE quando o usuario pedir relatorio por regiao, mapa economico do Brasil,
evolucao historica de PIB/IDH regional ou comparacao entre N/NE/CO/SE/S.
Nao usar para analise de municipio isolado ou para RH (usar turnover-analise).

## Steps
1. Definir objetivo, indicadores e janela temporal
   - Ex.: "evolucao do PIB e do IDH por regiao desde 2002". Sem objetivo, nao continuar.
   - Indicadores padrao: PIB (SIDRA, tabela de PIB dos Municipios) e IDH-M (Atlas).
2. Verificar fontes ANTES de codificar
   - Consultar a API (descricao da tabela) e fixar o ID de tabela e da variavel somente depois de ver a descricao retornada.
   - Se a API nao responder pelo ambiente do agente, o artefato consulta no navegador do usuario; deixar a verificacao pendente registrada no texto.
3. Montar o artefato em um unico arquivo HTML
   - Mapa do Brasil em SVG/GeoJSON reagrupado em 5 regioes com a API de geografia do IBGE
   - Eixo do tempo (seletor/animacao por ano), series historicas por regiao e painel de narrativa
   - Deixar sempre visivel: URL da consulta, data da leitura e periodicidade do indicador
4. Calcular so derivados declarados
   - Permitido: soma, razao (participacao da regiao no total nacional), variacao % entre anos. Declarar que sao derivados.
   - Nao usar deflator ou conversao que a fonte nao forneça; sem dado de exercicio real, nao falar em crescimento real, so nominal (se a fonte for a precos correntes).
5. Narrar cada regiao no formato-padrao
   - Definicao do indicador / Exemplo brasileiro / Limitacao
   - Achado (onde, qual regiao e periodo) / Causa provavel (porque, com fonte) / Acao ou implicacao
6. Contexto historico ancorado em dado
   - Ciclos (crise 2015-16, pandemia 2020) so aparecem se o proprio dado mostrar; citar o ano/ponto da serie
   - Interpretacao sem base na serie nao entra no relatorio
7. Saida
   - Resumo executivo por regiao; limitacoes declaradas (ex.: IDH-M so existe em anos censitarios)
   - Fontes com URL completa de consulta e data do acesso

## Regras fixas
- Nunca apresentar numero sem dizer de onde veio (URL da consulta).
- Nao inventar ID de tabela/variavel nem supor a serie: verificar na API; se incerto, escrever A VERIFICAR.
- Qualquer projecao ou estimativa entra marcada como ESTIMATIVA.
- Nao escrever o texto final pelo estudante: produzir rascunho e deixar abertas as escolhas humanas.
- LGPD: dados demograficos agregados, sem individuo identificado.

## Exemplo de saida
Painel Norte:
Definicao: PIB a precos correntes da tabela X (Fonte: IBGE SIDRA, acesso em yyyy-mm-dd).
Achado: Norte representa X% do PIB nacional em 2010, contra Y% em 2002 (derivado: razao entre PIB da regiao e total nacional, mesma fonte e anos).
Causa provavel: cada causa vem acompanhada de fonte especifica; causa sem citacao amarravel fica fora do relatorio.
Limitacao: serie a precos correntes pode comecar depois de 2002; IDH-M so existe em anos censitarios, entao a comparacao PIB x IDH se faz por marcar, nao por ano a ano.
