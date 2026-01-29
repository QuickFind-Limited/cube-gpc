# Comprehensive Revert Options for cube-gpc

## Full Change History (Past 30 Days)

### **Timeline Overview**

```
Jan 18 (TODAY)  → 5 commits (performance optimization sprint)
Jan 17          → 1 commit (3-pre-agg design)
Jan 16          → 2 commits (denormalized MV, rollup-only mode)
Jan 15          → 3 commits (granularity changes, refresh_key)
Before Jan 15   → Stable period (8c93ce4 - consolidated pre-aggs)
```

---

## **Jan 18, 2026 (TODAY) - 5 Commits**

### Current HEAD (8b5069e)
**What**: Added operations_monthly_fast + cogs_monthly_fast
**Files**: transaction_lines.yml, transaction_accounting_lines_cogs.yml
**Pre-aggs**: 6 total (revenue_analysis, weekly, monthly, fast monthly, operations fast, customer_geography)

### Before 8b5069e (27bd74f)
**What**: Fixed missing transaction_id in COGS cube
**Files**: transaction_accounting_lines_cogs.yml
**Note**: Bug fix for JOIN

### Before 27bd74f (ff45d6f)
**What**: Added revenue_monthly_fast
**Files**: transaction_lines.yml
**Pre-aggs**: 5 total

### Before ff45d6f (2c197f0)
**What**: Added weekly/monthly to transactions + fulfillments
**Files**: transactions.yml, fulfillments.yml

### Before 2c197f0 (9624643) ⭐ **OPTION 1**
**What**: Added weekly/monthly to transaction_lines
**Files**: transaction_lines.yml
**Pre-aggs**: 4 total (revenue_analysis, weekly, monthly, customer_geography)
**Revert command**:
```bash
git checkout 9624643 -- model/cubes/transaction_lines.yml \
  model/cubes/transaction_accounting_lines_cogs.yml \
  model/cubes/transactions.yml \
  model/cubes/fulfillments.yml
```

---

## **Jan 17, 2026 - 1 Commit**

### f587f96 ⭐ **OPTION 2 - "3-pre-agg design"**
**What**: Adopted cube-demo 3-pre-agg design (fixed 919x file size explosion)
**Files**: transaction_lines.yml
**Pre-aggs**: 3 total (revenue_analysis, sku_analysis, customer_geography)
**Description**: "Cleaner" design with fewer pre-aggs
**Revert command**:
```bash
git checkout f587f96 -- model/cubes/transaction_lines.yml \
  model/cubes/transaction_accounting_lines_cogs.yml \
  model/cubes/transactions.yml \
  model/cubes/fulfillments.yml
```

---

## **Jan 16, 2026 - 2 Commits**

### c3f275a ⭐ **OPTION 3 - "Denormalized MV"**
**What**: CRITICAL FIX - Use denormalized materialized view for 90% faster builds
**SQL Source**: `gpc.transaction_lines_denormalized_mv`
**Files**: transaction_lines.yml
**Performance**: 90% faster pre-agg builds
**Revert command**:
```bash
git checkout c3f275a -- model/cubes/transaction_lines.yml \
  model/cubes/transaction_accounting_lines_cogs.yml \
  model/cubes/transactions.yml \
  model/cubes/fulfillments.yml
```

### 0ba6b4d
**What**: Optimize pre-aggregations - 6 pre-aggs for rollup-only mode (99% coverage)
**Files**: transaction_lines.yml

---

## **Jan 15, 2026 - 3 Commits**

### ab6c240
**What**: Change from weekly to daily granularity
**Files**: transaction_lines.yml

### a5bf309
**What**: Change from month to week granularity
**Files**: transaction_lines.yml

### 20fba6b
**What**: Update refresh_key from 365 days to 1 day
**Files**: ALL cubes (26 files)

---

## **Before Jan 15, 2026 (STABLE PERIOD)**

### 8c93ce4 ⭐ **OPTION 4 - "Consolidated pre-aggs"**
**What**: Consolidate 14 pre-aggregations into single sales_analysis with 20 dimensions
**Date**: Before Jan 15
**Description**: Single large pre-agg approach
**Revert command**:
```bash
git checkout 8c93ce4 -- model/cubes/transaction_lines.yml \
  model/cubes/transaction_accounting_lines_cogs.yml \
  model/cubes/transactions.yml \
  model/cubes/fulfillments.yml
```

### c677e6a
**What**: Add monthly partitioning back (cube-gpc only)

### 795a7a6
**What**: Remove monthly partitioning from all pre-aggs

### 28f6ba4 ⭐ **OPTION 5 - "Fixed build_range_end"**
**What**: Use 2025-10-31 instead of CURRENT_DATE()
**Description**: Stable configuration before major changes
**Revert command**:
```bash
git checkout 28f6ba4 -- model/cubes/transaction_lines.yml \
  model/cubes/transaction_accounting_lines_cogs.yml \
  model/cubes/transactions.yml \
  model/cubes/fulfillments.yml
```

---

## **RECOMMENDED REVERT OPTIONS**

### ⭐ **SAFEST: Option 2 (f587f96) - "3-pre-agg design"**
**Date**: Jan 17, 2026
**Why**:
- Clean, simple design
- Fixed major file size issue
- Only 1 day old
- Well-documented approach
**Trade-off**: No weekly/monthly pre-aggs (queries may be slower)

### ⭐ **MIDDLE GROUND: Option 3 (c3f275a) - "Denormalized MV"**
**Date**: Jan 16, 2026
**Why**:
- 90% faster pre-agg builds (major performance win)
- Uses optimized materialized view
- Before the granularity experimentation
**Trade-off**: Still has multiple pre-agg approach

### ⭐ **MOST STABLE: Option 5 (28f6ba4) - "Before major changes"**
**Date**: Before Jan 15
**Why**:
- Before all the recent experimentation
- Fixed build_range_end configuration
- Known stable state
**Trade-off**: Older configuration, may miss some fixes

---

## **What Changed in Each File**

### transaction_lines.yml
- **TODAY**: Added operations_monthly_fast, revenue_monthly_fast
- **Jan 18**: Added revenue_analysis_weekly, revenue_analysis_monthly
- **Jan 17**: Adopted 3-pre-agg design
- **Jan 16**: Switched to denormalized MV

### transaction_accounting_lines_cogs.yml
- **TODAY**: Added transaction_id dimension + cogs_monthly_fast
- **Before**: Mostly unchanged

### transactions.yml
- **TODAY**: Added orders_weekly, orders_monthly
- **Before**: Basic configuration

### fulfillments.yml
- **TODAY**: Added fulfillment_weekly, fulfillment_monthly
- **Before**: Basic configuration

---

## **How to Revert**

### To revert EVERYTHING to a specific commit:
```bash
cd /home/produser/cube-gpc
git checkout <COMMIT_HASH> -- model/cubes/*.yml
git commit -m "Revert all cubes to <COMMIT_HASH>"
git push origin master
```

### To revert ONLY transaction_lines.yml:
```bash
cd /home/produser/cube-gpc
git checkout <COMMIT_HASH> -- model/cubes/transaction_lines.yml
git commit -m "Revert transaction_lines to <COMMIT_HASH>"
git push origin master
```

---

## **Quick Decision Guide**

**Want simplicity?** → Option 2 (f587f96) - 3-pre-agg design

**Want performance?** → Option 3 (c3f275a) - Denormalized MV

**Want stability?** → Option 5 (28f6ba4) - Before major changes

**Just undo today?** → Option 1 (9624643) - Before today's work

---

**Which option would you like to revert to?**
