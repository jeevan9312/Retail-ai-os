SELECT
    INVENTORY_ID,
    PRODUCT_ID,
    WAREHOUSE_ID,
    CURRENT_STOCK_LEVEL::NUMBER     AS current_stock_level,
    SAFETY_STOCK_THRESHOLD::NUMBER  AS safety_stock_threshold,
    REORDER_POINT::NUMBER           AS reorder_point,
    LEAD_TIME_DAYS::NUMBER          AS lead_time_days,
    SHELF_LIFE_EXPIRY::DATE         AS shelf_life_expiry,
    LAST_RESTOCKED_AT               AS last_restocked_at,
    -- Derived
    CASE WHEN CURRENT_STOCK_LEVEL <= REORDER_POINT
         THEN TRUE ELSE FALSE END   AS needs_reorder,
    ROUND(CURRENT_STOCK_LEVEL / NULLIF(SAFETY_STOCK_THRESHOLD, 0), 2) AS stock_coverage_ratio,
    CURRENT_TIMESTAMP()             AS dbt_loaded_at
FROM {{ source('raw', 'raw_inventory') }}
WHERE INVENTORY_ID IS NOT NULL