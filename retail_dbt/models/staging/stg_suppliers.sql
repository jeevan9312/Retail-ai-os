SELECT
    SUPPLIER_ID,
    SUPPLIER_NAME,
    CONTACT_EMAIL,
    CITY,
    STATE,
    COUNTRY,
    RELIABILITY_SCORE::FLOAT        AS reliability_score,
    ACTIVE::BOOLEAN                 AS active,
    CASE WHEN RELIABILITY_SCORE >= 0.8 THEN 'HIGH'
         WHEN RELIABILITY_SCORE >= 0.5 THEN 'MEDIUM'
         ELSE 'LOW' END             AS reliability_tier,
    CURRENT_TIMESTAMP()             AS dbt_loaded_at
FROM {{ source('raw', 'raw_suppliers') }}
WHERE SUPPLIER_ID IS NOT NULL