SELECT
    s.SUPPLIER_ID,
    s.SUPPLIER_NAME,
    s.reliability_score,
    s.reliability_tier,
    s.COUNTRY,
    COUNT(b.BATCH_ID)               AS total_batches,
    SUM(b.QUANTITY)                 AS total_units_supplied,
    AVG(b.PROCUREMENT_COST)         AS avg_procurement_cost,
    AVG(b.UNIT_COST)                AS avg_unit_cost,
    CURRENT_TIMESTAMP()             AS dbt_loaded_at
FROM {{ ref('stg_suppliers') }} s
LEFT JOIN {{ source('raw', 'raw_batches') }} b
    ON s.SUPPLIER_ID = b.SUPPLIER_ID
GROUP BY
    s.SUPPLIER_ID, s.SUPPLIER_NAME,
    s.reliability_score, s.reliability_tier, s.COUNTRY