-- A. Visão geral. Taxa de atraso usa todos os pedidos válidos.
SELECT COUNT(*) AS orders, SUM(is_late) AS late_orders,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS late_pct,
       COUNT(score) AS reviewed_orders, ROUND(AVG(score), 2) AS avg_score,
       ROUND(SUM(merchandise_value), 2) AS merchandise_value
FROM fact_orders;

-- B. Associação entre atraso e satisfação; notas baixas = 1 ou 2.
SELECT is_late, COUNT(*) AS orders, COUNT(score) AS reviewed,
       ROUND(AVG(score), 3) AS avg_score,
       ROUND(100.0 * SUM(CASE WHEN score <= 2 THEN 1 ELSE 0 END) / NULLIF(COUNT(score), 0), 2) AS low_score_pct
FROM fact_orders GROUP BY is_late;

-- C. CTE e ranking: estados com pelo menos 100 pedidos válidos.
WITH states AS (
    SELECT state, COUNT(*) AS orders, SUM(is_late) AS late_orders,
           100.0 * SUM(is_late) / COUNT(*) AS late_pct
    FROM fact_orders GROUP BY state HAVING COUNT(*) >= 100
)
SELECT *, DENSE_RANK() OVER (ORDER BY late_pct DESC) AS delay_rank
FROM states ORDER BY delay_rank, state;

-- D. Evolução mensal e comparação com o mês anterior.
WITH monthly AS (
    SELECT month, COUNT(*) AS orders,
           100.0 * SUM(is_late) / COUNT(*) AS late_pct
    FROM fact_orders GROUP BY month
)
SELECT *, ROUND(late_pct - LAG(late_pct) OVER (ORDER BY month), 2) AS change_pp
FROM monthly ORDER BY month;

-- E. Sensibilidade: somente avaliações respondidas após a entrega.
SELECT is_late, COUNT(*) AS reviewed, ROUND(AVG(score), 3) AS avg_score,
       ROUND(100.0 * SUM(score <= 2) / COUNT(*), 2) AS low_score_pct
FROM fact_orders WHERE score IS NOT NULL AND post_delivery_review = 1 GROUP BY is_late;
