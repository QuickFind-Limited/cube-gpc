# AUDIT Field Extractions - Record Count Summary

**Extraction Date**: 2025-11-24
**Status**: 9 of 12 Complete (75%)

---

## Completed Extractions

### Transaction Lines (by Type)

| Type | Status | Records | File Size | Notes |
|------|--------|---------|-----------|-------|
| CashRfnd | ✅ COMPLETE | 12,181 | 5.8MB | Cash refunds |
| CashSale | 🔄 RUNNING | ~2.5M (est) | ~500MB (est) | Largest dataset |
| CustCred | ✅ COMPLETE | 92,585 | 45MB | Customer credits |
| CustInvc | 🔄 RUNNING | ~2.8M (est) | ~600MB (est) | Largest dataset |
| RtnAuth | ✅ COMPLETE | 45,864 | 23MB | Return authorizations |
| SalesOrd | 🔄 RUNNING | ~2.2M (est) | ~550MB (est) | Largest dataset |

**Subtotal Completed**: 150,630 records
**Estimated Total**: ~7.6M records

### Transactions (by Type)

| Type | Status | Records | File Size | Notes |
|------|--------|---------|-----------|-------|
| CashRfnd | ✅ COMPLETE | 2,521 | 1.5MB | Cash refund transactions |
| CashSale | ✅ COMPLETE | 385,665 | 270MB | Cash sale transactions |
| CustCred | ✅ COMPLETE | 20,298 | 18MB | Credit memo transactions |
| CustInvc | ✅ COMPLETE | 466,920 | 631MB | Invoice transactions |
| RtnAuth | ✅ COMPLETE | 10,504 | 13MB | Return authorization transactions |
| SalesOrd | ✅ COMPLETE | 547,962 | 601MB | Sales order transactions |

**Total Completed**: 1,433,870 records (~1.4M transactions)

---

## AUDIT Fields Extracted

### Transaction Lines (4 new fields)

| Field | Type | Purpose | Values |
|-------|------|---------|--------|
| `mainline` | T/F | Header vs line item | T = header, F = item line |
| `taxline` | T/F | Tax calculation line | T = tax line, F = regular |
| `iscogs` | T/F | COGS accounting entry | T = COGS, F = regular |
| `transactiondiscount` | T/F | Discount line | T = discount, F = regular |
| `netamount` | Number | Transaction currency amount | Decimal |

**Purpose**: Enable filtering of system-generated lines for accurate counts

### Transactions (3 new fields)

| Field | Type | Purpose | Values |
|-------|------|---------|--------|
| `posting` | T/F | Posted to GL vs draft | T = posted, F = non-posting |
| `voided` | T/F | Voided/cancelled | T = voided, F = active |
| `postingperiod` | String | Accounting period | YYYY-MM format |

**Purpose**: Enable filtering of non-financial transactions for accurate metrics

---

## File Locations

### Raw AUDIT Files

```
/data/netsuite_extractions/

Transaction Lines (MONTHLY chunks):
├── lines_CashRfnd_AUDIT_MONTHLY_20251124_170139_FINAL.json  (12,181 records)
├── lines_CustCred_AUDIT_MONTHLY_20251124_170246_FINAL.json  (92,585 records)
├── lines_RtnAuth_AUDIT_MONTHLY_20251124_170154_FINAL.json   (45,864 records)
├── lines_CashSale_AUDIT_*_FINAL.json (in progress - ~220 monthly files)
├── lines_CustInvc_AUDIT_*_FINAL.json (in progress - ~220 monthly files)
└── lines_SalesOrd_AUDIT_*_FINAL.json (in progress - ~220 monthly files)

Transactions (CHUNKED by date range):
├── transactions_CashRfnd_AUDIT_20251124_170103_FINAL.json   (2,521 records)
├── transactions_CashSale_AUDIT_20251124_171209_FINAL.json   (385,665 records)
├── transactions_CustCred_AUDIT_20251124_170133_FINAL.json   (20,298 records)
├── transactions_CustInvc_AUDIT_20251124_172507_FINAL.json   (466,920 records)
├── transactions_RtnAuth_AUDIT_20251124_170117_FINAL.json    (10,504 records)
└── transactions_SalesOrd_AUDIT_20251124_172004_FINAL.json   (547,962 records)
```

### CSV Files (also generated)

```
├── lines_CashRfnd_AUDIT_MONTHLY_20251124_170139_FINAL.csv   (912KB)
├── lines_CustCred_AUDIT_MONTHLY_20251124_170246_FINAL.csv   (7.1MB)
├── lines_RtnAuth_AUDIT_MONTHLY_20251124_170154_FINAL.csv    (3.6MB)
└── (transactions CSV files similar)
```

---

## Data Quality Validation

### Expected Line Type Distribution

**Transaction Lines** (when all complete):

| Line Type | Expected % | Expected Count | Purpose |
|-----------|-----------|----------------|---------|
| Product lines (mainline='F', taxline='F', iscogs='F') | 50-60% | ~4-5M | Actual sales |
| COGS lines (iscogs='T') | 25-30% | ~2-3M | Cost tracking |
| Tax lines (taxline='T') | 10-15% | ~1M | Tax calculation |
| Header lines (mainline='T') | ~10% | ~800K | Transaction headers |
| Discount lines (transactiondiscount='T') | <5% | ~200K | Discounts |

**Transactions**:

| Transaction Type | Records | Expected Posting % | Purpose |
|-----------------|---------|-------------------|---------|
| CustInvc | 466,920 | ~95% posting='T' | Customer invoices (financial) |
| SalesOrd | 547,962 | ~5% posting='T' | Sales orders (non-financial) |
| CashSale | 385,665 | ~98% posting='T' | Cash sales (financial) |
| CustCred | 20,298 | ~95% posting='T' | Credit memos (financial) |
| RtnAuth | 10,504 | ~5% posting='T' | Return authorizations (non-financial) |
| CashRfnd | 2,521 | ~98% posting='T' | Cash refunds (financial) |

---

## Next Steps

1. **Wait for completion** of remaining 3 line extractions (CashSale, CustInvc, SalesOrd)
2. **Upload to GCS** - See `GCP_UPLOAD_POST_PROCESSING_GUIDE.md`
3. **Post-process** - Create filtered "clean" versions
4. **Load to BigQuery** - Create external tables or native tables
5. **Update Cube** - Modify YML files per migration plan

---

## Estimated Completion Time

- **Lines CashSale**: ~2-3 hours remaining (largest dataset)
- **Lines CustInvc**: ~2-3 hours remaining (largest dataset)
- **Lines SalesOrd**: ~2-3 hours remaining (largest dataset)
- **Total**: ~3-4 hours for all to complete

**Current Progress**: 9 of 12 complete (75%)
**Estimated Files Generated**: ~660 monthly chunk files + 12 combined files
**Estimated Total Size**: ~3-4GB of parquet data

---

## Contact

For questions about this extraction:
- Extraction scripts: `/data/netsuite_extractions/master-scripts/extract_*_AUDIT.py`
- Logs: `/data/netsuite_extractions/audit_logs/*.log`
- Output: `/data/netsuite_extractions/*_AUDIT_*_FINAL.*`
