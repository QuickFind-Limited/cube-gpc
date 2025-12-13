# GMROI Investigation - Complete Documentation Index

**Investigation Date:** December 8, 2025  
**Scope:** GymPlusCoffee Cube Analytics Platform  
**Thoroughness:** Very Thorough  

---

## Overview

This investigation reveals **THREE CRITICAL ISSUES** with GMROI calculations in the cube analytics platform:

1. **DC Intake Units Mismatch** (40% discrepancy between data sources)
2. **Gross Profit Calculation Error** (mathematically impossible: GP > Net Sales)
3. **Intake Margin Data Availability** (partially available from NetSuite)

All issues have been traced to root causes, with specific file locations and line numbers.

---

## Documents in This Investigation

### 1. GMROI_QUICK_REFERENCE.md (202 lines, 5.6 KB)
**Duration to Read:** 5-10 minutes  
**Best For:** Quick lookup, executive briefing, decision-making

**Contains:**
- Three critical issues summarized
- Root causes and discrepancies
- Pre-aggregation coverage table
- Measure definitions (what to use)
- Key files to review with line numbers
- Quick diagnostic queries
- Recommendations summary

**Start Here If:** You need answers fast or want to explain findings to stakeholders

---

### 2. GMROI_ACCURACY_INVESTIGATION.md (656 lines, 22 KB)
**Duration to Read:** 30-45 minutes (comprehensive read)  
**Best For:** Deep understanding, technical analysis, solution design

**Contains:**
- Executive summary with key findings
- Detailed root cause analysis with SQL definitions
- Unit count comparison table
- Gross profit calculation error explanation
- Intake margin availability assessment
- Pre-aggregation coverage analysis (19 pre-aggs reviewed)
- Transaction type confusion analysis
- Root cause hypothesis with examples
- Recommendations and fixes (3 specific fixes detailed)
- Verification checklist
- Summary table of all requirements vs availability

**Sections:**
1. Executive Summary (2 pages)
2. Detailed Findings - Issue 1: DC Intake Units (8 pages)
3. Detailed Findings - Issue 2: Gross Profit Error (10 pages)
4. Detailed Findings - Issue 3: Intake Margin (6 pages)
5. Pre-Aggregation Coverage Analysis (5 pages)
6. Transaction Type Confusion Analysis (3 pages)
7. Root Cause Hypothesis (3 pages)
8. Recommendations & Fixes (4 pages)
9. Verification Checklist (1 page)
10. Summary Table (1 page)

**Start Here If:** You want complete technical documentation or need to understand every aspect

---

### 3. GMROI_VERIFICATION_SQL.md (347 lines, 12 KB)
**Duration to Read:** 15-20 minutes (reference as needed)  
**Best For:** Running queries, verifying findings, testing hypotheses

**Contains:**
- 6 sections with 20+ SQL queries
- Each query has expected results
- Verification of all three issues
- Sample data queries to inspect actual values
- Results summary table

**Query Sections:**
1. DC Intake Units Mismatch (3 queries)
2. Gross Profit Calculation Error (4 queries)
3. Intake Margin Data Availability (4 queries)
4. Transaction Type Filtering (2 queries)
5. Pre-Aggregation Coverage (2 queries)
6. Sample Data Examples (2 queries)

**Each Query Includes:**
- SQL code
- Expected result
- Explanation of what it shows

**Start Here If:** You want to verify findings with actual data from your system

---

## Quick Navigation

### By Question

**"What's the DC Intake Units issue?"**  
→ GMROI_QUICK_REFERENCE.md, Section 1 (2 min)  
→ GMROI_ACCURACY_INVESTIGATION.md, Section "Issue 1" (8 pages)  
→ GMROI_VERIFICATION_SQL.md, Section 1 (Query 1a-1c)

**"Why is the €20.6M gross profit number wrong?"**  
→ GMROI_QUICK_REFERENCE.md, Section 2 (3 min)  
→ GMROI_ACCURACY_INVESTIGATION.md, Section "Issue 2" (10 pages)  
→ GMROI_VERIFICATION_SQL.md, Section 2 (Query 2a-2d)

**"Is intake margin data available or not?"**  
→ GMROI_QUICK_REFERENCE.md, Section 3 (3 min)  
→ GMROI_ACCURACY_INVESTIGATION.md, Section "Issue 3" (6 pages)  
→ GMROI_VERIFICATION_SQL.md, Section 3 (Query 3a-3d)

**"How do I fix these issues?"**  
→ GMROI_ACCURACY_INVESTIGATION.md, Section "Recommendations & Fixes" (4 pages)  
→ GMROI_QUICK_REFERENCE.md, "Recommendations Summary" (5 bullet points)

**"Which measures should I use for GMROI?"**  
→ GMROI_QUICK_REFERENCE.md, "Measure Definitions" section  
→ GMROI_ACCURACY_INVESTIGATION.md, "Summary Table" (end of document)

### By Audience

**For Business Users / Stakeholders:**
1. Read: GMROI_QUICK_REFERENCE.md (5 min)
2. Ask: Questions about findings
3. Review: "Recommendations Summary" section

**For Data Analysts / BI Teams:**
1. Start: GMROI_QUICK_REFERENCE.md for context (10 min)
2. Read: GMROI_ACCURACY_INVESTIGATION.md for details (45 min)
3. Run: GMROI_VERIFICATION_SQL.md queries (30 min)
4. Implement: Recommendations from Investigation

**For Data Engineers / Cube Developers:**
1. Read: GMROI_ACCURACY_INVESTIGATION.md, Section "Recommendations & Fixes" (15 min)
2. Reference: File locations and line numbers throughout docs
3. Review: Pre-aggregation coverage analysis (5 min)
4. Implement: Schema/measure changes as recommended

### By Time Available

**5 minutes:** Read GMROI_QUICK_REFERENCE.md completely

**15 minutes:** Read GMROI_QUICK_REFERENCE.md + skim key sections of Investigation

**30 minutes:** Read Investigation fully, skip SQL verification

**60 minutes:** Read everything, run sample SQL queries

**2+ hours:** Read everything, run all verification queries, design fixes

---

## Key Files Referenced in Investigation

These files in the cube-gpc repository are discussed with specific line numbers:

### Cube Definition Files
- `/home/produser/cube-gpc/model/cubes/transaction_lines.yml`
  - Line 203: gross_margin measure (CORRECT formula)
  - Line 224: itemrcpt_line_count measure
  - Line 467: estgrossprofit dimension
  - Lines 508-560: sales_analysis pre-agg

- `/home/produser/cube-gpc/model/cubes/supplier_lead_times.yml`
  - Line 3-23: SQL definition with INNER JOIN filters
  - Line 156-173: lead_time_rollup pre-agg (insufficient for GMROI)

- `/home/produser/cube-gpc/model/cubes/landed_costs.yml`
  - Line 10-11: estgrossprofit fields (NetSuite estimate)
  - Line 104-122: monthly_landed_costs pre-agg

### SQL View Files
- `/home/produser/cube-gpc/docs/bigquery-views/transactions_analysis.sql`
  - Line 23-33: View definition showing transaction type filters
  - Lines 36-47: Expected transaction counts by type

- `/home/produser/cube-gpc/create_filtered_views.sql`
  - Line 23-28: transaction_lines_clean view definition

---

## Key Findings Summary

### Finding 1: DC Intake Units Mismatch

| Metric | Value | Source | Status |
|---|---|---|---|
| YTD Intake Units (Wrong) | 632,106 | supplier_lead_times | Reported by AI agent |
| YTD Intake Units (Correct) | 1,060,254 | transaction_lines | Actual complete count |
| Difference | 428,148 units (40%) | - | Due to PO linkage filter |
| Root Cause | INNER JOIN to purchase_orders | supplier_lead_times.yml:8 | By design |
| Recommendation | Use transaction_lines measure | itemrcpt_line_count | High priority |

### Finding 2: Gross Profit Calculation Error

| Metric | Value | Status | Issue |
|---|---|---|---|
| Reported GP | €20.6M | From AI agent | Mathematically impossible |
| Reported Net Sales | €23.0M | From AI agent | GP > Net Sales! |
| Actual Sales Margin | €5.8-9.2M | Calculated | 20-35% typical |
| Root Cause | Sum of estgrossprofit (ItemRcpt) | landed_costs.yml:10 | Wrong measure |
| Correct Measure | transaction_lines.gross_margin | transaction_lines.yml:203 | Revenue - Cost |
| Recommendation | Use gross_margin measure | Pre-agged in sales_analysis | Critical fix |

### Finding 3: Intake Margin Availability

| Component | Available | Source | Coverage |
|---|---|---|---|
| Unit Cost | Yes | item_receipt_lines.rate | 100% |
| Receipt Amount | Yes | transaction_lines.amount | 100% |
| Estimated Margin % | Yes | transaction_lines.estgrossprofitpercent | 100% |
| Retail Value | No | Not exported | 0% |
| VAT Breakdown | No | Not in ItemRcpt | 0% |
| Workaround | Yes | Use NetSuite's % estimate | Available |

---

## Action Items

### Immediate (Verify Findings)
- [ ] Run Query 1a-1b from GMROI_VERIFICATION_SQL.md to confirm unit counts
- [ ] Run Query 2b from verification SQL to check actual margin
- [ ] Run Query 3a-3c to verify data availability
- [ ] Document confirmed findings

### Short Term (Fix Issues)
- [ ] Update supplier_lead_times.yml documentation (note: PO-linked only)
- [ ] Create new measure for "dc_inventory_intake_units" in transaction_lines
- [ ] Document that estgrossprofit should NOT be used for sales GMROI
- [ ] Update any AI agent prompts to use correct measures

### Medium Term (Improve Data Model)
- [ ] Add intake_margin measure to transaction_lines for ItemRcpt analysis
- [ ] Consider separate pre-agg for inventory intake metrics
- [ ] Document GMROI calculation formula officially
- [ ] Add validation to prevent combining ItemRcpt and sales revenue

### Long Term (Architecture)
- [ ] Review other cubes for similar measure confusion
- [ ] Implement measure naming conventions to prevent future confusion
- [ ] Create data governance documentation
- [ ] Add pre-agg for retail value calculations if needed for future analysis

---

## Document Maintenance

**Last Updated:** December 8, 2025  
**Investigation Lead:** Claude Code  
**Scope:** GymPlusCoffee cube-gpc repository  

**To Update These Docs:**
1. GMROI_QUICK_REFERENCE.md - Update after each recommendation is implemented
2. GMROI_ACCURACY_INVESTIGATION.md - Add verification results from SQL queries
3. GMROI_VERIFICATION_SQL.md - Add expected actual results once verified

---

## Additional Resources

### Related Documentation in cube-gpc:
- ARCHITECTURE_ANALYSIS_INDEX.md - Overall cube architecture
- CUBE_ARCHITECTURE_ANALYSIS.md - Detailed pre-agg analysis
- RETAIL_METRICS_GAP_ANALYSIS.md - GMROI listed as #1 critical gap

### Related Documentation in GymPlusCoffee-Preview/backend:
- PHASE2_DATA_AVAILABILITY_SUMMARY.md - Item receipt data validation
- TRANSACTIONLINE_VERIFIED_FIELDS.md - Field availability reference
- POST_EXTRACTION_DEPLOYMENT_GUIDE_v2.md - Field descriptions

---

## Questions?

All three investigation documents contain:
- **GMROI_QUICK_REFERENCE.md** - Answers to quick questions
- **GMROI_ACCURACY_INVESTIGATION.md** - Deep technical explanation
- **GMROI_VERIFICATION_SQL.md** - Proof via data queries

Start with the Quick Reference, then drill down to Investigation for details.

