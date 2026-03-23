#!/usr/bin/env python3
"""
Validate Cube pre-aggregation refresh policy.

Policy enforced:
- Every pre-aggregation must define refresh_key.every = the configured default,
  except for explicitly allowed freshness-critical overrides.
- Non-partitioned pre-aggregations must not define:
  - refresh_key.incremental
  - refresh_key.update_window
- Every partitioned pre-aggregation must define:
  - build_range_start as an object (not scalar),
  - no build_range_end, except explicit dynamic source-max exceptions,
  - refresh_key.incremental = true,
  - refresh_key.update_window = 28 day(s).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PRE_START_RE = re.compile(r"^(\s*)pre_aggregations:\s*$")
ITEM_RE = re.compile(r"^(\s*)-\s+name:\s*([A-Za-z0-9_]+)\s*$")
KEY_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")
ALLOWED_DYNAMIC_BUILD_RANGE_END_PREAGGS = {
    # item_receipts.trandate is mixed-format source data. This dynamic MAX(...) end
    # prevents Cube from truncating the newest partition while still avoiding a fixed cap.
    "item_receipts.receipt_analysis",
    # purchase_orders and vendor_spend showed the same truncation pattern in production:
    # source rows were present in March 2026 while Cube materialization stopped in older
    # month partitions. These dynamic source-max ends keep partition coverage aligned.
    "purchase_orders.po_totals",
    "purchase_orders.po_summary",
    "vendor_spend.vendor_spend_summary",
    "vendor_spend.vendor_spend_monthly",
}
REFRESH_EVERY_OVERRIDES = {
    # These pre-aggregations back the nightly freshness validator and must
    # invalidate frequently enough to reflect the latest warehouse sync.
    "transaction_lines.sales_summary_fast": "1 hour",
    "transaction_lines.sales_product_detail": "1 hour",
    "transaction_lines.product_category_analysis": "1 hour",
    "transaction_lines.customer_geography": "1 hour",
    "transaction_lines.size_geography": "1 hour",
    "transaction_lines.discount_analysis": "1 hour",
    "purchase_orders.po_totals": "1 hour",
    "purchase_orders.po_summary": "1 hour",
    "item_receipts.receipt_analysis": "1 hour",
    "vendor_spend.vendor_spend_summary": "1 hour",
    "product_sales_detail.product_daily_sales": "1 hour",
    "product_sales_detail.product_context_monthly": "1 hour",
    "product_sales_detail.product_daily_sales_sales_only": "1 hour",
    "product_sales_detail.product_context_monthly_sales_only": "1 hour",
}


@dataclass
class PreAggConfig:
    file_path: Path
    cube_name: str
    name: str
    line: int
    attrs: Dict[str, str]
    attr_lines: Dict[str, int]
    refresh: Dict[str, str]
    refresh_lines: Dict[str, int]

    @property
    def full_name(self) -> str:
        return f"{self.cube_name}.{self.name}"

    @property
    def partitioned(self) -> bool:
        return "partition_granularity" in self.attrs


def parse_interval_days(raw: str) -> Optional[int]:
    value = raw.strip().lower()
    m = re.match(r"^(\d+)\s*(day|days)$", value)
    if not m:
        return None
    return int(m.group(1))


def parse_interval_minutes(raw: str) -> Optional[int]:
    value = raw.strip().lower()
    m = re.match(r"^(\d+)\s*(hour|hours|day|days)$", value)
    if not m:
        return None
    quantity = int(m.group(1))
    unit = m.group(2)
    if unit.startswith("hour"):
        return quantity * 60
    return quantity * 24 * 60


def discover_preaggs(model_dir: Path) -> List[PreAggConfig]:
    if not model_dir.exists() or not model_dir.is_dir():
        raise SystemExit(f"Model directory not found: {model_dir}")

    out: List[PreAggConfig] = []
    for cube_file in sorted(model_dir.glob("*.yml")):
        cube_name = cube_file.stem
        lines = cube_file.read_text(encoding="utf-8").splitlines()
        in_pre = False
        pre_indent = -1
        i = 0
        while i < len(lines):
            line = lines[i]
            m_pre = PRE_START_RE.match(line)
            if m_pre:
                in_pre = True
                pre_indent = len(m_pre.group(1))
                i += 1
                continue

            if in_pre:
                indent = len(line) - len(line.lstrip(" "))
                if line.strip() and indent <= pre_indent and not line.lstrip().startswith("#"):
                    in_pre = False
                    pre_indent = -1
                    continue

                m_item = ITEM_RE.match(line)
                if m_item and len(m_item.group(1)) > pre_indent:
                    item_indent = len(m_item.group(1))
                    item_name = m_item.group(2)
                    item_line = i + 1
                    key_indent = item_indent + 2

                    attrs: Dict[str, str] = {}
                    attr_lines: Dict[str, int] = {}
                    refresh: Dict[str, str] = {}
                    refresh_lines: Dict[str, int] = {}

                    i += 1
                    while i < len(lines):
                        sub = lines[i]
                        if sub.strip():
                            sub_indent = len(sub) - len(sub.lstrip(" "))
                            if sub_indent <= pre_indent and not sub.lstrip().startswith("#"):
                                break
                            m_next = ITEM_RE.match(sub)
                            if m_next and len(m_next.group(1)) == item_indent:
                                break
                            m_key = KEY_RE.match(sub)
                            if m_key:
                                ind = len(m_key.group(1))
                                key = m_key.group(2)
                                val = m_key.group(3).strip()
                                if ind == key_indent:
                                    attrs[key] = val
                                    attr_lines[key] = i + 1
                                elif (
                                    attrs.get("refresh_key", "__missing__") == ""
                                    and ind == key_indent + 2
                                ):
                                    refresh[key] = val
                                    refresh_lines[key] = i + 1
                        i += 1

                    out.append(
                        PreAggConfig(
                            file_path=cube_file,
                            cube_name=cube_name,
                            name=item_name,
                            line=item_line,
                            attrs=attrs,
                            attr_lines=attr_lines,
                            refresh=refresh,
                            refresh_lines=refresh_lines,
                        )
                    )
                    continue

            i += 1

    if not out:
        raise SystemExit(f"No pre-aggregations found under: {model_dir}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Cube pre-aggregation refresh policy.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model-dir",
        default=str(Path(__file__).resolve().parent / "model" / "cubes"),
        help="Directory containing cube YAML files.",
    )
    parser.add_argument(
        "--required-refresh-every",
        default="365 days",
        help="Required refresh_key.every value for all pre-aggregations.",
    )
    parser.add_argument(
        "--required-update-window-days",
        type=int,
        default=28,
        help="Required update window in days for partitioned pre-aggregations.",
    )
    args = parser.parse_args()

    required_every_minutes = parse_interval_minutes(str(args.required_refresh_every))
    if required_every_minutes is None:
        raise SystemExit(
            f"Invalid --required-refresh-every: {args.required_refresh_every!r}. "
            "Use format like '1 hour', '1 hours', '365 day' or '365 days'."
        )

    preaggs = discover_preaggs(Path(args.model_dir).resolve())
    violations: List[str] = []

    for pa in preaggs:
        every_raw = pa.refresh.get("every", "")
        every_minutes = parse_interval_minutes(every_raw)
        expected_every_raw = REFRESH_EVERY_OVERRIDES.get(pa.full_name, str(args.required_refresh_every))
        expected_every_minutes = parse_interval_minutes(expected_every_raw)
        if expected_every_minutes is None:
            raise SystemExit(
                f"Internal policy error: invalid expected refresh interval {expected_every_raw!r} "
                f"for {pa.full_name}"
            )
        if every_minutes != expected_every_minutes:
            line = pa.refresh_lines.get("every", pa.line)
            violations.append(
                f"{pa.file_path}:{line} {pa.full_name}: refresh_key.every={every_raw!r} "
                f"(expected {expected_every_raw!r})"
            )

        if not pa.partitioned:
            if "incremental" in pa.refresh:
                line = pa.refresh_lines.get("incremental", pa.line)
                violations.append(
                    f"{pa.file_path}:{line} {pa.full_name}: non-partitioned pre-aggregations must not set "
                    "refresh_key.incremental"
                )
            if "update_window" in pa.refresh:
                line = pa.refresh_lines.get("update_window", pa.line)
                violations.append(
                    f"{pa.file_path}:{line} {pa.full_name}: non-partitioned pre-aggregations must not set "
                    "refresh_key.update_window"
                )
            continue

        if "build_range_start" not in pa.attrs:
            violations.append(
                f"{pa.file_path}:{pa.line} {pa.full_name}: missing build_range_start"
            )
        elif pa.attrs.get("build_range_start", "__missing__") != "":
            line = pa.attr_lines.get("build_range_start", pa.line)
            violations.append(
                f"{pa.file_path}:{line} {pa.full_name}: build_range_start must be object, "
                f"found scalar {pa.attrs.get('build_range_start')!r}"
            )

        if "build_range_end" in pa.attrs and pa.full_name not in ALLOWED_DYNAMIC_BUILD_RANGE_END_PREAGGS:
            line = pa.attr_lines.get("build_range_end", pa.line)
            violations.append(
                f"{pa.file_path}:{line} {pa.full_name}: build_range_end must not be set"
            )

        incremental = pa.refresh.get("incremental", "").strip().lower()
        if incremental != "true":
            line = pa.refresh_lines.get("incremental", pa.line)
            violations.append(
                f"{pa.file_path}:{line} {pa.full_name}: refresh_key.incremental={pa.refresh.get('incremental', '')!r} "
                "expected 'true'"
            )

        update_window_raw = pa.refresh.get("update_window", "")
        update_window_days = parse_interval_days(update_window_raw)
        if update_window_days != args.required_update_window_days:
            line = pa.refresh_lines.get("update_window", pa.line)
            violations.append(
                f"{pa.file_path}:{line} {pa.full_name}: refresh_key.update_window={update_window_raw!r} "
                f"(expected {args.required_update_window_days} day(s))"
            )

    partitioned_count = sum(1 for p in preaggs if p.partitioned)
    print(
        f"Checked {len(preaggs)} pre-aggregations "
        f"({partitioned_count} partitioned) in {Path(args.model_dir).resolve()}."
    )

    if violations:
        print("Policy violations:")
        for row in violations:
            print(f"- {row}")
        return 1

    print("Policy check passed with zero violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
