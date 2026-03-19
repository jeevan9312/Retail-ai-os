SELECT
    i.INVENTORY_ID,
    i.PRODUCT_ID,
    i.WAREHOUSE_ID,
    i.current_stock_level,
    i.safety_stock_threshold,
    i.reorder_point,
    i.lead_time_days,
    i.needs_reorder,
    i.stock_coverage_ratio,
    p.PRODUCT_NAME,
    p.CATEGORY,
    p.requires_refrigeration,
    CASE
        WHEN i.current_stock_level = 0    THEN 'OUT_OF_STOCK'
        WHEN i.needs_reorder = TRUE       THEN 'REORDER_NOW'
        WHEN i.stock_coverage_ratio < 1.5 THEN 'LOW_STOCK'
        ELSE 'HEALTHY'
    END                             AS stock_status,
    CURRENT_TIMESTAMP()             AS dbt_loaded_at
FROM {{ ref('stg_inventory') }} i
LEFT JOIN {{ ref('stg_products') }} p
    ON i.PRODUCT_ID = p.PRODUCT_ID