# OTHER Channel Analysis - Root Cause Identified

## Executive Summary

**Total OTHER Revenue**: €6,553,721.91 (7.6% of total revenue)
**Date Range**: July 1, 2022 - October 31, 2025

## Root Cause: 9 Departments Missing from Channel Classification

The following departments are falling into the "OTHER" category because they don't match any of the current CASE conditions:

| Department ID | Department Name      | Line Count | Revenue (EUR) | % of OTHER |
|--------------|---------------------|-----------|---------------|-----------|
| 202          | Central             | 146       | €3,142,509.87 | 47.9%     |
| NULL         | *No Department*     | 1,770     | €2,924,159.71 | 44.6%     |
| 203          | Sales               | 5,006     | €417,250.61   | 6.4%      |
| 103          | Supply Chain        | 329       | €30,420.51    | 0.5%      |
| 1            | Marketing           | 1,167     | €25,286.50    | 0.4%      |
| 105          | Product             | 168       | €1,519.05     | 0.0%      |
| 3            | Digital Marketing   | 35        | €0.00         | 0.0%      |
| 102          | HR                  | 10        | €0.00         | 0.0%      |
| 107          | Buying              | 4        | €0.00         | 0.0%      |

## Key Findings

### 1. Department 202 "Central" - €3.14m (47.9% of OTHER)
- **Likely Channel**: This appears to be a central/admin department
- **Action Required**: Determine if these are legitimate sales and which channel they belong to
- Possible categories: D2C, RETAIL, or a new administrative category

### 2. NULL Department - €2.92m (44.6% of OTHER) ⚠️ CRITICAL
- **Issue**: 1,770 transaction lines with NO department assigned
- **Action Required**: URGENT - These transactions are missing critical classification data
- **Recommendation**: 
  - Investigate why department is NULL
  - Add data quality check to prevent NULL departments
  - Determine correct department/channel for these transactions

### 3. Department 203 "Sales" - €417k (6.4% of OTHER)
- **Likely Channel**: Could be general sales - need to determine if D2C, RETAIL, or B2B
- **Action Required**: Clarify business rules for "Sales" department

### 4. Remaining Departments (€57k combined, 0.9% of OTHER)
- Marketing (1), Digital Marketing (3), HR (102), Product (105), Buying (107), Supply Chain (103)
- These are operational departments with minimal revenue
- Likely legitimate but need channel classification

## Current Channel Classification Logic

```yaml
CASE
  WHEN department = 109 THEN 'D2C'
  WHEN department = 108 THEN 'RETAIL'
  WHEN department = 207 THEN 'B2B_MARKETPLACE'
  WHEN department_name LIKE '%Wholesale%' THEN 'B2B_WHOLESALE'
  WHEN department_name LIKE '%Event%' THEN 'EVENTS'
  ELSE 'OTHER'
END
```

## Recommended Actions

### Immediate (Critical)
1. **Investigate NULL departments** (€2.92m)
   - Why are 1,770 lines missing department data?
   - Can we backfill department from other transaction fields?
   - Add data validation to prevent NULL departments going forward

2. **Classify Department 202 "Central"** (€3.14m)
   - Review sample transactions to understand nature
   - Determine correct channel assignment
   - Update CASE logic

### Short-term
3. **Classify Department 203 "Sales"** (€417k)
   - Understand business rules for "Sales" department
   - Map to appropriate channel

4. **Handle Operational Departments** (€57k)
   - Decide if these should be excluded or classified
   - Create business rule for non-revenue departments

### Proposed Updated Logic

```yaml
CASE
  WHEN department = 109 THEN 'D2C'
  WHEN department = 108 THEN 'RETAIL'
  WHEN department = 207 THEN 'B2B_MARKETPLACE'
  WHEN department = 202 THEN '[TBD - Central]'  -- NEEDS BUSINESS DECISION
  WHEN department = 203 THEN '[TBD - Sales]'    -- NEEDS BUSINESS DECISION
  WHEN department_name LIKE '%Wholesale%' THEN 'B2B_WHOLESALE'
  WHEN department_name LIKE '%Event%' THEN 'EVENTS'
  WHEN department IS NULL THEN 'UNCLASSIFIED'   -- Make NULL explicit
  ELSE 'OTHER'
END
```

## Next Steps

1. **Business Decision Required**: Determine correct channel for:
   - Department 202 "Central"
   - Department 203 "Sales"
   - NULL department transactions

2. **Data Quality**: Investigate and fix NULL department issue

3. **Update Cube Configuration**: Modify channel_type dimension in:
   `/home/produser/cube-gpc/model/cubes/transaction_lines.yml` (lines 474-486)

4. **Validation**: After updates, verify OTHER channel revenue approaches 0%

---

**Analysis Date**: 2026-01-28
**Data Source**: Parquet files (transaction_lines, transactions, departments)
**Query**: All shards (000000000000 through 000000000016)
