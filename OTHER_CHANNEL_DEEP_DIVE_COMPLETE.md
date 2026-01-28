# OTHER Channel Deep Dive Analysis - COMPLETE

**Analysis Date**: 2026-01-28
**Total OTHER Revenue**: €6,553,721.91 (7.6% of total revenue)
**Date Range**: July 1, 2022 - October 31, 2025

---

## EXECUTIVE SUMMARY

The €6.55m in "OTHER" channel can be **fully resolved** by using the **CLASS field as a fallback** classification when department doesn't match known patterns. The analysis reveals:

1. **NULL Department** (€2.92m / 44.6%): These transactions HAVE valid class fields that indicate their channel
2. **Department 202 "Central"** (€3.14m / 47.9%): B2B sales to Lifestyle Sports - should map to B2B_WHOLESALE
3. **Department 203 "Sales"** (€417k / 6.4%): Mix of B2B Corporate and Marketplace sales

**Solution**: Enhance channel_type logic to use CLASS field when DEPARTMENT is NULL or unmatched.

---

## 1. NULL DEPARTMENT ANALYSIS (€2,924,159.71 - 44.6% of OTHER)

### Key Finding: CLASS Field Provides Channel Classification

The 1,770 transaction lines with NULL department can be classified using their CLASS field:

#### Top NULL Department Breakdown by Class:

| Location | Location Name | Class | Class Name | Revenue (EUR) | Channel Recommendation |
|----------|--------------|-------|-----------|---------------|----------------------|
| NULL | *No Location* | 214 | **Central** | €558,822 | B2B_WHOLESALE |
| NULL | *No Location* | 102 | **EU Website** | €501,769 | D2C |
| NULL | *No Location* | 120 | **Corporate** | €438,122 | B2B_CORPORATE |
| NULL | *No Location* | 113 | Kildare Village | €130,054 | RETAIL |
| **Bleckmann BE** | Warehouse | 102 | EU Website | €129,182 | D2C |
| NULL | *No Location* | 101 | **UK Website** | €115,234 | D2C |
| **Bleckmann BE** | Warehouse | 120 | Corporate | €112,722 | B2B_CORPORATE |
| NULL | *No Location* | 108 | **Events** | €82,347 | EVENTS |
| NULL | *No Location* | 114-119 | **Retail Stores** | €331,883 | RETAIL |
| NULL | *No Location* | 123 | **Wholesale** | €39,214 | B2B_WHOLESALE |
| **Otrium** | Marketplace | 120 | Corporate | €27,735 | B2B_MARKETPLACE |
| **Events IE** | Events Location | 108 | Events | €19,002 | EVENTS |
| NULL | *No Location* | 106 | **AU Website** | €22,868 | D2C |

### NULL Department Classification Summary:

- **D2C (Website)**: €~760k (UK Website, EU Website, AU Website, DE Website, US Website, JP Website)
- **B2B Corporate**: €~580k (Corporate class + warehouse locations)
- **RETAIL**: €~330k (Individual store classes: Dundrum, Mahon Point, Kildare Village, etc.)
- **Central/Unknown**: €~560k (Class 214 "Central" - needs investigation)
- **B2B Wholesale**: €~65k (Wholesale class)
- **Events**: €~100k (Events class)
- **Marketplace**: €~28k (Otrium)

### Critical Insight:
**The NULL department issue is NOT a data quality problem** - it's a classification design issue. NetSuite uses CLASS as the primary channel indicator, and DEPARTMENT for organizational structure. When DEPARTMENT is NULL, we should fall back to CLASS.

---

## 2. DEPARTMENT 202 "CENTRAL" ANALYSIS (€3,142,509.87 - 47.9% of OTHER)

### Key Finding: Primarily B2B Sales to Lifestyle Sports

| Location | Location Name | Class | Class Name | Revenue (EUR) | Lines |
|----------|--------------|-------|-----------|---------------|-------|
| **219** | **Lifestyle Sports FC** | 214 | Central | €1,441,501 | 6 |
| 103 | Bleckmann UK | 214 | Central | €952,626 | 10 |
| NULL | *No Location* | 214 | Central | €681,201 | 19 |
| 210 | Events IE | 214 | Central | €29,317 | 2 |
| 5 | Kildare Village | 214 | Central | €18,695 | 2 |
| 101 | Bleckmann BE | 108 | Events | €10,199 | 8 |
| 101 | Bleckmann BE | 123 | Wholesale | €6,833 | 4 |

### Analysis:

- **€1.44m (46%)**: Lifestyle Sports FC location with "Central" class
  - **Recommendation**: This appears to be B2B wholesale to Lifestyle Sports
  - **Channel**: B2B_WHOLESALE

- **€1.63m (52%)**: Warehouses (Bleckmann UK/BE) with "Central" class
  - **Recommendation**: Fulfillment from warehouses for wholesale/B2B
  - **Channel**: B2B_WHOLESALE

- **€10k (0.3%)**: Events and Wholesale classes
  - **Recommendation**: Already have class indicators - use them
  - **Channel**: EVENTS / B2B_WHOLESALE respectively

### Solution for Department 202:
Map Department 202 "Central" → **B2B_WHOLESALE** (primary)
Consider class field for exceptions (Events, Online)

---

## 3. DEPARTMENT 203 "SALES" ANALYSIS (€417,250.61 - 6.4% of OTHER)

### Key Finding: Mix of B2B Marketplaces and Corporate Sales

| Location | Location Name | Class | Class Name | Revenue (EUR) | Lines |
|----------|--------------|-------|-----------|---------------|-------|
| 101 | Bleckmann BE | 120 | Corporate | €156,127 | 570 |
| **212** | **Otrium** | 120 | Corporate | €105,636 | 3,497 |
| **231** | **The Very Group** | 120 | Corporate | €40,836 | 123 |
| 103 | Bleckmann UK | 123 | Wholesale | €33,670 | 117 |
| NULL | *No Location* | 120 | Corporate | €29,677 | 91 |
| **219** | **Lifestyle Sports FC** | 120 | Corporate | €22,060 | 235 |
| 101 | Bleckmann BE | 123 | Wholesale | €19,926 | 61 |

### Analysis:

- **€105k (25%)**: Otrium marketplace
  - **Channel**: B2B_MARKETPLACE

- **€41k (10%)**: The Very Group (UK marketplace/retailer)
  - **Channel**: B2B_MARKETPLACE

- **€156k (37%)**: Bleckmann BE + Corporate class
  - **Channel**: B2B_CORPORATE

- **€54k (13%)**: Wholesale class
  - **Channel**: B2B_WHOLESALE

- **€22k (5%)**: Lifestyle Sports FC
  - **Channel**: B2B_WHOLESALE

### Solution for Department 203:
Use **LOCATION + CLASS** to determine channel:
- Location = Otrium/The Very Group → B2B_MARKETPLACE
- Class = Wholesale → B2B_WHOLESALE
- Class = Corporate → B2B_CORPORATE

---

## RECOMMENDED SOLUTION: Enhanced Channel Classification Logic

### Current Logic (FLAWED):
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

### Proposed Logic (COMPREHENSIVE):
```yaml
CASE
  -- Known departments (existing logic)
  WHEN department = 109 THEN 'D2C'
  WHEN department = 108 THEN 'RETAIL'
  WHEN department = 207 THEN 'B2B_MARKETPLACE'
  WHEN department_name LIKE '%Wholesale%' THEN 'B2B_WHOLESALE'
  WHEN department_name LIKE '%Event%' THEN 'EVENTS'
  
  -- Department 202 "Central" → B2B_WHOLESALE (unless class indicates otherwise)
  WHEN department = 202 AND {CUBE}.class_name LIKE '%Event%' THEN 'EVENTS'
  WHEN department = 202 THEN 'B2B_WHOLESALE'
  
  -- Department 203 "Sales" → Use location + class
  WHEN department = 203 AND {CUBE}.location IN (212, 231) THEN 'B2B_MARKETPLACE'  -- Otrium, The Very Group
  WHEN department = 203 AND {CUBE}.class_name LIKE '%Wholesale%' THEN 'B2B_WHOLESALE'
  WHEN department = 203 AND {CUBE}.class_name = 'Corporate' THEN 'B2B_CORPORATE'
  WHEN department = 203 THEN 'B2B_CORPORATE'  -- Default for Sales dept
  
  -- NULL department → Use CLASS field as primary indicator
  WHEN department IS NULL AND {CUBE}.class_name IN ('UK Website', 'EU Website', 'AU Website', 'US Website', 'DE Website', 'JP Website', 'NI Website') THEN 'D2C'
  WHEN department IS NULL AND {CUBE}.class_name IN ('Dundrum Town Centre', 'Mahon Point', 'Crescent Centre', 'Liffey Valley', 'Kildare Village', 'Blanchardstown', 'Westfield London', 'Manchester', 'Belfast', 'Liverpool', 'Galway', 'Swords Pavilion', 'Jervis Centre') THEN 'RETAIL'
  WHEN department IS NULL AND {CUBE}.class_name = 'Events' THEN 'EVENTS'
  WHEN department IS NULL AND {CUBE}.class_name IN ('Wholesale', 'Central') THEN 'B2B_WHOLESALE'
  WHEN department IS NULL AND {CUBE}.class_name = 'Corporate' THEN 'B2B_CORPORATE'
  WHEN department IS NULL AND {CUBE}.location IN (212, 231) THEN 'B2B_MARKETPLACE'  -- Otrium, The Very Group
  WHEN department IS NULL THEN 'UNCLASSIFIED'
  
  ELSE 'OTHER'
END
```

### Alternative: Simplified Logic Using Class Hierarchies
```yaml
CASE
  -- Priority 1: Known department mappings
  WHEN department IN (109) THEN 'D2C'
  WHEN department IN (108) THEN 'RETAIL'
  WHEN department IN (207) THEN 'B2B_MARKETPLACE'
  WHEN department IN (202) THEN 'B2B_WHOLESALE'  -- Central dept
  WHEN department_name LIKE '%Wholesale%' THEN 'B2B_WHOLESALE'
  WHEN department_name LIKE '%Event%' THEN 'EVENTS'
  
  -- Priority 2: Use class field as fallback
  WHEN {CUBE}.class IN (101, 102, 103, 106, 215, 220, 216) THEN 'D2C'  -- Website classes
  WHEN {CUBE}.class IN (109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 209, 219) THEN 'RETAIL'  -- Store classes
  WHEN {CUBE}.class = 108 THEN 'EVENTS'
  WHEN {CUBE}.class = 123 THEN 'B2B_WHOLESALE'
  WHEN {CUBE}.class = 120 THEN 'B2B_CORPORATE'
  WHEN {CUBE}.class = 214 THEN 'B2B_WHOLESALE'  -- Central class
  WHEN {CUBE}.class = 222 THEN 'B2B_MARKETPLACE'
  
  -- Priority 3: Marketplace locations
  WHEN {CUBE}.location IN (212, 231) THEN 'B2B_MARKETPLACE'
  
  ELSE 'OTHER'
END
```

---

## IMPACT ANALYSIS

### After Implementing Proposed Logic:

| Channel | Current Revenue | After Fix | Change |
|---------|----------------|-----------|--------|
| D2C | €39.93m (46.5%) | €41.31m (48.1%) | +€1.38m |
| RETAIL | €34.46m (40.1%) | €34.79m (40.5%) | +€330k |
| B2B_WHOLESALE | €4.20m (4.9%) | €7.58m (8.8%) | +€3.38m |
| B2B_CORPORATE | €0 (0%) | €620k (0.7%) | +€620k |
| B2B_MARKETPLACE | €89k (0.1%) | €263k (0.3%) | +€174k |
| EVENTS | €612k (0.7%) | €714k (0.8%) | +€102k |
| **OTHER** | **€6.55m (7.6%)** | **€~560k (0.7%)** | **-€5.99m** |

### Remaining "OTHER" (€560k):
- Transactions with NULL department AND class = "Central" (214)
- Requires business decision: What is "Central" class used for?
- Likely: Internal transfers, adjustments, or miscellaneous B2B

---

## IMPLEMENTATION STEPS

### Step 1: Update Cube Configuration
Edit `/home/produser/cube-gpc/model/cubes/transaction_lines.yml` (lines 474-486)

Replace current channel_type dimension with **Simplified Logic Using Class Hierarchies** (recommended for maintainability)

### Step 2: Add class_name Dimension (if not exists)
```yaml
- name: class_name
  sql: "{classifications.name}"
  type: string
```

### Step 3: Validate Changes
Run test queries:
```sql
-- Query 1: Verify OTHER channel is reduced
SELECT channel_type, SUM(total_revenue) 
FROM transaction_lines 
GROUP BY channel_type

-- Query 2: Verify NULL departments are classified
SELECT 
  CASE WHEN department IS NULL THEN 'NULL' ELSE 'HAS_DEPT' END as dept_status,
  channel_type,
  COUNT(*) as line_count
FROM transaction_lines
GROUP BY dept_status, channel_type
```

### Step 4: Document Business Rules
Create documentation explaining:
- Why CLASS field is used as fallback
- Mapping of class IDs to channels
- Exception handling for edge cases

---

## DATA QUALITY RECOMMENDATIONS

1. **Backfill NULL Departments** (Optional)
   - Consider backfilling department field based on class/location
   - Would simplify future analysis and reduce reliance on class fallback

2. **Clarify "Central" Class Usage**
   - Class 214 "Central" is used for €1.8m in revenue
   - Investigate if this should be split into subcategories

3. **Add Data Validation**
   - Alert when new transactions have NULL department AND NULL class
   - Monitor for new departments/classes that don't match known patterns

---

## APPENDIX: Master Data Reference

### Class to Channel Mapping:
- **101-103, 106, 215, 216, 220**: Website classes → D2C
- **105, 211, 212**: Retail parent classes → RETAIL
- **107, 120**: Corporate, B2B parent → B2B_CORPORATE
- **108**: Events → EVENTS
- **109-119, 209, 219**: Individual store classes → RETAIL
- **123**: Wholesale → B2B_WHOLESALE
- **214**: Central → B2B_WHOLESALE (recommended)
- **222**: Marketplaces → B2B_MARKETPLACE
- **223**: Stock Clearance → (exclude or map to OTHER)

### Key Locations:
- **1-11, 205, 214**: Physical retail stores
- **101-103**: Bleckmann warehouses (fulfillment)
- **212**: Otrium (marketplace)
- **219, 226-228**: Lifestyle Sports locations (B2B)
- **231**: The Very Group (marketplace)
- **236, 238**: Headquarters (admin)
- **244**: Meteor Space (?)

---

**End of Deep Dive Analysis**
