# Validação empírica do FIGEM nos municípios chilenos

[Español](README.md) · [English](README.en.md) · [Português](README.pt-BR.md)

Repositório reproduzível associado a:

> Montecinos García, R. S., & Vega Toledo, E. (2025). *Validación empírica
> del FIGEM en municipios chilenos: tipologías fiscales y evaluación
> cuantitativa*. Revista Políticas Públicas, 18(2), 3–21.

O artigo avalia se os grupos normativos do Fundo de Incentivo à Melhoria da
Gestão Municipal (FIGEM) agrupam municípios fiscalmente comparáveis, utilizando
dados do SINIM e registros do FIGEM para 345 municípios no período de 2016 a
2024.

## Pipeline reproduzível

O `src/Clustering_USACH.py` reproduz:

1. a imputação documentada de valores FIGEM ausentes;
2. a construção de variáveis per capita;
3. a análise de componentes principais (PCA) do desenvolvimento fiscal relativo;
4. a avaliação do K-Means para `k=2..6` e a solução final `k=4`;
5. as tipologias fiscais com rótulos semânticos estáveis;
6. a matriz FIGEM-clusters e o Kappa de Cohen como indicador complementar;
7. o modelo de painel com efeitos fixos municipais e anuais, com erros-padrão HC3;
8. os testes de robustez com dez sementes;
9. as tabelas e figuras de apoio do artigo.

A solução `k=4` é mantida pelo equilíbrio entre desempenho estatístico,
interpretabilidade e utilidade para avaliação de políticas. Embora `k=3`
apresente o maior coeficiente de silhueta, a escolha de `k=4` é uma decisão
analítica substantiva, e não uma maximização automática da métrica.

O `src/generador_graficos_USACH.py` recria as seis figuras do artigo a partir
do resultado reproduzido.

## Reprodução

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python src/Clustering_USACH.py
python src/generador_graficos_USACH.py
```

O pipeline lê `data/Input_USACH.xlsx` e grava o resultado rastreável com 17
planilhas em `data/Output_USACH.xlsx`.

Execute `python scripts/verify_reproduction.py` para verificar os principais
resultados publicados no artigo.

Os resultados esperados incluem:

```text
345 municípios
PCA1: 81,0%
Silhouette k=4: 0,2376
Kappa: -0,0095
Discrepância modal: 48,7%
R² within: 0,1495
```

A discrepância de 48,7% é o complemento da concordância modal por linha na
tabela de cinco grupos FIGEM por quatro clusters. Ela não representa uma
medida estrita de acurácia de classificação um-a-um.

## Escopo e limitações

O estudo é avaliativo, não causal. Os efeitos fixos identificam associações
intra-municipais, não efeitos causais. A imputação dos valores FIGEM está
documentada na planilha `01_Imputacion_FIGEM` e não substitui as observações
originais.

A proposta de redesenho híbrido apresentada no artigo é uma hipótese de
política pública. Qualquer implementação exigiria simulação distributiva,
análise de ganhadores e perdedores e uma transição gradual.

O código é distribuído sob a licença MIT. Os dados de origem são informações
públicas do SINIM/FIGEM, baixadas manualmente e consolidadas pelos autores. A
procedência e a atribuição estão documentadas em
`docs/DATA-AND-LICENSE.md`.

O GitHub Actions compila automaticamente os scripts e verifica os principais
resultados publicados no artigo.

## Estrutura

```text
data/
  Input_USACH.xlsx
  Output_USACH.xlsx
src/
  Clustering_USACH.py
  generador_graficos_USACH.py
figuras/
docs/
  Cuaderno_Metodologico_FIGEM.docx
requirements.txt
```
