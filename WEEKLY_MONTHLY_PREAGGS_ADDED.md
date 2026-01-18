# Weekly/Monthly Pre-Aggregations Added

**Date**: January 18, 2026
**Purpose**: Optimize query performance for weekly and monthly reporting

---

## Changes Summary

Added weekly and monthly pre-aggregations to time-based cubes following the pattern established in `transaction_lines.yml`.

### Files Updated:

1. **transactions.yml** - Order/transaction header analysis
2. **fulfillments.yml** - Fulfillment/shipping analysis

---

## transactions.yml Changes

Added 2 new pre-aggregations:

### `orders_weekly`
- **Granularity**: week
- **Partition**: week
- **Use Case**: 1-3 month queries, weekly reporting
- **Performance**: ~7x faster than daily pre-agg for weekly queries
- **Measures**: All key order metrics (order_count, unique_customers, fulfilled_orders, etc.)
- **Dimensions**: type, status, billing_country, shipping_country, currency, customer_type

### `orders_monthly`
- **Granularity**: month
- **Partition**: month
- **Use Case**: 3+ month queries (12-month reports, YoY analysis)
- **Performance**: ~30x faster than daily pre-agg for monthly queries
- **Measures**: Same as weekly
- **Dimensions**: Same as weekly

---

## fulfillments.yml Changes

Added 2 new pre-aggregations:

### `fulfillment_weekly`
- **Granularity**: week
- **Partition**: week
- **Use Case**: Weekly operational reporting, shipping performance metrics
- **Performance**: ~7x faster than daily pre-agg
- **Measures**: fulfillment_count, unique_orders, shipped_count, pending_count
- **Dimensions**: status, status_name, shipcarrier

### `fulfillment_monthly`
- **Granularity**: month
- **Partition**: month
- **Use Case**: Long-range shipping trends, carrier analysis
- **Performance**: ~30x faster than daily pre-agg
- **Measures**: Same as weekly
- **Dimensions**: Same as weekly

---

## Configuration Details

All new pre-aggregations use:
- **build_range_end**: `SELECT '2025-10-31'` (consistent with transaction_lines)
- **refresh_key**: `every: 1 day` (daily incremental updates)
- **partition_granularity**: Matches data granularity (week for weekly, month for monthly)
- **indexes**: Strategic indexes on commonly filtered dimensions

---

## Performance Impact Estimates

### Weekly Queries (1-3 months):
- **Before**: Scan 90 daily pre-agg rows
- **After**: Scan ~13 weekly pre-agg rows
- **Improvement**: ~7x faster

### Monthly Queries (12 months):
- **Before**: Scan 365 daily pre-agg rows
- **After**: Scan 12 monthly pre-agg rows
- **Improvement**: ~30x faster

---

## Query Optimization Strategy

Cube.js will automatically select the optimal pre-aggregation:

1. **Daily queries (< 7 days)** → Use daily pre-agg
2. **Weekly queries (1-3 months)** → Use weekly pre-agg
3. **Monthly queries (3+ months)** → Use monthly pre-agg

No query changes required - optimization is transparent to end users.

---

## Next Phase Recommendations

### High Priority (Phase 2):
- `transaction_accounting_lines_cogs.yml` - COGS/margin analysis
- `fulfillment_lines.yml` - Detailed fulfillment line analysis

### Medium Priority (Phase 3):
- `item_receipt_lines.yml` - Receiving/procurement trends
- `landed_costs.yml` - Freight/duty cost analysis
- `purchase_order_lines.yml` - PO volume trends

### Do NOT Add:
- `inventory.yml` - Snapshot cube with no time dimension

---

## Validation

After deployment, verify pre-aggregations are being used:

```sql
-- Check pre-agg build status
SELECT * FROM cubedev_pre_aggregations.orders_weekly;
SELECT * FROM cubedev_pre_aggregations.orders_monthly;
SELECT * FROM cubedev_pre_aggregations.fulfillment_weekly;
SELECT * FROM cubedev_pre_aggregations.fulfillment_monthly;

-- Monitor query performance in Cube Cloud dashboard
-- Confirm weekly/monthly queries hit new pre-aggs
```

---

## Related Documentation

- [NETSUITE_INVENTORY_CALCULATION_GUIDE.md](../backend/NETSUITE_INVENTORY_CALCULATION_GUIDE.md) - Historical inventory calculation research
- Pattern based on transaction_lines.yml updates (revenue_analysis_weekly, revenue_analysis_monthly)

---

**Version**: 1.0
**Commit**: Weekly/monthly pre-aggs added to transactions and fulfillments cubes
