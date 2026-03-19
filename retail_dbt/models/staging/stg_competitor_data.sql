SELECT
    ID                                  AS competitor_record_id,
    OBSERVATION_DATE::DATE              AS observation_date,
    COMPETITOR_ID,
    COMPETITOR_PRICE::FLOAT             AS competitor_price,
    MARKET_SHARE_PERCENTAGE::FLOAT      AS market_share_pct,
    TREND_SCORE::FLOAT                  AS trend_score,
    CURRENT_TIMESTAMP()                 AS dbt_loaded_at
FROM {{ source('raw', 'raw_competitor_data') }}