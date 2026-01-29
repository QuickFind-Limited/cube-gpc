# HIGH RISK Metrics Test Results - Detailed Analysis

**Test Date**: January 18, 2026
**Total Tests**: 8
**Results**: 2 PASSED, 2 FAILED (timeout), 4 ERROR (bugs)

---

## Summary Table

| Test ID | Metric | Status | Duration | Issue Type |
|---------|--------|--------|----------|------------|
| MM001 | Gross Margin % (GL COGS) | ERROR | 0.59s | 500 - Missing dimension |
| GMROI001 | GMROI (GL COGS) | ERROR | 0.46s | 500 - Missing dimension |
| LIFE004 | Units Per Week | ERROR | 0.61s | 400 - Pre-agg not built |
| RET004 | Return Rate Components | ✅ PASSED | 1.01s | None |
| RET005 | Return Rate % | FAILED | 13.85s | Timeout - needs optimization |
| FD002 | Fulfillments Per Order | ✅ PASSED | 0.31s | None |
| MM001_COMP | Revenue + GL COGS | ERROR | 0.24s | 500 - Missing dimension |
| COGS_DIRECT | GL COGS Direct | FAILED | 11.33s | Timeout - needs optimization |

---

## Detailed Analysis (To Be Completed)

### ✅ PASSED Tests (2)

#### RET004 - Return Rate Components
- **Status**: PASSED (1.01s)
- **Query**: customer_credits_aligned, revenue_transaction_count_aligned by customer_type
- **Why it works**: TBD - needs investigation
- **Pre-agg used**: TBD

#### FD002 - Fulfillments Per Order
- **Status**: PASSED (0.31s)
- **Query**: fulfillments_per_order by status_name
- **Why it works**: TBD - needs investigation
- **Pre-agg used**: TBD

---

### ❌ ERROR Tests (4)

#### MM001 - Gross Margin % (GL-based COGS)
- **Status**: ERROR 500 (0.59s)
- **Error Message**: `transaction_accounting_lines_cogs.transaction_id cannot be resolved`
- **Root Cause**: CONFIRMED - Missing transaction_id dimension in COGS cube
- **Fix Applied**: Added transaction_id dimension
- **Status**: FIXED ✅
- **Needs Re-test**: Yes

#### GMROI001 - GMROI (GL-based COGS)
- **Status**: ERROR 500 (0.46s)
- **Error Message**: TBD - needs curl test
- **Root Cause**: ASSUMED - Same as MM001
- **Fix Applied**: Same fix (transaction_id dimension)
- **Status**: ASSUMED FIXED
- **Needs Re-test**: Yes

#### MM001_COMP - Revenue + GL COGS Components
- **Status**: ERROR 500 (0.24s)
- **Error Message**: TBD - needs curl test
- **Root Cause**: ASSUMED - Same as MM001
- **Fix Applied**: Same fix (transaction_id dimension)
- **Status**: ASSUMED FIXED
- **Needs Re-test**: Yes

#### LIFE004 - Units Per Week
- **Status**: ERROR 400 (0.61s)
- **Error Message**: `No pre-aggregation table has been built for this query yet`
- **Root Cause**: UNKNOWN - needs investigation
- **Possible Causes**:
  1. Measure not in any pre-aggregation
  2. Measure uses MIN/MAX which can't be pre-aggregated
  3. Pre-agg build failed
  4. Wrong dimensions requested
- **Investigation Needed**:
  - [ ] Check measure SQL definition
  - [ ] Check which pre-aggs include this measure
  - [ ] Check if measure is additive/rollup-safe
  - [ ] Test query without time granularity
- **Fix Applied**: NONE
- **Status**: NEEDS INVESTIGATION

---

### 🕐 TIMEOUT/FAILED Tests (2)

#### RET005 - Return Rate %
- **Status**: FAILED (13.85s - "Continue wait")
- **Error Message**: "Continue wait"
- **Root Cause**: UNKNOWN - needs investigation
- **Possible Causes**:
  1. No monthly pre-agg for this measure
  2. Calculated measure (ratio) can't use pre-agg
  3. Too many dimensions in pre-agg
  4. Pre-agg exists but query doesn't match it
- **Investigation Needed**:
  - [ ] Check measure SQL definition
  - [ ] Check which pre-aggs include this measure
  - [ ] Check if measure is in monthly pre-agg
  - [ ] Compare to working RET004 - what's different?
  - [ ] Test with fewer dimensions
  - [ ] Test with weekly granularity
- **Fix Applied**: NONE
- **Status**: NEEDS INVESTIGATION

#### COGS_DIRECT - GL COGS Direct from COGS Cube
- **Status**: FAILED (11.33s - "Continue wait")
- **Error Message**: "Continue wait"
- **Root Cause**: UNKNOWN - needs investigation
- **Possible Causes**:
  1. No monthly pre-agg in COGS cube
  2. COGS cube has too many dimensions (18 suspected)
  3. COGS cube uses daily granularity only
  4. Pre-agg build incomplete
- **Investigation Needed**:
  - [ ] Check COGS cube pre-agg configuration
  - [ ] Count dimensions in cogs_analysis pre-agg
  - [ ] Check if monthly pre-agg exists
  - [ ] Test with fewer dimensions
  - [ ] Compare query to pre-agg definition
- **Fix Applied**: NONE
- **Status**: NEEDS INVESTIGATION

---

## Next Steps

### Immediate (Before Making Changes)
1. Re-test MM001, GMROI001, MM001_COMP (verify transaction_id fix works)
2. Investigate LIFE004 - understand why pre-agg not built
3. Investigate RET005 - compare to RET004, understand timeout
4. Investigate COGS_DIRECT - analyze pre-agg config

### After Investigation
5. Document root causes for ALL failures
6. Propose fixes with evidence
7. Apply fixes
8. Re-test all failures
9. Document final results

---

## Investigation Log

### Investigation 1: MM001 Error Message
**Date**: 2026-01-18 14:11
**Method**: curl test
**Finding**: `transaction_accounting_lines_cogs.transaction_id cannot be resolved`
**Conclusion**: Missing dimension - FIXED

### Investigation 2: LIFE004 Error Message
**Date**: 2026-01-18 14:12
**Method**: curl test
**Finding**: `No pre-aggregation table has been built for this query yet`
**Conclusion**: Pre-agg issue - NEEDS DEEPER ANALYSIS

### Investigation 3: (To be completed)
...

