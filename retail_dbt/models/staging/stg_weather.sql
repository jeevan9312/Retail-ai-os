SELECT
    ID                              AS weather_id,
    OBSERVATION_DATE::DATE          AS observation_date,
    TEMPERATURE::FLOAT              AS temperature,
    PRECIPITATION_LEVEL::FLOAT      AS precipitation_level,
    HUMIDITY::FLOAT                 AS humidity,
    WEATHER_CONDITION_CODE,
    CASE WHEN PRECIPITATION_LEVEL > 5  THEN 'RAINY'
         WHEN TEMPERATURE > 30        THEN 'HOT'
         WHEN TEMPERATURE < 10        THEN 'COLD'
         ELSE 'NORMAL' END            AS weather_category,
    CURRENT_TIMESTAMP()             AS dbt_loaded_at
FROM {{ source('raw', 'raw_weather') }}