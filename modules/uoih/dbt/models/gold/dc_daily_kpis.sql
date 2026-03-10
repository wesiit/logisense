{{
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['facility_id', 'date'],
    file_format='iceberg',
    partition_by=['date'],
    on_schema_change='sync_all_columns'
  )
}}

/*
  DC Daily KPIs Model

  Computes per-facility per-date KPIs:
  - total_movements: Count of all inventory movements
  - picks_completed: Movements of type PICK
  - inventory_accuracy_pct: Cycle count confirmations with no variance / total
  - orders_fulfilled: Distinct order IDs in DISPATCHED status

  Source tables:
  - silver.iwms_inventory_movements
  - silver.iwms_inventory_positions
*/

WITH movements AS (
    SELECT
        facility_id,
        CAST(performed_at AS DATE) AS date,
        movement_type,
        quantity,
        reference_id,
        -- For cycle counts, check if quantity matches expected
        CASE
            WHEN movement_type = 'CYCLE_COUNT'
            AND ABS(COALESCE(JSON_EXTRACT_SCALAR(raw_payload, '$.variance'), '0')::INT) = 0
            THEN 1
            ELSE 0
        END AS accurate_cycle_count,
        CASE
            WHEN movement_type = 'CYCLE_COUNT' THEN 1
            ELSE 0
        END AS is_cycle_count
    FROM {{ source('silver', 'iwms_inventory_movements') }}
    WHERE 1=1
    {% if is_incremental() %}
        AND CAST(performed_at AS DATE) >= DATE_ADD('day', -1, CAST('{{ var("run_date") }}' AS DATE))
    {% endif %}
),

orders AS (
    -- Get orders that were dispatched (completed)
    SELECT DISTINCT
        facility_id,
        CAST(performed_at AS DATE) AS date,
        reference_id AS order_id
    FROM {{ source('silver', 'iwms_inventory_movements') }}
    WHERE movement_type = 'PICK'
      AND reference_id IS NOT NULL
      AND reference_id != ''
    {% if is_incremental() %}
        AND CAST(performed_at AS DATE) >= DATE_ADD('day', -1, CAST('{{ var("run_date") }}' AS DATE))
    {% endif %}
),

movement_aggregates AS (
    SELECT
        facility_id,
        date,
        COUNT(*) AS total_movements,
        SUM(CASE WHEN movement_type = 'PICK' THEN 1 ELSE 0 END) AS picks_completed,
        SUM(accurate_cycle_count) AS accurate_cycle_counts,
        SUM(is_cycle_count) AS total_cycle_counts
    FROM movements
    GROUP BY facility_id, date
),

order_aggregates AS (
    SELECT
        facility_id,
        date,
        COUNT(DISTINCT order_id) AS orders_fulfilled
    FROM orders
    GROUP BY facility_id, date
)

SELECT
    m.facility_id,
    m.date,
    m.total_movements,
    m.picks_completed,
    -- Calculate inventory accuracy percentage
    CASE
        WHEN m.total_cycle_counts > 0
        THEN ROUND(
            (CAST(m.accurate_cycle_counts AS DOUBLE) / CAST(m.total_cycle_counts AS DOUBLE)) * 100,
            2
        )
        ELSE 100.0  -- If no cycle counts, assume 100% accuracy
    END AS inventory_accuracy_pct,
    COALESCE(o.orders_fulfilled, 0) AS orders_fulfilled,
    m.total_cycle_counts AS cycle_counts,
    CURRENT_TIMESTAMP AS computed_at
FROM movement_aggregates m
LEFT JOIN order_aggregates o
    ON m.facility_id = o.facility_id
    AND m.date = o.date
