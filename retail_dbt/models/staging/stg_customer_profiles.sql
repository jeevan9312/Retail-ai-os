SELECT
    CUSTOMER_ID,
    DEMOGRAPHIC_SEGMENT,
    LOYALTY_POINTS::NUMBER          AS loyalty_points,
    LAST_PURCHASE_DATE::DATE        AS last_purchase_date,
    APP_SESSION_DURATION::FLOAT     AS app_session_duration,
    CASE WHEN LOYALTY_POINTS >= 1000 THEN 'GOLD'
         WHEN LOYALTY_POINTS >= 500  THEN 'SILVER'
         ELSE 'BRONZE' END          AS loyalty_tier,
    CURRENT_TIMESTAMP()             AS dbt_loaded_at
FROM {{ source('raw', 'raw_customer_profiles') }}
WHERE CUSTOMER_ID IS NOT NULL