#!/usr/bin/env python3
"""
Systematic Metrics Testing for Cube.js Performance
Tests 12-month queries to identify timeout issues

Usage:
    export CUBE_API_URL="https://your-instance.cubecloudapp.dev/cubejs-api/v1"
    export CUBE_API_TOKEN="your-api-token"
    python3 test_metrics.py

Or:
    python3 test_metrics.py --url <API_URL> --token <API_TOKEN>
"""

import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Tuple, List
from datetime import datetime

# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


class MetricTester:
    def __init__(self, api_url: str, api_token: str, timeout: int = 30):
        self.api_url = api_url
        self.api_token = api_token
        self.timeout = timeout
        self.results: List[Dict[str, Any]] = []

    def test_metric(self, test_id: str, name: str, description: str, query: Dict[str, Any]) -> Tuple[bool, float, str]:
        """
        Test a single metric query

        Returns: (success, duration, error_message)
        """
        print(f"\n{Colors.BOLD}Testing {test_id}: {name}{Colors.NC}")
        print(f"Description: {description}")
        print(f"Query: {json.dumps(query, indent=2)}")

        start_time = time.time()

        try:
            # Prepare request
            query_str = json.dumps(query)
            params = urllib.parse.urlencode({'query': query_str})
            url = f"{self.api_url}/load?{params}"

            req = urllib.request.Request(url)
            req.add_header('Authorization', self.api_token)
            req.add_header('Content-Type', 'application/json')

            # Make request with timeout
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
                duration = time.time() - start_time

                # Check for errors in response
                if 'error' in data:
                    error_msg = data.get('error', 'Unknown error')
                    print(f"{Colors.RED}❌ FAILED{Colors.NC} ({duration:.2f}s) - {error_msg}")
                    self.results.append({
                        'test_id': test_id,
                        'name': name,
                        'status': 'FAILED',
                        'duration': duration,
                        'error': error_msg
                    })
                    return False, duration, error_msg

                print(f"{Colors.GREEN}✓ PASSED{Colors.NC} ({duration:.2f}s)")
                self.results.append({
                    'test_id': test_id,
                    'name': name,
                    'status': 'PASSED',
                    'duration': duration
                })
                return True, duration, ""

        except urllib.error.URLError as e:
            duration = time.time() - start_time
            if duration >= self.timeout:
                error_msg = f"TIMEOUT after {duration:.2f}s"
                print(f"{Colors.RED}❌ TIMEOUT{Colors.NC} ({duration:.2f}s)")
            else:
                error_msg = str(e)
                print(f"{Colors.RED}❌ ERROR{Colors.NC} ({duration:.2f}s) - {error_msg}")

            self.results.append({
                'test_id': test_id,
                'name': name,
                'status': 'TIMEOUT' if duration >= self.timeout else 'ERROR',
                'duration': duration,
                'error': error_msg
            })
            return False, duration, error_msg

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            print(f"{Colors.RED}❌ ERROR{Colors.NC} ({duration:.2f}s) - {error_msg}")
            self.results.append({
                'test_id': test_id,
                'name': name,
                'status': 'ERROR',
                'duration': duration,
                'error': error_msg
            })
            return False, duration, error_msg

    def print_summary(self):
        """Print test summary"""
        print(f"\n{Colors.BOLD}{'='*60}{Colors.NC}")
        print(f"{Colors.BOLD}TEST SUMMARY{Colors.NC}")
        print(f"{Colors.BOLD}{'='*60}{Colors.NC}\n")

        passed = sum(1 for r in self.results if r['status'] == 'PASSED')
        failed = sum(1 for r in self.results if r['status'] == 'FAILED')
        timeout = sum(1 for r in self.results if r['status'] == 'TIMEOUT')
        error = sum(1 for r in self.results if r['status'] == 'ERROR')
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.NC}")
        print(f"{Colors.RED}Failed: {failed}{Colors.NC}")
        print(f"{Colors.RED}Timeout: {timeout}{Colors.NC}")
        print(f"{Colors.YELLOW}Error: {error}{Colors.NC}")
        print()

        # Print detailed results
        print(f"{Colors.BOLD}Detailed Results:{Colors.NC}\n")
        for result in self.results:
            status_color = Colors.GREEN if result['status'] == 'PASSED' else Colors.RED
            print(f"  {result['test_id']}: {status_color}{result['status']}{Colors.NC} ({result['duration']:.2f}s)")
            if 'error' in result:
                print(f"    Error: {result['error']}")

        print()

    def save_results(self, filename: str):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total': len(self.results),
                    'passed': sum(1 for r in self.results if r['status'] == 'PASSED'),
                    'failed': sum(1 for r in self.results if r['status'] == 'FAILED'),
                    'timeout': sum(1 for r in self.results if r['status'] == 'TIMEOUT'),
                    'error': sum(1 for r in self.results if r['status'] == 'ERROR')
                },
                'results': self.results
            }, f, indent=2)
        print(f"Results saved to: {filename}")


def main():
    parser = argparse.ArgumentParser(description='Test Cube.js metrics for performance issues')
    parser.add_argument('--url', help='Cube API URL')
    parser.add_argument('--token', help='Cube API Token')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds (default: 30)')
    parser.add_argument('--output', default='test_results.json', help='Output file for results')

    args = parser.parse_args()

    # Get credentials
    api_url = args.url or os.environ.get('CUBE_API_URL')
    api_token = args.token or os.environ.get('CUBE_API_TOKEN')

    if not api_url or not api_token:
        print(f"{Colors.RED}ERROR: Missing API credentials{Colors.NC}\n")
        print("Set environment variables:")
        print('  export CUBE_API_URL="https://your-instance.cubecloudapp.dev/cubejs-api/v1"')
        print('  export CUBE_API_TOKEN="your-api-token"')
        print("\nOr use command-line arguments:")
        print("  python3 test_metrics.py --url <URL> --token <TOKEN>")
        sys.exit(1)

    # Create tester
    tester = MetricTester(api_url, api_token, args.timeout)

    print(f"{Colors.BOLD}{'='*60}{Colors.NC}")
    print(f"{Colors.BOLD}HIGH RISK METRICS TESTING{Colors.NC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.NC}")
    print(f"Date Range: 2024-11-01 to 2025-10-31 (12 months)")
    print(f"Timeout: {args.timeout}s")
    print(f"API URL: {api_url}")
    print(f"{Colors.BOLD}{'='*60}{Colors.NC}")

    # Test 1: MM001 - Gross Margin % (GL-based with JOIN)
    tester.test_metric(
        "MM001",
        "Gross Margin % (GL-based COGS)",
        "Uses gl_based_gross_margin_pct which requires JOIN to transaction_accounting_lines_cogs",
        {
            "measures": ["transaction_lines.gl_based_gross_margin_pct"],
            "dimensions": ["transaction_lines.channel_type"],
            "timeDimensions": [{
                "dimension": "transaction_lines.transaction_date",
                "granularity": "month",
                "dateRange": ["2024-11-01", "2025-10-31"]
            }]
        }
    )

    # Test 2: GMROI001 - GMROI (GL-based)
    tester.test_metric(
        "GMROI001",
        "GMROI (GL-based COGS)",
        "Gross Margin Return on Investment using GL COGS (requires JOIN)",
        {
            "measures": ["transaction_lines.gl_based_gmroi"],
            "dimensions": ["transaction_lines.category"],
            "timeDimensions": [{
                "dimension": "transaction_lines.transaction_date",
                "granularity": "month",
                "dateRange": ["2024-11-01", "2025-10-31"]
            }]
        }
    )

    # Test 3: LIFE004 - Sales Velocity (units per week)
    tester.test_metric(
        "LIFE004",
        "Sales Velocity (units per week)",
        "Complex calculated measure using MIN/MAX date aggregation",
        {
            "measures": ["transaction_lines.units_per_week"],
            "dimensions": ["transaction_lines.category"],
            "timeDimensions": [{
                "dimension": "transaction_lines.transaction_date",
                "granularity": "month",
                "dateRange": ["2024-11-01", "2025-10-31"]
            }]
        }
    )

    # Test 4: RET004 - Return Rate Components
    tester.test_metric(
        "RET004",
        "Return Rate Components",
        "Customer credits vs revenue transactions (transaction level)",
        {
            "measures": ["transactions.customer_credits_aligned", "transactions.revenue_transaction_count_aligned"],
            "dimensions": ["transactions.customer_type"],
            "timeDimensions": [{
                "dimension": "transactions.trandate",
                "granularity": "month",
                "dateRange": ["2024-11-01", "2025-10-31"]
            }]
        }
    )

    # Test 5: RET005 - Return Rate % (line-level)
    tester.test_metric(
        "RET005",
        "Return Rate % (line level)",
        "Calculated return_rate measure (units_returned / total units)",
        {
            "measures": ["transaction_lines.return_rate"],
            "dimensions": ["transaction_lines.category"],
            "timeDimensions": [{
                "dimension": "transaction_lines.transaction_date",
                "granularity": "month",
                "dateRange": ["2024-11-01", "2025-10-31"]
            }]
        }
    )

    # Test 6: FD002 - Fulfillments per Order
    tester.test_metric(
        "FD002",
        "Fulfillments per Order",
        "Calculated measure: fulfillment_count / unique_orders",
        {
            "measures": ["fulfillments.fulfillments_per_order"],
            "dimensions": ["fulfillments.status_name"],
            "timeDimensions": [{
                "dimension": "fulfillments.trandate",
                "granularity": "month",
                "dateRange": ["2024-11-01", "2025-10-31"]
            }]
        }
    )

    # Test 7: MM001 Components - Revenue + GL COGS separately
    tester.test_metric(
        "MM001_COMP",
        "MM001 Components (Revenue + GL COGS)",
        "Test component measures separately to isolate JOIN issue",
        {
            "measures": ["transaction_lines.total_revenue", "transaction_lines.gl_based_cogs"],
            "dimensions": ["transaction_lines.channel_type"],
            "timeDimensions": [{
                "dimension": "transaction_lines.transaction_date",
                "granularity": "month",
                "dateRange": ["2024-11-01", "2025-10-31"]
            }]
        }
    )

    # Test 8: GL COGS Direct from COGS cube
    tester.test_metric(
        "COGS_DIRECT",
        "GL COGS (Direct from COGS cube)",
        "Query COGS cube directly (no JOIN) to test if COGS cube itself has issues",
        {
            "measures": ["transaction_accounting_lines_cogs.gl_cogs"],
            "dimensions": ["transaction_accounting_lines_cogs.category"],
            "timeDimensions": [{
                "dimension": "transaction_accounting_lines_cogs.transaction_date",
                "granularity": "month",
                "dateRange": ["2024-11-01", "2025-10-31"]
            }]
        }
    )

    # Print summary and save results
    tester.print_summary()
    tester.save_results(args.output)

    # Exit with error code if any tests failed
    failed_count = sum(1 for r in tester.results if r['status'] != 'PASSED')
    sys.exit(1 if failed_count > 0 else 0)


if __name__ == '__main__':
    main()
