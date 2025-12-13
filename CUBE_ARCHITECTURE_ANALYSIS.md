# Cube.dev Data Model Architecture Analysis
## Comprehensive Report - GymPlusCoffee/Cube.dev

---

## EXECUTIVE SUMMARY

The Cube.dev data model contains **27 cubes** organized across several layers with a mix of star schema patterns and some architectural anti-patterns. The primary fact table is `transaction_lines` with supporting dimension and bridge cubes. There are significant structural issues around **grain level conflicts**, **missing dimensions**, and **repeated dimension logic** that should be addressed systematically.

**Key Findings:**
- Primary fact cube: `transaction_lines` at grain: (transaction_id, item_id, location_id)
- Secondary customer dimension cubes: `b2c_customers`, `b2c_customer_channels`, `b2b_customers`
- Major structural issues: Conflicting grains, denormalized dimensions, missing channel/country availability
- Pre-aggregation strategy: Well-implemented with 30+ pre-aggs aligned to common queries
- Architecture Pattern: Hybrid star/snowflake with denormalization at transaction_lines level

---

## 1. CUBE STRUCTURE & HIERARCHY

### 1.1 Fact Tables (Transaction-Level Data)

| Cube Name | Grain | Primary Measures | Table Source | Notes |
|-----------|-------|------------------|--------------|-------|
| **transaction_lines** | (txn_id, item_id, location_id) | Revenue, units, costs, margins | transaction_lines_clean | MAIN fact table - denormalized with product/location dims |
| **landed_costs** | (transaction_id, line_id) | Landed costs, freight, duties | transaction_lines (filtered) | Subset of transaction_lines where ItemRcpt + blandedcost='T' |
| **fulfillment_lines** | (fulfillment_id, item_id, location_id) | Units shipped, fulfillment days | fulfillment_lines | Order fulfillment tracking |
| **order_baskets** | (order_id) | Basket size, AOV, units | transaction_lines (aggregated) | Order-level aggregation |
| **cross_sell** | (item_a_id, item_b_id, date) | Co-purchase counts | transaction_lines (self-join) | Product affinity pairs |
| **sell_through** | (item_id) | Sell-through %, current stock | items + inventory (joined) | DEPRECATED - has flaws |
| **sell_through_seasonal** | (item_id) | Season-specific sell-through | transaction_lines + inventory | REPLACEMENT - more accurate |

**Issue Found #1: Grain Conflict in Sell-Through**
- `sell_through` (DEPRECATED) mixes all-time cumulative sales with point-in-time inventory
- Result: Meaningless ratios like "all sales ever / today's stock"
- `sell_through_seasonal` fixes this by analyzing within-season boundaries
- **Impact**: Either use seasonal version or filter historical data carefully

### 1.2 Dimension/Bridge Tables (Master Data)

| Cube Name | Type | Grain | Primary Keys | Notes |
|-----------|------|-------|--------------|-------|
| **items** | Dimension | item_id | id, itemid (SKU) | Product master with category, section, season, size, color |
| **locations** | Dimension | location_id | id, name | Warehouse/store locations with channel_type logic |
| **b2c_customers** | Customer Dimension | (email, billing_country) | email | Aggregated B2C customer with LTV |
| **b2c_customer_channels** | Bridge | (email, country, channel) | (email, country, channel) | B2C customer behavior segmented by channel |
| **b2b_customers** | Customer Dimension | id (entity_id) | id | B2B wholesale customer master |
| **b2b_customer_addresses** | Address Bridge | (address_id, customer_id) | address_id | Links B2B customers to addresses |
| **b2b_addresses** | Address Dimension | address_id | address_id | B2B address reference |
| **transactions** | Transaction Header | transaction_id | id | Order/invoice/sales order headers |
| **currencies** | Reference | currency_id | id | Currency codes + exchange rates |
| **departments** | Reference | department_id | id | Business departments (eCommerce, Retail, etc.) |
| **classifications** | Reference | class_id | id | Business classifications (EU Website, Kildare Village, etc.) |
| **subsidiaries** | Reference | subsidiary_id | id | Legal entities (GPC Ireland, GPC UK) |

**Issue Found #2: Customer Dimension Design**
- B2C customers split across TWO cubes: `b2c_customers` and `b2c_customer_channels`
- `b2c_customers` grain: (email, billing_country) - aggregates all channels together
- `b2c_customer_channels` grain: (email, country, channel) - breaks down by channel
- **Problem**: Cannot easily answer "how many unique customers across all channels?" vs "per channel"
- **Root Cause**: Email + country is not a complete unique identifier for customers - they may buy through multiple channels
- **Impact**: Requires using `unique_customers` measure in b2c_customer_channels or custom calculations

### 1.3 Supply Chain/Inventory Tables

| Cube Name | Grain | Measures | Notes |
|-----------|-------|----------|-------|
| **inventory** | (item_id, location_id) | Stock levels, available, backorder | Point-in-time snapshot |
| **on_order_inventory** | (po_line_id, item_id) | On-order qty, value | Real-time PO tracking |
| **purchase_orders** | po_id | PO count, total value | PO headers |
| **purchase_order_lines** | po_line_id | Ordered qty, received qty, cost | PO line details |
| **item_receipts** | receipt_id | Receipt count, value | Receipt headers (goods in) |
| **item_receipt_lines** | receipt_line_id | Received qty, unit cost | Receipt line details + PO linkage |
| **supplier_lead_times** | (receipt_line_id) | Lead time days, variance, std_dev | PO-to-receipt lead times |

**Issue Found #3: No Direct Link Between Supplier and Products**
- `purchase_order_lines` has supplier via PO header relationship, but not directly queryable
- To analyze "supplier X's product performance" requires joining through multiple tables
- **Missing Dimension**: No supplier dimension cube

---

## 2. DIMENSION MANAGEMENT ANALYSIS

### 2.1 Repeated Dimensions Across Cubes

| Dimension | Used In | Type | Grain Issue | Notes |
|-----------|---------|------|------------|-------|
| **channel_type** | transaction_lines, inventory, locations | Denormalized | CONFLICT | Defined in locations but denormalized into transaction_lines via join. Inventory must use locations dimension for channel. |
| **billing_country** | transaction_lines, transactions, b2c_customers, b2b_customers | Denormalized | PARTIAL | Copied into multiple cubes, not linked as foreign keys |
| **shipping_country** | transaction_lines, transactions | Denormalized | PARTIAL | Same as billing_country |
| **item dims** | transaction_lines, items, inventory | Mixed | OK | Items denormalized (SKU, name, category, etc.) in transaction_lines AND separate items cube |
| **location** | transaction_lines, inventory, locations | Mixed | OK | Location name available in both; transactions also have denormalized location_name |
| **currency_name** | transaction_lines, transactions | Denormalized | OK | Currency code denormalized into transaction_lines |
| **department_name** | transaction_lines | Denormalized | OK | Denormalized from departments reference table |
| **classification_name** | transaction_lines | Denormalized | OK | Denormalized from classifications reference table |
| **subsidiary** | transactions, purchase_orders | Mixed | OK | Both store subsidiary ID, can join to subsidiaries dimension |

**Issue Found #4: Channel Type Centralization Conflict**
- **Design Decision**: Centralize channel_type logic in locations cube (via CASE statement - lines 25-42)
- **Implementation**: transaction_lines joins to locations by name (`location_name = locations.name`)
- **Problem**: Inventory cube cannot use this same join pattern - it joins via location_id
  - Result: Inventory has to reference `locations.channel_type` in pre-agg dimensions
  - Makes channel_type available in inventory queries but through a more complex path
- **Impact**: Inconsistent access paths - some cubes use direct relationship, others use locations dimension reference

**Issue Found #5: B2C Customer Grain Ambiguity**
- Grain: `(email, billing_country)`
- **Problem**: Email is the real unique identifier, but billing_country splits the same customer into multiple rows
- **Question**: If a customer buys to Ireland then UK (different billing countries), are they 1 or 2 customers?
- **Current answer**: 2 separate rows in the cube
- **Impact**: Customer count = # of (email, country) pairs, not # of unique emails
  - This is intentional (to support country-level analysis), but can be confusing

### 2.2 Conformed Dimensions vs Non-Conformed

**Conformed (Properly Standardized):**
- Items (SKU, category, section, season, size, color, collection, range)
- Locations (name, channel_type, location_type, region)
- Currencies (name, symbol, exchange rate)
- Subsidiaries (name, country)
- Departments (name)
- Classifications (name)

**Non-Conformed (Problematic):**
- **Countries**: billing_country and shipping_country are strings, not linked to a countries dimension
  - Used directly in transaction_lines, transactions, b2c_customers
  - No master list of valid countries
  - Risk: Typos, inconsistent naming
- **Email/Customer**: No customer master table for B2C - only aggregated cubes
  - Email is denormalized into multiple cubes
  - No single source of truth for customer metadata
- **Transaction Types**: Hard-coded as 'SalesOrd', 'CustInvc', 'CashSale', 'ItemRcpt' - no type dimension

### 2.3 Dimensions at Correct Grain

**Correctly Grained:**
- Items dimension fits naturally with transaction_lines (many transactions per item)
- Locations dimension fits with inventory (one inventory per location per item)
- Customer dimensions fit their respective cubes (email is PK for b2c_customers)
- Currencies/subsidiaries/departments fit as reference tables

**Questionable Grains:**
- **Landed costs cube** grain: (transaction_id, line_id) - this is just a filtered subset of transaction_lines
  - Redundant with transaction_lines' itemrcpt measures
  - Separate cube exists only because it's ItemRcpt-specific (blandedcost='T')
  - Could be consolidated, but separation is OK for organizational clarity

---

## 3. JOIN PATTERNS & RELATIONSHIPS

### 3.1 Join Topology

**Star Schema (transaction_lines as center):**
```
                    items (many_to_one)
                       |
transactions_analysis  |
         |              |
         |---> transaction_lines <------ locations (many_to_one)
         |
         |---> currencies
         |---> subsidiaries
```

**Bridge Tables (for analysis):**
```
b2c_customer_channels
    |---> locations (via channel_type match)
    
b2b_customer_addresses
    |---> b2b_customers (many_to_one)
    
fulfillment_lines
    |---> fulfillments (many_to_one)
    |---> transactions (many_to_one, via fulfillments.entity)
    |---> items (many_to_one)
    |---> locations (many_to_one)
```

**Supply Chain:**
```
purchase_orders
    |---> purchase_order_lines (one_to_many)
              |---> items (many_to_one)
              |---> item_receipt_lines (via createdfrom)
                       |---> item_receipts (many_to_one)
                       |---> supplier_lead_times (derived)
```

### 3.2 Many-to-Many Risk Analysis

**Potential M2M Issues:**

1. **transaction_lines + inventory join:**
   - SQL: `"{CUBE}.item = {inventory.item}"`
   - **Risk Level**: HIGH
   - **Issue**: No location filter, so one transaction_line can match ALL inventory positions for that item
   - **Cause**: Missing join condition on location
   - **Current Use**: Allowed in transaction_lines for inventory-sales correlation
   - **Impact**: Will fan-out when used, need to limit dimensions carefully

2. **fulfillment_lines + transactions join:**
   - Path: fulfillment_lines -> fulfillments -> transactions
   - SQL: `"{fulfillments}.entity = {transactions.id}"`
   - **Risk Level**: MEDIUM-HIGH
   - **Issue**: fulfillments.entity is the ORDER (source transaction), but semantics unclear
   - **Impact**: Can create confusion about relationship direction

3. **cross_sell self-join on transaction_lines:**
   - SQL: `tl1.transaction = tl2.transaction AND tl1.item < tl2.item`
   - **Risk Level**: MEDIUM
   - **Issue**: Multiple items per transaction, so multiple pairs generated per transaction
   - **Impact**: Expected and used for affinity analysis, but requires care with aggregations

### 3.3 Join Path Complexity Issues

**Issue Found #6: Inconsistent Join Paths to Locations**

1. **transaction_lines** joins to locations via NAME:
   ```yaml
   - name: locations
     sql: "{CUBE}.location_name = {locations.name}"
   ```
   
2. **inventory** joins to locations via ID:
   ```yaml
   - name: locations
     sql: "{CUBE}.location = {locations.id}"
   ```
   
3. **fulfillment_lines** joins to locations via ID:
   ```yaml
   - name: locations
     sql: "{CUBE}.location = {locations.id}"
   ```

**Problem**: Transaction lines use location NAME as join key, but location table has ID. This works because location_name is denormalized, but it's fragile:
- If location name changes, the join breaks
- If two locations have similar names, join may be ambiguous
- Should use location ID consistently

**Why it happened**: transaction_lines denormalizes location_name but not location_id, so the join must be by name.

---

## 4. PRE-AGGREGATION STRATEGY

### 4.1 Pre-Aggregation Alignment with Query Patterns

**transaction_lines (19 pre-aggs)** - Very well designed:

| Pre-Agg Name | Measures | Dimensions | Grain | Rationale |
|--------------|----------|-----------|-------|-----------|
| sales_analysis | Revenue, units, costs, tax, discount, margins | channel_type, category, section, season, collection, product_range, dept, class, billing_country, currency | DAY | Most common sales queries (D2C vs Retail, by product) |
| product_analysis | Revenue, units, margin, txn_count, sku_count | sku, name, category, section, season, size, color, range | DAY | Product-level drill-downs |
| location_analysis | Revenue, units, txn_count, margin | location_name, channel_type, dept, class | DAY | Store/warehouse performance |
| daily_metrics | Revenue, units, txn_count | channel_type | DAY | Simple daily dashboard |
| discount_analysis | Revenue, discount, discounted_units, units | channel_type, category, section, season, pricing_type | DAY | Discount tracking (DM001/DM002) |
| customer_geography | Revenue, units, txn_count | customer_email, billing_country, shipping_country | DAY | Geographic/customer patterns |
| product_range_analysis | Revenue, units, margin, discount, dates | product_range, collection, category, section, season | MONTH | Range/collection trends |
| size_geography | Units, revenue | size, color, billing_country, category, section | DAY | Size curve by region |
| transaction_type_analysis | Revenue, units, txn_count | transaction_type, channel_type, billing_country | DAY | Type breakdown |
| weekly_metrics | Revenue, units, txn_count | channel_type, category, section | DAY | Weekly trends |
| product_geography | Revenue, units, margin, txn_count | sku, name, category, section, season, billing_country | DAY | Product X Geography matrix |
| channel_product | Revenue, units, margin, txn_count | channel_type, category, section, season, size, sku | DAY | D2C vs Retail product comparison |
| size_color_analysis | Revenue, units, margin | size, color, category, section, season, channel_type | DAY | Fashion size/color combos |
| size_location_analysis | Revenue, units, margin | size, location_name, class, category, section, season, channel_type | DAY | Store size curves |
| yearly_metrics | Revenue, units, txn_count, margin | channel_type, category, section, billing_country | YEAR | YoY comparison |
| transaction_grain_aov | Revenue, line_count, units | transaction, channel_type, category, section, billing_country | DAY | **Exact transaction counts for AOV (OM002)** |

**✓ Strengths:**
- Covers all major dimensions (channel, category, section, season, geography)
- Multiple granularities (day, month, year)
- Partition strategy (by month) matches refresh patterns
- Includes exact count pre-agg for AOV calculations (transaction_grain_aov)

**Issue Found #7: Missing Pre-Aggregation**
- No pre-agg for **time-series trends** (date trending)
- No pre-agg for **customer-level analysis** (would require different cube - b2c_customers already has this)
- No pre-agg for **supplier_id dimension** in any cube (hidden in purchase_orders header)

### 4.2 Overlapping/Redundant Pre-Aggregations

Most are distinct, but some overlap:
- `sales_analysis` and `weekly_metrics` overlap heavily (same granularity, mostly same dimensions)
- `product_analysis` is more specific than `sales_analysis` 
- `product_range_analysis` is a subset of `product_analysis` (but at MONTH granularity)

**Not redundant, just complementary** - each serves a different query pattern.

---

## 5. SPECIFIC ISSUES DEEP DIVE

### 5.1 B2C Customers Cube - Grain & Dimensions Analysis

**Grain: (email, billing_country)**
- Email is the identifying field (primary_key)
- Billing country is an additional grouping dimension
- Result: Same email appearing 2x if they bought to UK and Ireland

**Dimensions Available:**
- email (PK)
- billing_country
- first_order_date (time)
- last_order_date (time)
- order_count (numeric)
- lifetime_value (numeric)
- customer_tier (derived CASE)
- recency_bucket (derived CASE)
- purchase_frequency_bucket (derived CASE)

**Issue Found #8: Missing Channel Dimension in b2c_customers**
- Cube has NO way to answer: "What % of high-value customers come from D2C vs Retail?"
- Must switch to `b2c_customer_channels` cube, which HAS channel_type
- But b2c_customer_channels has different grain: (email, country, channel)
- **Problem**: Cannot easily pivot between "all customers" view and "customers by channel" view
- **Workaround**: Use b2c_customer_channels with `unique_customers` measure for cross-channel customer count

### 5.2 Transaction Lines - Missing Dimensions

**Available dimensions:**
- item-level: sku, product_name, category, section, season, size, color, collection, product_range
- location-level: location_name, channel_type
- geography: billing_country, shipping_country, currency_name
- time: transaction_date (parameterized), month, quarter, year, week
- business: department_name, classification_name, transaction_type, pricing_type
- financial: quantity, amount, rate, costestimate, exchange_rate

**Missing Dimensions:**
- **supplier** - No way to analyze by supplier directly; would need to join through inventory->items->purchase_order_lines
- **customer** - Only customer_email available (no customer ID, no customer tier/segment)
- **order_id** - No order-level grouping (only transaction_id which is line-level)
- **status** - No order/fulfillment status breakdown
- **shipping_method** - No shipping carrier or method
- **payment_method** - No payment type

**Impact**: Many queries will require complex joins or won't be possible:
- "Units shipped by supplier" requires extra joins
- "Revenue by customer tier" requires customer dimension
- "Sales by fulfillment status" not possible

### 5.3 Inventory Cube - Channel & Country Availability

**Available dimensions in inventory:**
- item (via join)
- location (via join)
- stock_status (calculated: In Stock, Zero Stock, Backorder)
- items.category, items.section, items.season, items.size, items.range, items.markdown
- locations.name, locations.channel_type, locations.location_type, locations.region

**Available in pre-agg dimensions:**
- location
- stock_status
- items.* (category, section, season, size, range, markdown)
- locations.name
- locations.region
- locations.channel_type ✓ (added in latest version)
- locations.location_type ✓ (added in latest version)

**Status**: ✓ FIXED - Both channel_type and region are available in pre-agg

**Country dimension**: ⚠️ MISSING
- Inventory only has location-level data
- Locations have region (IRELAND, UK, EU, GLOBAL) but not country
- Cannot answer "inventory by country" without additional mapping

---

## 6. ARCHITECTURE PATTERNS

### 6.1 Schema Type Assessment

**Predominant Pattern: Denormalized Star Schema**

- **Central Fact**: transaction_lines (fully denormalized with product/location/currency attributes)
- **Dimension Tables**: items, locations, currencies, subsidiaries, departments, classifications
- **Hybrid Approach**: Mix of pure dimensions and bridge/aggregate cubes

**Snowflake Elements:**
- item_receipts <- item_receipt_lines <- supplier_lead_times (fact->detail->derived)
- purchase_orders <- purchase_order_lines <- items/suppliers
- fulfillments <- fulfillment_lines <- transactions

### 6.2 Anti-Patterns Identified

**Issue Found #9: Measures in Dimension Cubes**

1. **items cube** - Contains `item_count`, `active_item_count`
   - These are fine (count of items is a valid measure for a dimension table)
   
2. **locations cube** - Contains `location_count`
   - Questionable (usually dimension tables don't have measures)
   - Valid use case: Checking number of active locations
   
3. **currencies cube** - Contains `currency_count`
   - Not really needed
   
**Anti-Pattern**: These are reference/dimension tables being queried as fact tables
- **Solution**: Keep measures for operational monitoring only, don't rely on them for analysis
- **Not critical**, just slightly messy design

**Issue Found #10: Calculated Measures in Pre-Aggregations**

Multiple cubes include calculated measures in pre-aggs, which violates best practices:
- **discount_rate** in transaction_lines: calculated (REMOVED from pre-agg - good fix)
- **average_order_value** in transaction_lines: calculated (REMOVED from pre-agg - good fix)
- **fulfillments_per_order** in fulfillments: calculated (REMOVED from pre-agg - good fix)

**Status**: ✓ FIXED - All calculated measures removed from pre-aggs, using component measures instead

### 6.3 Fact Table Design Issues

**Issue Found #11: Denormalization Depth**

transaction_lines denormalizes extensively:
- Product attributes (10+ fields): sku, name, category, section, season, size, color, range, collection
- Location name (1 field)
- Currency name (1 field)
- Department & classification names (2 fields)
- Transaction header info (4 fields): type, currency, date, status

**Rationale**: Improves query performance, reduces joins
**Cost**: Storage overhead, update complexity if source data changes
**Assessment**: ✓ ACCEPTABLE - Standard practice for data warehouses

---

## 7. SPECIFIC QUERY PATTERN ISSUES

### 7.1 Can You Analyze...?

| Query | Possible? | How | Complexity | Notes |
|-------|-----------|-----|-----------|-------|
| Revenue by channel | ✓ | transaction_lines.channel_type | Simple | Pre-agg: sales_analysis |
| Revenue by supplier | ✗ | No direct dimension | HARD | Need: items <- purchase_order_lines <- purchase_orders |
| Revenue by customer tier | ✗ (B2C only) | b2c_customers.customer_tier | MEDIUM | Must segment b2c vs b2b separately |
| Revenue by country | ✓ | transaction_lines.billing_country | Simple | Pre-agg: customer_geography |
| Inventory by channel | ✓ | inventory > locations.channel_type | Medium | Requires locations join in pre-agg |
| Inventory by country | ✗ | No country mapping for locations | HARD | Locations have region not country |
| Lead time by supplier | ✓ | supplier_lead_times.supplier_id | Simple | Pre-agg: lead_time_rollup |
| Customer LTV by channel | ✓ (B2C only) | b2c_customer_channels.channel_lifetime_value | Simple | Pre-agg: customer_channel_analysis |
| Order status breakdown | ✗ | transactions cube has status but no transaction_lines link | MEDIUM | Would need to join transactions to transaction_lines |
| Product affinity | ✓ | cross_sell cube | Medium | Pre-agg: cross_sell_analysis |
| Sell-through by season | ✓ | sell_through_seasonal cube | Simple | Pre-agg: seasonal_sellthrough |

### 7.2 Hard Queries Requiring Custom Joins

1. **"Top 10 suppliers by revenue"**
   - Need: transaction_lines -> items -> purchase_order_lines -> purchase_orders
   - Missing: Supplier ID in transaction_lines denormalization
   - Workaround: Create a supplier_id dimension cube

2. **"Customer retention by segment"**
   - Need: customer segment (not in any cube)
   - Missing: Cohort tracking dimension
   - Workaround: Add customer_tier to transaction_lines, or use b2c_customers as bridge

3. **"SKU performance by location vs competition"**
   - Missing: Competitor sales data
   - Need: Additional competitive analysis cube

---

## 8. ARCHITECTURAL RECOMMENDATIONS

### 8.1 Priority 1: Critical Issues (Fix First)

**Issue #1: Add Supplier Dimension**
- Create `supplier_dimension` cube from purchase_orders, aggregating by supplier entity
- Add `supplier_id` to transaction_lines' purchase order connection chain
- Enables: "Revenue by supplier" queries without complex joins

**Issue #2: Fix Location Join in transaction_lines**
- Change join from name-based to ID-based
- Denormalize location_id into transaction_lines
- Current risk: Name changes break the join; ambiguous names fail silently

**Issue #3: Add Country Dimension**
- Create `countries` reference cube with country codes and names
- Link from: transactions (billing_country, shipping_country), inventory (via locations), b2b_addresses
- Replace string-based geography with proper dimension

### 8.2 Priority 2: Major Architectural Improvements

**Issue #4: Consolidate Customer Dimensions**
- Current: b2c_customers (email, country) + b2c_customer_channels (email, country, channel)
- Proposal: Single `b2c_customers_bridge` with (email, country, channel) grain
  - Include `all_channels` aggregation in separate pre-agg
  - Add customer_tier calculation based on total LTV (across all channels)
  - Adds channel as first-class dimension to customer analysis

**Issue #5: Create Order-Level Cube**
- Current: transaction_lines is line-grain; order_baskets exists but minimal
- Proposal: Full `orders` cube with (order_id) grain containing:
  - Order status, fulfillment status
  - Order metrics: total, units, line_count
  - Customer info: email, country, tier
  - Channel type from location
  - Enables order-level analysis without aggregating line data

**Issue #6: Separate ItemReceipt Stream**
- Current: ItemReceipt mixed with sales in transaction_lines
- Proposal: Create separate `inventory_receipts` cube for ItemRcpt transactions
  - Keep landed_costs separate for cost analysis
  - Cleaner separation of concerns

### 8.3 Priority 3: Pre-Aggregation Enhancements

**Issue #7: Add Supplier Pre-Aggregation**
```yaml
- name: supplier_analysis  # NEW
  measures: [total_revenue, units_sold, transaction_count, gross_margin]
  dimensions: [supplier, category, section, channel_type]
  time_dimension: transaction_date
  granularity: month
```

**Issue #8: Add Customer Cohort Pre-Aggregation**
```yaml
- name: customer_cohort_analysis  # NEW
  measures: [customer_count, unique_customers, repeat_customers, total_ltv]
  dimensions: [cohort_month, customer_tier, billing_country]
  granularity: month
```

### 8.4 Priority 4: Documentation & Clarity

**Issue #9: Document Dimension Conflicts**
- Channel type has two access paths (direct in transaction_lines vs via locations join in inventory)
- Document when to use which approach
- Add warnings to cube descriptions

**Issue #10: Add Grain Contracts to Cube Descriptions**
- Each cube should state: "This cube has grain (field1, field2...)"
- Warn about duplicates: "Customer (email, country) pairs - same email may appear 2x"
- Clarify aggregation semantics

---

## 9. SUMMARY TABLE: All 27 Cubes

| # | Cube Name | Grain | Type | Key Measures | Issues |
|----|-----------|-------|------|--------------|--------|
| 1 | transaction_lines | (txn_id, item_id, loc_id) | FACT | Revenue, units, costs, margins | Missing: supplier_id, customer_id, status |
| 2 | b2c_customers | (email, billing_country) | DIM | Customer count, LTV, repeat rate | Missing: channel_type dimension |
| 3 | b2c_customer_channels | (email, country, channel) | BRIDGE | Customer count, LTV by channel | OK |
| 4 | b2b_customers | (customer_id) | DIM | Customer count, balance, aged aging | OK |
| 5 | b2b_customer_addresses | (address_id, cust_id) | BRIDGE | Address count | OK |
| 6 | b2b_addresses | (address_id) | DIM | Address reference | OK |
| 7 | items | (item_id) | DIM | Item count | OK |
| 8 | locations | (location_id) | DIM | Location count | Channel logic centralized here (good) |
| 9 | inventory | (item_id, location_id) | SNAPSHOT | Stock levels, SKU count | Missing: country dimension |
| 10 | transactions | (txn_id) | FACT_HDR | Transaction count, customer count | Redundant with transaction_lines header |
| 11 | currencies | (currency_id) | REF | Currency count | OK |
| 12 | departments | (dept_id) | REF | Department count | OK |
| 13 | classifications | (class_id) | REF | Classification count | OK |
| 14 | subsidiaries | (sub_id) | REF | Subsidiary count | OK |
| 15 | purchase_orders | (po_id) | FACT_HDR | PO count, total value | Supplier hidden in entity field |
| 16 | purchase_order_lines | (po_line_id) | FACT | Order qty, received qty, cost | OK - good traceability |
| 17 | item_receipts | (receipt_id) | FACT_HDR | Receipt count, value | OK |
| 18 | item_receipt_lines | (receipt_line_id) | FACT | Received qty, unit cost | Good: createdfrom links to PO |
| 19 | supplier_lead_times | (irl_id) | DERIVED | Lead time days, variance | OK - calculated from PO + receipt link |
| 20 | on_order_inventory | (po_line_id) | SNAPSHOT | On-order qty, value | OK - derived from open POs |
| 21 | landed_costs | (txn_id, line_id) | FACT | Landed costs (freight, duty) | OK - subset of ItemRcpt lines |
| 22 | fulfillments | (fulfillment_id) | FACT_HDR | Fulfillment count, shipped count | OK |
| 23 | fulfillment_lines | (fulfillment_line_id) | FACT | Units shipped, fulfillment days | OK |
| 24 | sell_through | (item_id) | SNAPSHOT | Sell-through % | DEPRECATED - flawed grain |
| 25 | sell_through_seasonal | (item_id) | SNAPSHOT | Season-specific sell-through % | REPLACEMENT - correct grain |
| 26 | order_baskets | (order_id) | AGGREGATE | Revenue, units, basket size | OK - order level summary |
| 27 | cross_sell | (item_a, item_b, date) | DERIVED | Co-purchase counts | OK - product affinity |

---

## 10. KEY ARCHITECTURAL METRICS

| Metric | Value | Assessment |
|--------|-------|-----------|
| Total Cubes | 27 | Large but manageable |
| Fact Cubes | 8 | (transaction_lines, transactions, purchase_orders, item_receipts, fulfillments, landed_costs, supplier_lead_times, on_order_inventory) |
| Dimension Cubes | 12 | (items, locations, currencies, departments, classifications, subsidiaries, b2c_customers, b2b_customers, b2b_addresses, etc.) |
| Bridge/Aggregate Cubes | 7 | (b2c_customer_channels, b2b_customer_addresses, order_baskets, cross_sell, sell_through, sell_through_seasonal, fulfillment_lines, inventory) |
| Total Pre-Aggs | 30+ | Well-designed, mostly non-overlapping |
| Max Join Depth | 5 levels | (transaction_lines -> items -> purchase_order_lines -> purchase_orders -> supplier) |
| Denormalized Fact Cube | transaction_lines | Extensive denormalization (15+ attributes) |
| Grain Conflicts | 2 | (sell_through vs sell_through_seasonal, b2c_customers vs b2c_customer_channels) |
| Missing Dimensions | 5+ | (supplier in transaction_lines, country in inventory, customer in transaction_lines, order status, payment method) |

---

## CONCLUSION

The Cube.dev data model is **well-structured overall** with good pre-aggregation strategy and appropriate use of denormalization. However, there are **actionable architectural issues** that would improve usability:

1. **Add missing dimensions** (supplier, country, customer)
2. **Fix join inconsistencies** (location name vs ID)
3. **Consolidate customer cubes** (merge b2c dimensions)
4. **Document grain contracts** clearly

The model supports most common business queries with existing pre-aggregations, but requires workarounds for supplier/customer analysis and lacks true country-level filtering capability.

