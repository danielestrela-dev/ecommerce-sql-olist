# Entrega & experiência 📦

**Como os atrasos nas entregas se relacionam com as avaliações dos clientes?**

Projeto de portfólio de Daniel Estrela com SQL, SQLite e Python. Usa dados públicos reais da Olist e apresenta resultados em uma página interativa, com filtros de estado e mês da compra.

**[Abrir análise online](https://danielestrela-dev.github.io/ecommerce-sql-olist/)** · [Consultas SQL](sql/02_analysis.sql) · [Resultados em CSV](results/)

## Principais resultados

| Indicador | Resultado |
|---|---:|
| Pedidos entregues com datas válidas | 96.470 |
| Pedidos atrasados | 6.534 (6,77%) |
| Nota média dos pedidos no prazo | 4,29 / 5 |
| Nota média dos pedidos atrasados | 2,27 / 5 |
| Notas 1 ou 2 entre avaliados no prazo | 9,27% |
| Notas 1 ou 2 entre avaliados com atraso | 62,42% |

**O detalhe mais importante:** muitas avaliações dos pedidos atrasados foram respondidas antes da entrega. Ao restringir a análise às respostas após a entrega, as médias são **4,29 no prazo** (89.263 avaliações) e **3,72 com atraso** (1.908 avaliações). Portanto, o momento da avaliação muda bastante a comparação. A seleção desse subgrupo também pode introduzir viés.

Os resultados mostram associação, sem estabelecer que o atraso causou a diferença de notas. São dados históricos; não representam o desempenho atual da Olist.

## Decisões de análise

- **Grão:** uma linha por pedido. Itens e pagamentos são agregados antes das junções para evitar multiplicação de valores e contagens.
- **Universo:** dos 99.441 pedidos originais, 96.478 têm status `delivered`. Oito são excluídos por datas ausentes ou entrega anterior à compra. Restam 96.470.
- **Atraso:** `data da entrega > data prevista`. A comparação usa dias de calendário; a hora da entrega no dia previsto não gera um falso atraso.
- **Avaliação:** última resposta por pedido usando `ROW_NUMBER`. Há 551 linhas de avaliação além da quantidade de pedidos distintos. Critério de desempate: data da resposta, data de criação, ID e nota, todos em ordem decrescente.
- **Sem avaliação:** 646 pedidos permanecem no denominador da taxa de atraso, mas são excluídos da média de notas e da proporção de notas baixas.
- **Nota baixa:** nota 1 ou 2, dividida pelo total de pedidos avaliados do respectivo grupo.
- **Tempo:** o mês dos gráficos corresponde à compra. O recorte válido tem compras de 15/09/2016 a 29/08/2018; meses de fronteira são incompletos.
- **Ranking de estados:** mínimo de 100 pedidos no recorte para reduzir comparações com amostras muito pequenas. Isso não garante estabilidade estatística.

## Habilidades demonstradas

`JOIN` · `GROUP BY` · `CASE WHEN` · CTEs · `ROW_NUMBER` · `DENSE_RANK` · `LAG` · tratamento de nulos · validação de dados · análise de sensibilidade · comunicação de resultados.

O SQL faz a transformação e os cálculos. Python cuida da leitura dos CSVs, execução das consultas, verificações e exportação; usa somente a biblioteca padrão. A página usa HTML, CSS e JavaScript, sem servidor de aplicação.

## Reproduzir

Requer **Python 3.10+**, com SQLite **3.25+** (funções de janela).

```bash
git clone https://github.com/danielestrela-dev/ecommerce-sql-olist.git
cd ecommerce-sql-olist
python scripts/build.py
```

O script baixa o ZIP oficial do Kaggle, importa cinco tabelas, executa o modelo e as cinco análises e gera o banco local, o JSON do painel, os CSVs e o manifesto com hashes SHA-256. Não é preciso instalar pacotes.

Se o download automático estiver indisponível, baixe o ZIP pela [página oficial](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), salve como `data/raw/olist.zip` e rode novamente. Os hashes de referência estão em [data/manifest.json](data/manifest.json); mudanças na fonte podem alterar resultados.

Para ver a página localmente:

```bash
python -m http.server 8000 --directory docs
```

Abra `http://localhost:8000`. Para consultar o banco em uma ferramenta SQL, abra `data/olist.sqlite` e execute [sql/02_analysis.sql](sql/02_analysis.sql). A view `fact_orders` já estará criada.

## Estrutura

```text
sql/01_model.sql       # Modelo no grão de pedido e tratamento dos dados
sql/02_analysis.sql    # Cinco consultas comentadas
scripts/build.py      # Reprodução completa e verificações
results/              # Saídas das consultas em CSV
data/manifest.json    # Contagens, recorte e hashes da fonte
docs/                 # Página pública e dados agregados
```

O pipeline verifica unicidade de pedidos e clientes, ausência de multiplicação nas junções, domínio das notas e reconciliação dos agregados com a base final. Os dados brutos e o banco não são versionados; a página publica somente agregados, sem textos de avaliações ou identificadores de clientes.

## Recomendações e próximos passos

1. Investigar rotas com alto volume e atraso elevado, cruzando com vendedor e categoria antes de recomendar mudanças operacionais.
2. Testar comunicação proativa para entregas em risco, com um experimento e métricas definidos antecipadamente.
3. Comparar clientes semelhantes e controlar fatores como estado, categoria e período. O projeto atual não faz ajuste causal nem testa significância estatística.

O valor de mercadorias na consulta geral soma `price` dos itens dos pedidos válidos. Não é lucro, receita líquida ou total pago; frete e pagamentos são medidas separadas.

## Fonte e atribuição

**Olist — Brazilian E-Commerce Public Dataset**, disponibilizado no [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). A base original está sob [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Os resultados e agregados derivados aqui são compartilhados sob a mesma licença, para uso não comercial, com atribuição e compartilhamento pela mesma licença. Transformações: seleção de tabelas, limpeza, deduplicação, junções e agregação.

Projeto educacional independente, sem vínculo com a Olist. Elaborado com apoio de IA na implementação e documentação.
