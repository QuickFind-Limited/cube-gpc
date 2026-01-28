# AOV Wholesale Inflation Fix - Implementation Summary

## Problem Statement

**Issue**: Average Order Value (AOV) metric was inflated by B2B wholesale orders
- Overall AOV showed €315.85 for July 2022
- When broken down: Online €31.39, Retail €83.10, Other €3,474.95
- B2B wholesale orders have much higher AOV (€500-2000) compared to consumer orders (€30-80)
- Users asking "what's our AOV?" typically want consumer/retail AOV, not including bulk B2B

**Root Cause**:
1. Single `average_order_value` measure included ALL channels (D2C, Retail, B2B Wholesale, B2B Corporate, B2B Marketplace)
2. Before channel_type fix (v63), wholesale transactions were in "OTHER" channel
3. No way to exclude B2B wholesale from AOV calculations

## Solution Implemented

Created two-measure approach for flexibility:

### 1. Updated `average_order_value` (existing measure)
- **Behavior**: UNCHANGED - still includes all channels
- **Updated Description**: Added warning about B2B inflation
- **Use Case**: Total business performance analysis
- **When to use**: "Show me AOV across all business channels including wholesale"

```yaml
- name: average_order_value
  sql: "1.0 * {total_revenue} / NULLIF({transaction_count}, 0)"
  type: number
  format: currency
  description: "Average order value (AOV) - ALL CHANNELS including B2B/wholesale.
    Uses count_distinct_approx for transaction counting (10-20% error margin acceptable).
    WARNING: B2B wholesale orders have much higher AOV (€500-2000) and will inflate
    this metric. For consumer/retail AOV analysis, use average_order_value_retail
    instead or filter out B2B_WHOLESALE, B2B_CORPORATE, and B2B_MARKETPLACE channels."
```

### 2. New `average_order_value_retail` (recommended measure)
- **Behavior**: Automatically excludes B2B_WHOLESALE, B2B_CORPORATE, B2B_MARKETPLACE
- **Use Case**: Consumer/retail AOV analysis, marketing performance, pricing strategy
- **When to use**: "What's our average order value?" (most common query)
- **Filter**: Uses channel_type dimension to exclude B2B channels

```yaml
- name: average_order_value_retail
  sql: "1.0 * {total_revenue} / NULLIF({transaction_count}, 0)"
  type: number
  format: currency
  filters:
    - sql: >
        {channel_type} NOT IN ('B2B_WHOLESALE', 'B2B_CORPORATE', 'B2B_MARKETPLACE')
  description: "Average order value for RETAIL/CONSUMER channels only (excludes B2B
    wholesale). Use this measure for consumer-facing AOV analysis, pricing strategy,
    and marketing performance. Represents typical consumer basket size without bulk
    B2B orders inflating the average. This is the RECOMMENDED measure for most AOV
    queries."
```

## Impact Analysis

### Q4 2024 Example (Actual Data)

| Metric | All Channels | Retail Only | Difference |
|--------|-------------|-------------|------------|
| **Total Revenue** | €12,121,387 | €11,562,142 | -€559,245 (-4.6%) |
| **Total Orders** | 226,990 | 225,891 | -1,099 (-0.5%) |
| **Average Order Value** | **€53.40** | **€51.18** | **-€2.22 (-4.1%)** |

### Channel Breakdown (Q4 2024)

| Channel | AOV | Revenue | Orders | % of Total |
|---------|-----|---------|--------|------------|
| D2C | €44.23 | €7,191,732 | 162,590 | 59.3% |
| RETAIL | €69.07 | €4,369,734 | 63,264 | 36.0% |
| **B2B_WHOLESALE** | **€568.64** | **€503,814** | **886** | **4.2%** |
| **B2B_CORPORATE** | **€1,895.62** | **€51,182** | **27** | **0.4%** |
| B2B_MARKETPLACE | €22.85 | €4,250 | 186 | 0.04% |
| OTHER | €17.42 | €627 | 36 | 0.01% |
| EVENTS | €49.00 | €49 | 1 | 0.0004% |

**Key Insight**: B2B wholesale represents only 0.5% of orders but inflates AOV by 4.1%

## Validation

### Pre-Deployment Validation
Run this query to test both measures:

```javascript
{
  "measures": [
    "transaction_lines.average_order_value",
    "transaction_lines.average_order_value_retail",
    "transaction_lines.total_revenue",
    "transaction_lines.transaction_count"
  ],
  "dimensions": ["transaction_lines.channel_type"],
  "timeDimensions": [{
    "dimension": "transaction_lines.transaction_date",
    "dateRange": ["2024-10-01", "2024-12-31"]
  }]
}
```

**Expected Results**:
- `average_order_value` shows overall AOV (all channels)
- `average_order_value_retail` shows lower AOV (excludes B2B)
- B2B channels show €0.00 for `average_order_value_retail`
- Non-B2B channels show same value for both measures

### Validation Script
```bash
cd /home/produser/cube-gpc
python3 test_aov_measures.py
```

## User Guidance

### When to Use Each Measure

**Use `average_order_value_retail` (RECOMMENDED) for**:
- "What's our average order value?"
- "Show me AOV this quarter"
- "How is our AOV trending?"
- Consumer marketing analysis
- Pricing strategy decisions
- Retail performance metrics
- Comparing online vs in-store shopping behavior

**Use `average_order_value` (ALL CHANNELS) for**:
- "Show me total business AOV including wholesale"
- "What's our AOV across all business channels?"
- Complete business performance analysis
- B2B vs Retail comparison (when you want to see B2B)

### Natural Language Query Mapping

| User Query | Recommended Measure | Reason |
|------------|-------------------|--------|
| "What's our AOV?" | `average_order_value_retail` | Most users want consumer AOV |
| "Show me average order value" | `average_order_value_retail` | Default to consumer context |
| "What's our AOV including wholesale?" | `average_order_value` | Explicitly includes B2B |
| "Average order value for all business" | `average_order_value` | "All business" = all channels |

## Dependencies

### Prerequisites
- Requires channel_type dimension v63 (with B2B channel classification)
- Channels must be properly classified: B2B_WHOLESALE, B2B_CORPORATE, B2B_MARKETPLACE

### Related Changes
- **v63 channel_type fix** (2025-01-28): Fixed channel classification to properly identify B2B wholesale
- This AOV fix builds on v63 by filtering based on channel_type

## Deployment Checklist

- [x] Update `average_order_value` description with B2B inflation warning
- [x] Create `average_order_value_retail` measure with B2B filter
- [x] Create validation script (`test_aov_measures.py`)
- [x] Document implementation (this file)
- [ ] Commit changes to git
- [ ] Push to GitHub
- [ ] Wait for Cube Cloud to pick up changes (~2-5 minutes)
- [ ] Run validation script to confirm measure works
- [ ] Update user documentation/training materials

## Rollback Plan

If issues occur, revert to single measure:

```yaml
- name: average_order_value
  sql: "1.0 * {total_revenue} / NULLIF({transaction_count}, 0)"
  type: number
  format: currency
  description: "Average order value (AOV) - revenue transactions only. This is the ONLY AOV measure - use for all queries."
```

Remove:
- `average_order_value_retail` measure
- Updated description on `average_order_value`

## Testing

### Manual Testing Steps
1. Query `average_order_value_retail` for Q4 2024
2. Verify AOV is ~€51 (not €53)
3. Query by channel_type and verify B2B channels show €0.00 for retail measure
4. Verify non-B2B channels show correct values

### Automated Testing
```bash
# Run full validation
python3 /home/produser/cube-gpc/test_aov_measures.py

# Expected output:
# ✅ SUCCESS: New retail AOV measure working correctly!
# ✅ PASSED: All B2B channels correctly excluded from retail AOV
# ✅ PASSED: Non-B2B channels have retail AOV values
```

## Version History

- **v64**: AOV wholesale fix implementation (2025-01-28)
  - Added `average_order_value_retail` measure
  - Updated `average_order_value` description
  - Created validation scripts and documentation

## Notes

1. **Why Two Measures Instead of Changing Default?**
   - Historical consistency: Existing dashboards/reports using `average_order_value` continue to work
   - Flexibility: Users can choose based on their analysis needs
   - Clear intent: Measure name indicates what's included

2. **Error Margin**: Both measures use `count_distinct_approx` with 10-20% error margin, which is acceptable for business analysis

3. **Future Consideration**: If all users prefer retail-only AOV, could deprecate the all-channels measure in future version

4. **Related to RM002 Metric**: This fix directly addresses the RM002 (Average Order Value) issue where wholesale orders were inflating the metric

## Contact

For questions or issues:
- Cube.js schema: `/home/produser/cube-gpc/model/cubes/transaction_lines.yml`
- Validation scripts: `/home/produser/cube-gpc/test_aov_*.py`
- Related docs: `CHANNEL_FIX_IMPLEMENTATION_SUMMARY.md`
