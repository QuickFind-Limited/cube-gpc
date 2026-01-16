#!/bin/bash

# Test simple SELECT * FROM table cubes

set -e

RESULTS_FILE="/tmp/simple_cube_validation.txt"

echo "==================================================" > "$RESULTS_FILE"
echo "Simple Cube SQL Validation (SELECT * FROM)" >> "$RESULTS_FILE"
echo "Test Date: $(date)" >> "$RESULTS_FILE"
echo "==================================================" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

TOTAL=0
PASSED=0
FAILED=0

test_table() {
    local cube_name="$1"
    local table_name="$2"

    TOTAL=$((TOTAL + 1))

    echo "Testing: $cube_name ($table_name)" >> "$RESULTS_FILE"
    echo "----------------------------------------" >> "$RESULTS_FILE"

    if echo "SELECT * FROM $table_name LIMIT 1" | bq query --use_legacy_sql=false --dry_run 2>&1 | grep -q "Query successfully validated"; then
        echo "✅ PASSED" >> "$RESULTS_FILE"
        PASSED=$((PASSED + 1))
    else
        echo "❌ FAILED" >> "$RESULTS_FILE"
        FAILED=$((FAILED + 1))
        echo "" >> "$RESULTS_FILE"
        echo "Error:" >> "$RESULTS_FILE"
        echo "SELECT * FROM $table_name LIMIT 1" | bq query --use_legacy_sql=false --dry_run 2>&1 >> "$RESULTS_FILE"
    fi

    echo "" >> "$RESULTS_FILE"
}

# Test the 4 simple cubes
test_table "fulfillments.yml" "gpc.fulfillments"
test_table "inventory.yml" "gpc.inventory_calculated"
test_table "locations.yml" "gpc.locations"
test_table "transactions.yml" "gpc.transactions_analysis"

# Summary
echo "==================================================" >> "$RESULTS_FILE"
echo "VALIDATION SUMMARY" >> "$RESULTS_FILE"
echo "==================================================" >> "$RESULTS_FILE"
echo "Total Tables Tested: $TOTAL" >> "$RESULTS_FILE"
echo "Passed: $PASSED" >> "$RESULTS_FILE"
echo "Failed: $FAILED" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

if [ $FAILED -gt 0 ]; then
    echo "⚠️  SOME TABLES FAILED VALIDATION" >> "$RESULTS_FILE"
else
    echo "✅ ALL TABLES VALIDATED SUCCESSFULLY" >> "$RESULTS_FILE"
fi

cat "$RESULTS_FILE"

exit $FAILED
