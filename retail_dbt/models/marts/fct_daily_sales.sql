SELECT
    transaction_date,
    STORE_ID,
    PRODUCT_ID,
    COUNT(TRANSACTION_ID)           AS total_transactions,
    SUM(quantity_sold)              AS total_units_sold,
    SUM(gross_amount)               AS total_gross_revenue,
    SUM(net_amount)                 AS total_net_revenue,
    AVG(unit_price)                 AS avg_unit_price,
    AVG(discount_applied)           AS avg_discount,
    CURRENT_TIMESTAMP()             AS dbt_loaded_at
FROM {{ ref('stg_transactions') }}
GROUP BY transaction_date, STORE_ID, PRODUCT_ID