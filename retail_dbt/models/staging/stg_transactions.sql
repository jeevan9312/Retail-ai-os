SELECT
    TRANSACTION_ID,
    TIMESTAMP                                                           AS transaction_timestamp,
    PRODUCT_ID,
    QUANTITY_SOLD::NUMBER                                               AS quantity_sold,
    UNIT_PRICE::FLOAT                                                   AS unit_price,
    DISCOUNT_APPLIED::FLOAT                                             AS discount_applied,
    PAYMENT_METHOD,
    STORE_ID,
    ROUND(UNIT_PRICE * QUANTITY_SOLD, 2)                                AS gross_amount,
    ROUND(UNIT_PRICE * QUANTITY_SOLD * (1 - DISCOUNT_APPLIED/100), 2)  AS net_amount,
    DATE(TIMESTAMP)                                                     AS transaction_date,
    CURRENT_TIMESTAMP()                                                 AS dbt_loaded_at
FROM {{ source('raw', 'raw_transactions') }}
WHERE TRANSACTION_ID IS NOT NULL
  AND QUANTITY_SOLD > 0
  AND UNIT_PRICE > 0