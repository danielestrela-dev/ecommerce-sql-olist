-- SQLite 3.25+. Grão final: exatamente uma linha por pedido entregue válido.
DROP VIEW IF EXISTS fact_orders;
CREATE VIEW fact_orders AS
WITH ranked_reviews AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY order_id
        ORDER BY review_answer_timestamp DESC, review_creation_date DESC,
                 review_id DESC, CAST(review_score AS INTEGER) DESC
    ) AS rn
    FROM reviews
), item_totals AS (
    SELECT order_id, SUM(CAST(price AS REAL)) AS merchandise_value,
           SUM(CAST(freight_value AS REAL)) AS freight_value
    FROM items GROUP BY order_id
), payment_totals AS (
    SELECT order_id, SUM(CAST(payment_value AS REAL)) AS payment_value
    FROM payments GROUP BY order_id
)
SELECT o.order_id, c.customer_state AS state,
       substr(o.order_purchase_timestamp, 1, 7) AS month,
       date(o.order_purchase_timestamp) AS purchased_on,
       date(o.order_delivered_customer_date) AS delivered_on,
       date(o.order_estimated_delivery_date) AS estimated_on,
       -- Prazo comparado por data: a previsão não tem hora útil.
       CASE WHEN date(o.order_delivered_customer_date) > date(o.order_estimated_delivery_date)
            THEN 1 ELSE 0 END AS is_late,
       MAX(0, julianday(date(o.order_delivered_customer_date)) -
              julianday(date(o.order_estimated_delivery_date))) AS delay_days,
       julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp) AS delivery_days,
       CAST(r.review_score AS INTEGER) AS score,
       CASE WHEN r.review_answer_timestamp >= o.order_delivered_customer_date THEN 1 ELSE 0 END AS post_delivery_review,
       i.merchandise_value, i.freight_value, p.payment_value
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN ranked_reviews r ON r.order_id = o.order_id AND r.rn = 1
LEFT JOIN item_totals i ON i.order_id = o.order_id
LEFT JOIN payment_totals p ON p.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND julianday(o.order_purchase_timestamp) IS NOT NULL
  AND julianday(o.order_delivered_customer_date) IS NOT NULL
  AND julianday(o.order_estimated_delivery_date) IS NOT NULL
  AND o.order_delivered_customer_date >= o.order_purchase_timestamp;
