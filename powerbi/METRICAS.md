# Métricas, critérios e decisões

Todos os recortes de tempo usam a **data da compra**, inclusive os de logística. Os indicadores respeitam os filtros de estado e mês e as seleções dos visuais na página.

| Métrica | Cálculo e universo | Valor geral | Decisão apoiada |
|---|---|---:|---|
| Vendas | Soma de `price` dos itens de pedidos com status `delivered`, sem frete | R$ 13.221.498,11 | Dimensionar a operação comercial |
| Ticket médio | Vendas / pedidos entregues | R$ 137,04 | Investigar mudanças de mix e valor por pedido |
| Pedidos | Todos os status, uma linha por pedido | 99.441 | Entender demanda e volume |
| Pedidos entregues | Apenas `delivered` | 96.478 | Denominador do ticket |
| Cancelados | Apenas `canceled`; `unavailable` não entra como cancelamento | 625 | Investigar perdas operacionais |
| Taxa de cancelamento | Cancelados / todos os pedidos | 0,63% | Comparar períodos com o volume como contexto |
| Entregas válidas | Entregues com compra, previsão e entrega presentes e válidas; entrega não anterior à compra | 96.470 | Denominador confiável de logística |
| Entregas atrasadas | Data da entrega maior que a data prevista | 6.534 | Identificar volume afetado |
| Taxa de atraso | Atrasadas / entregas válidas | 6,77% | Priorizar investigação de rotas e períodos |
| Prazo médio | Média dos dias corridos fracionários entre compra e entrega, somente entregas válidas | 12,56 dias | Investigar gargalos e planejar prazos |

## Por que os universos são diferentes?

Para calcular cancelamento, é preciso manter pedidos cancelados. Para calcular prazo, é preciso uma entrega válida. Portanto, reaproveitar apenas o recorte de 96.470 entregas do estudo SQL tornaria o indicador de cancelamento incorreto.

As oito entregas com datas inválidas continuam nas vendas e no ticket porque têm status entregue e valor de produtos; são excluídas somente dos indicadores de prazo e atraso. Pedidos ainda em processamento ou sem disponibilidade não são reclassificados como cancelados.

## Como interpretar os gráficos

| Gráfico | Pergunta de negócio | Próxima ação possível |
|---|---|---|
| Vendas mensais | Em quais períodos o volume financeiro cresce? | Conferir calendário comercial e capacidade operacional |
| Ticket mensal | A mudança no valor de vendas acompanha o valor por pedido? | Investigar categorias, preços e promoções antes de atribuir causa |
| Cancelamento mensal | Quais períodos concentram taxas maiores? | Investigar estoque, aprovação e atendimento |
| Vendas por estado | Onde está a maior participação comercial? | Cruzar demanda com atendimento e logística |
| Atraso mensal | Quais coortes de compras enfrentaram pior cumprimento do prazo? | Investigar eventos operacionais e capacidade do período |
| Prazo por estado | Quais estados levam mais tempo para receber? | Avaliar distância, promessa de entrega e rotas |
| Tabela de estados | O problema combina taxa elevada e volume relevante? | Priorizar por impacto e contexto, não somente pela maior taxa |

Prazo alto não significa necessariamente atraso: uma entrega pode demorar mais e cumprir o prazo prometido. Os dois indicadores devem ser analisados em conjunto.

## Amostras pequenas e meses incompletos

O cartão geral de cancelamento inclui todos os pedidos. O gráfico mensal usa `Taxa cancelamento elegivel`, que retorna em branco com menos de 100 pedidos no contexto. Isso evita destacar setembro e outubro de 2018, que têm somente 16 e 4 pedidos e nenhuma entrega, como se fossem meses comparáveis aos demais.

Prazo e taxa no detalhamento de estados ficam em branco com menos de 100 entregas válidas no contexto. A tabela mantém as contagens para dar transparência ao tamanho do recorte. Meses de início e término da base não representam períodos completos.

O gráfico mensal de atraso também exige pelo menos 100 entregas válidas, evitando destacar meses com uma única entrega. O cartão geral de atraso continua usando todas as entregas válidas.

## Comparação mensal

As medidas `Vendas mes anterior (R$)` e `Variacao mensal vendas` estão disponíveis no modelo para ampliar o painel. Usam `DATEADD` em um calendário contínuo. Sem vendas no período de comparação, a variação retorna em branco. Para interpretação mensal, selecione um mês ou use o contexto de uma linha/gráfico por mês; comparar um conjunto arbitrário de meses com seu deslocamento não equivale a uma única variação mês a mês.
