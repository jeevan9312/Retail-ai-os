SELECT
    PRODUCT_ID,
    PRODUCT_NAME,
    CATEGORY,
    SUBCATEGORY,
    UNIT_OF_MEASURE,
    SHELF_LIFE_DAYS::NUMBER         AS shelf_life_days,
    REQUIRES_REFRIGERATION::BOOLEAN AS requires_refrigeration,
    SKU,
    CURRENT_TIMESTAMP()             AS dbt_loaded_at
FROM {{ source('raw', 'raw_products') }}
WHERE PRODUCT_ID IS NOT NULL