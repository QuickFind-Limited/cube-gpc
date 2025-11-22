# Pre-Aggregations Issue and Fix

## Issue

Pre-aggregations in `transaction_lines.yml` were causing this error:

```
This pre-aggregation matches no queries. Please check if join paths in this pre-aggregation are correct
and if there are no conflicting pre-aggregations that matches same set of queries earlier.
```

## Root Cause

The pre-aggregation was referencing dimensions from joined cubes directly:

```yaml
pre_aggregations:
  - name: main_rollup
    dimensions:
      - channel_type           # Local dimension - OK
      - locations.region       # Joined cube dimension - PROBLEM
      - items.category         # Joined cube dimension - PROBLEM
      - items.season           # Joined cube dimension - PROBLEM
      - transactions.type      # Joined cube dimension - PROBLEM
    time_dimension: transactions.trandate  # Joined cube - PROBLEM
```

Cube.js pre-aggregations cannot directly reference dimensions from joined cubes using dot notation. The pre-aggregation needs to reference dimensions that are defined locally in the cube.

## Temporary Fix

Pre-aggregations were disabled (commented out) to allow the schema to compile and queries to work without optimization.

## Proper Fix

To re-enable pre-aggregations, add local dimension references in `transaction_lines.yml` that wrap the joined cube fields:

### Step 1: Add Local Dimensions

```yaml
dimensions:
  # ... existing dimensions ...

  # Add these local references for pre-aggregation support
  - name: item_category
    sql: "{items.category}"
    type: string
    description: Product category (for pre-aggregation)

  - name: item_season
    sql: "{items.season}"
    type: string
    description: Product season (for pre-aggregation)

  - name: item_size
    sql: "{items.size}"
    type: string
    description: Product size (for pre-aggregation)

  - name: item_range
    sql: "{items.range}"
    type: string
    description: Product range (for pre-aggregation)

  - name: location_region
    sql: "{locations.region}"
    type: string
    description: Location region (for pre-aggregation)

  - name: transaction_type
    sql: "{transactions.type}"
    type: string
    description: Transaction type (for pre-aggregation)

  - name: transaction_billing_country
    sql: "{transactions.billing_country}"
    type: string
    description: Billing country (for pre-aggregation)

  - name: transaction_date
    sql: "CAST({transactions.trandate} AS TIMESTAMP)"
    type: time
    description: Transaction date (for pre-aggregation)
```

### Step 2: Update Pre-Aggregation

```yaml
pre_aggregations:
  - name: main_rollup
    measures:
      - total_revenue
      - net_revenue
      - units_sold
      - units_returned
      - total_tax
      - line_count
    dimensions:
      - channel_type
      - location_region          # Now local
      - item_category            # Now local
      - item_season              # Now local
      - item_size                # Now local
      - item_range               # Now local
      - transaction_type         # Now local
      - transaction_billing_country  # Now local
    time_dimension: transaction_date  # Now local
    granularity: day
    partition_granularity: month
    refresh_key:
      every: 1 hour
    indexes:
      - name: channel_idx
        columns:
          - channel_type
          - transaction_date
      - name: product_idx
        columns:
          - item_category
          - item_season
          - transaction_date
      - name: region_idx
        columns:
          - location_region
          - channel_type
          - transaction_date
      - name: country_idx
        columns:
          - transaction_billing_country
          - transaction_date
```

## Alternative Approach

If you don't need pre-aggregations immediately, queries will still work - they'll just hit the raw data directly without the performance optimization of pre-computed rollups.

Pre-aggregations are most valuable when:
- You have large datasets (millions of rows)
- You have frequently repeated queries
- Query latency needs to be sub-second

## References

- [Cube.js Pre-Aggregations Documentation](https://cube.dev/docs/caching/pre-aggregations)
- [Cube.js Joins Documentation](https://cube.dev/docs/schema/reference/joins)
