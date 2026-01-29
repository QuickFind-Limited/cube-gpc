# transaction_lines.yml Revert Options

## Recent Changes Timeline (Past 7 Days)

### **CURRENT** (HEAD - commit 8b5069e + ff45d6f)
**Date**: January 18, 2026 (TODAY)
**Changes**:
- Added `revenue_monthly_fast` pre-agg (6 dimensions)
- Added `operations_monthly_fast` pre-agg (4 dimensions)
**Total Pre-aggs**: 6
- revenue_analysis (daily)
- revenue_analysis_weekly
- revenue_analysis_monthly
- revenue_monthly_fast (NEW)
- operations_monthly_fast (NEW)
- customer_geography

**Purpose**: Fix RET005 and total_revenue timeouts for 12-month queries

---

### **Option 1: Revert to 9624643** (BEFORE TODAY)
**Date**: January 18, 2026 (earlier today)
**Commit**: `9624643` - "Add weekly and monthly pre-aggregations to fix timeout issues"
**Total Pre-aggs**: 4
- revenue_analysis (daily)
- revenue_analysis_weekly
- revenue_analysis_monthly
- customer_geography

**This removes**:
- revenue_monthly_fast (added by ff45d6f)
- operations_monthly_fast (added by 8b5069e)

**Use this if**: You want weekly/monthly but not the "fast" variants

---

### **Option 2: Revert to f587f96** (Before weekly/monthly)
**Date**: ~3-4 days ago
**Commit**: `f587f96` - "Adopt cube-demo 3-pre-agg design to fix 919x file size explosion"
**Total Pre-aggs**: 3
- revenue_analysis (daily)
- sku_analysis (daily)
- customer_geography (daily)

**This removes**:
- revenue_analysis_weekly
- revenue_analysis_monthly
- revenue_monthly_fast
- operations_monthly_fast

**Use this if**: You want the 3-pre-agg design without any weekly/monthly

---

### **Option 3: Revert to c3f275a** (Denormalized MV)
**Date**: ~5-6 days ago
**Commit**: `c3f275a` - "CRITICAL FIX: Use denormalized materialized view for 90% faster pre-agg builds"
**Changes**: Uses `transaction_lines_denormalized_mv` as SQL source
**Total Pre-aggs**: Multiple (need to check)

**Use this if**: You want the denormalized materialized view approach

---

## How to Revert

### To revert to Option 1 (9624643 - before today):
```bash
cd /home/produser/cube-gpc
git checkout 9624643 -- model/cubes/transaction_lines.yml
git commit -m "Revert transaction_lines to before operations_monthly_fast changes"
git push origin master
```

### To revert to Option 2 (f587f96 - 3-pre-agg design):
```bash
cd /home/produser/cube-gpc
git checkout f587f96 -- model/cubes/transaction_lines.yml
git commit -m "Revert transaction_lines to 3-pre-agg design"
git push origin master
```

### To revert to Option 3 (c3f275a - denormalized MV):
```bash
cd /home/produser/cube-gpc
git checkout c3f275a -- model/cubes/transaction_lines.yml
git commit -m "Revert transaction_lines to denormalized MV version"
git push origin master
```

---

## Question for User

**Which version would you like to revert to?**

1. **Option 1 (9624643)** - Has weekly/monthly, removes today's "fast" pre-aggs
2. **Option 2 (f587f96)** - 3-pre-agg design, no weekly/monthly
3. **Option 3 (c3f275a)** - Denormalized MV version
4. **Other** - Specify commit hash

Please specify which option you'd like.
