#!/bin/bash

# Systematic High-Risk Metrics Testing
# Tests 12-month queries for timeout issues
# Date range: 2024-11-01 to 2025-10-31 (12 months)
#
# Usage:
#   export CUBE_API_URL="https://your-cube-instance.cubecloudapp.dev/cubejs-api/v1"
#   export CUBE_API_TOKEN="your-api-token"
#   ./test_high_risk_metrics.sh
#
# Or pass as arguments:
#   ./test_high_risk_metrics.sh <API_URL> <API_TOKEN>

set -e

# API Configuration
if [ $# -eq 2 ]; then
    CUBE_API_URL="$1"
    CUBE_API_TOKEN="$2"
else
    CUBE_API_URL="${CUBE_API_URL:-https://aquamarine-ibex.gcp-europe-west1.cubecloudapp.dev/cubejs-api/v1}"
    CUBE_API_TOKEN="${CUBE_API_TOKEN}"
fi

# Validate credentials
if [ -z "$CUBE_API_TOKEN" ]; then
    echo "ERROR: CUBE_API_TOKEN not set"
    echo ""
    echo "Usage:"
    echo "  export CUBE_API_URL=\"https://your-cube-instance.cubecloudapp.dev/cubejs-api/v1\""
    echo "  export CUBE_API_TOKEN=\"your-api-token\""
    echo "  ./test_high_risk_metrics.sh"
    echo ""
    echo "Or pass as arguments:"
    echo "  ./test_high_risk_metrics.sh <API_URL> <API_TOKEN>"
    exit 1
fi

# Test timeout (30 seconds)
TIMEOUT=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Results file
RESULTS_FILE="/home/produser/cube-gpc/high_risk_test_results.txt"
echo "High-Risk Metrics Test Results - $(date)" > "$RESULTS_FILE"
echo "=======================================" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Function to test a metric
test_metric() {
    local test_name="$1"
    local query="$2"

    echo "Testing: $test_name"
    echo "Query: $query"
    echo ""

    # Record start time
    start_time=$(date +%s)

    # Make request with timeout
    response=$(curl -s --max-time $TIMEOUT \
        -H "Authorization: ${CUBE_API_TOKEN}" \
        -H "Content-Type: application/json" \
        -G \
        --data-urlencode "query=${query}" \
        "${CUBE_API_URL}/load" 2>&1) || {

        end_time=$(date +%s)
        duration=$((end_time - start_time))

        if [[ $duration -ge $TIMEOUT ]]; then
            echo -e "${RED}❌ TIMEOUT${NC} (${duration}s)"
            echo "$test_name: TIMEOUT (${duration}s)" >> "$RESULTS_FILE"
            echo "  Query: $query" >> "$RESULTS_FILE"
            echo "" >> "$RESULTS_FILE"
            return 1
        else
            echo -e "${RED}❌ ERROR${NC} (${duration}s)"
            echo "$test_name: ERROR (${duration}s)" >> "$RESULTS_FILE"
            echo "  Response: $response" >> "$RESULTS_FILE"
            echo "" >> "$RESULTS_FILE"
            return 1
        fi
    }

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    # Check for errors in response
    if echo "$response" | grep -q "error"; then
        error_msg=$(echo "$response" | grep -o '"error":"[^"]*"' | head -1)
        echo -e "${RED}❌ FAILED${NC} (${duration}s) - $error_msg"
        echo "$test_name: FAILED (${duration}s)" >> "$RESULTS_FILE"
        echo "  Error: $error_msg" >> "$RESULTS_FILE"
        echo "  Query: $query" >> "$RESULTS_FILE"
        echo "" >> "$RESULTS_FILE"
        return 1
    fi

    # Success
    echo -e "${GREEN}✓ PASSED${NC} (${duration}s)"
    echo "$test_name: PASSED (${duration}s)" >> "$RESULTS_FILE"
    echo "" >> "$RESULTS_FILE"
    echo ""
    return 0
}

echo "========================================="
echo "HIGH RISK METRICS TESTING"
echo "Date Range: 2024-11-01 to 2025-10-31 (12 months)"
echo "Timeout: ${TIMEOUT}s"
echo "========================================="
echo ""

# Test 1: MM001 - Gross Margin % (GL-based with JOIN)
echo "TEST 1: MM001 - Gross Margin % (GL-based COGS)"
test_metric "MM001_GrossMarginPct" '{
  "measures": ["transaction_lines.gl_based_gross_margin_pct"],
  "dimensions": ["transaction_lines.channel_type"],
  "timeDimensions": [{
    "dimension": "transaction_lines.transaction_date",
    "granularity": "month",
    "dateRange": ["2024-11-01", "2025-10-31"]
  }]
}'

# Test 2: GMROI001 - Gross Margin Return on Investment (GL-based)
echo "TEST 2: GMROI001 - GMROI (GL-based COGS)"
test_metric "GMROI001_GMROI" '{
  "measures": ["transaction_lines.gl_based_gmroi"],
  "dimensions": ["transaction_lines.category"],
  "timeDimensions": [{
    "dimension": "transaction_lines.transaction_date",
    "granularity": "month",
    "dateRange": ["2024-11-01", "2025-10-31"]
  }]
}'

# Test 3: LIFE004 - Sales Velocity (units per week)
echo "TEST 3: LIFE004 - Sales Velocity (units per week)"
test_metric "LIFE004_UnitsPerWeek" '{
  "measures": ["transaction_lines.units_per_week"],
  "dimensions": ["transaction_lines.category"],
  "timeDimensions": [{
    "dimension": "transaction_lines.transaction_date",
    "granularity": "month",
    "dateRange": ["2024-11-01", "2025-10-31"]
  }]
}'

# Test 4: RET004 - Return Rate (Customer Credits / Revenue Transactions)
echo "TEST 4: RET004 - Return Rate (transaction level)"
test_metric "RET004_ReturnRate" '{
  "measures": ["transactions.customer_credits_aligned", "transactions.revenue_transaction_count_aligned"],
  "dimensions": ["transactions.customer_type"],
  "timeDimensions": [{
    "dimension": "transactions.trandate",
    "granularity": "month",
    "dateRange": ["2024-11-01", "2025-10-31"]
  }]
}'

# Test 5: RET005 - Return Rate % (line-level)
echo "TEST 5: RET005 - Return Rate % (line level)"
test_metric "RET005_ReturnRatePct" '{
  "measures": ["transaction_lines.return_rate"],
  "dimensions": ["transaction_lines.category"],
  "timeDimensions": [{
    "dimension": "transaction_lines.transaction_date",
    "granularity": "month",
    "dateRange": ["2024-11-01", "2025-10-31"]
  }]
}'

# Test 6: FD002 - Fulfillments per Order
echo "TEST 6: FD002 - Fulfillments per Order"
test_metric "FD002_FulfillmentsPerOrder" '{
  "measures": ["fulfillments.fulfillments_per_order"],
  "dimensions": ["fulfillments.status_name"],
  "timeDimensions": [{
    "dimension": "fulfillments.trandate",
    "granularity": "month",
    "dateRange": ["2024-11-01", "2025-10-31"]
  }]
}'

# Test 7: MM001 Alternative - Total Revenue and GL COGS (component measures)
echo "TEST 7: MM001 Components - Revenue + GL COGS separately"
test_metric "MM001_Components" '{
  "measures": ["transaction_lines.total_revenue", "transaction_lines.gl_based_cogs"],
  "dimensions": ["transaction_lines.channel_type"],
  "timeDimensions": [{
    "dimension": "transaction_lines.transaction_date",
    "granularity": "month",
    "dateRange": ["2024-11-01", "2025-10-31"]
  }]
}'

# Test 8: GL COGS Only (from cogs cube directly)
echo "TEST 8: GL COGS - Direct from COGS cube"
test_metric "GL_COGS_Direct" '{
  "measures": ["transaction_accounting_lines_cogs.gl_cogs"],
  "dimensions": ["transaction_accounting_lines_cogs.category"],
  "timeDimensions": [{
    "dimension": "transaction_accounting_lines_cogs.transaction_date",
    "granularity": "month",
    "dateRange": ["2024-11-01", "2025-10-31"]
  }]
}'

echo ""
echo "========================================="
echo "TEST SUMMARY"
echo "========================================="
echo ""
echo "Results saved to: $RESULTS_FILE"
echo ""
cat "$RESULTS_FILE"
