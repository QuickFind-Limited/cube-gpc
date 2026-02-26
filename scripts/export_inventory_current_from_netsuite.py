#!/usr/bin/env python3
"""
Export NetSuite AggregateItemLocation into a CSV suitable for loading into:
  magical-desktop.gpc_prod_native_v1.inventory_current_raw_netsuite

Required env vars:
  NETSUITE_ACCOUNT_ID
  GYM_PLUS_COFFEE_CONSUMER_ID
  GYM_PLUS_COFFEE_CONSUMER_SECRET
  GYM_PLUS_COFFEE_TOKEN_ID
  GYM_PLUS_COFFEE_TOKEN_SECRET
"""

from __future__ import annotations

import csv
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import requests
from requests_oauthlib import OAuth1


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


ACCOUNT_ID = get_required_env("NETSUITE_ACCOUNT_ID")
BASE_URL = f"https://{ACCOUNT_ID.lower().replace('_', '-')}.suitetalk.api.netsuite.com"
AUTH = OAuth1(
    client_key=get_required_env("GYM_PLUS_COFFEE_CONSUMER_ID"),
    client_secret=get_required_env("GYM_PLUS_COFFEE_CONSUMER_SECRET"),
    resource_owner_key=get_required_env("GYM_PLUS_COFFEE_TOKEN_ID"),
    resource_owner_secret=get_required_env("GYM_PLUS_COFFEE_TOKEN_SECRET"),
    signature_method="HMAC-SHA256",
    realm=ACCOUNT_ID,
)
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Prefer": "transient",
}


class SuiteQLClient:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, sql: str, limit: int = 1000, offset: int = 0, retries: int = 6) -> Dict:
        url = f"{BASE_URL}/services/rest/query/v1/suiteql?limit={limit}&offset={offset}"
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                self.calls += 1
                resp = requests.post(
                    url,
                    auth=AUTH,
                    headers=HEADERS,
                    json={"q": sql},
                    timeout=180,
                )
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    time.sleep(min(2**attempt, 20))
                    continue
                raise RuntimeError(f"SuiteQL failed {resp.status_code}: {resp.text[:1200]}")
            except Exception as exc:
                last_err = str(exc)
                time.sleep(min(2**attempt, 20))
        raise RuntimeError(f"SuiteQL failed after retries: {last_err}")


def scalar_int(client: SuiteQLClient, sql: str) -> int:
    data = client.run(sql, limit=1, offset=0)
    items = data.get("items", [])
    if not items:
        return 0
    for key, value in items[0].items():
        if key != "links":
            return int(float(value))
    return 0


def list_locations(client: SuiteQLClient) -> List[int]:
    sql = "SELECT DISTINCT location FROM AggregateItemLocation ORDER BY location"
    locations: List[int] = []
    offset = 0
    while True:
        data = client.run(sql, limit=1000, offset=offset)
        batch = data.get("items", [])
        locations.extend(int(row["location"]) for row in batch)
        if len(batch) < 1000:
            break
        if offset >= 4000:
            raise RuntimeError("Location discovery exceeded SuiteQL 5000 row window")
        offset += 1000
    return locations


def count_range(client: SuiteQLClient, location: int, lo: int, hi: int) -> int:
    sql = (
        "SELECT COUNT(*) AS c FROM AggregateItemLocation "
        f"WHERE location = {location} AND item BETWEEN {lo} AND {hi}"
    )
    return scalar_int(client, sql)


def split_ranges(
    client: SuiteQLClient, location: int, lo: int, hi: int, max_rows: int = 4500
) -> List[Tuple[int, int, int]]:
    ranges: List[Tuple[int, int, int]] = []

    def rec(start: int, end: int) -> None:
        count = count_range(client, location, start, end)
        if count == 0:
            return
        if count <= max_rows or start == end:
            ranges.append((start, end, count))
            return
        mid = (start + end) // 2
        rec(start, mid)
        rec(mid + 1, end)

    rec(lo, hi)
    return ranges


def fetch_rows(client: SuiteQLClient, location: int, lo: int, hi: int) -> List[Dict[str, str]]:
    sql = f"""
    SELECT
      ail.item,
      i.itemid,
      i.displayname,
      i.itemtype,
      ail.location,
      ail.quantityonhand AS quantity_on_hand,
      ail.quantityavailable AS calculated_quantity_available,
      TO_CHAR(ail.lastmodifieddate, 'YYYY-MM-DD') AS last_transaction_date,
      0 AS transaction_count
    FROM AggregateItemLocation ail
    LEFT JOIN item i ON i.id = ail.item
    WHERE ail.location = {location}
      AND ail.item BETWEEN {lo} AND {hi}
    ORDER BY ail.item, ail.location
    """
    rows: List[Dict[str, str]] = []
    offset = 0
    while True:
        data = client.run(sql, limit=1000, offset=offset)
        batch = data.get("items", [])
        rows.extend(batch)
        if len(batch) < 1000:
            break
        if offset >= 4000:
            raise RuntimeError(
                f"Range overflow at location={location}, item={lo}-{hi}, offset={offset}"
            )
        offset += 1000
    return rows


def main() -> int:
    client = SuiteQLClient()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_csv = f"/tmp/netsuite_inventory_aggregateitemlocation_{ts}.csv"

    total_rows = scalar_int(client, "SELECT COUNT(*) AS c FROM AggregateItemLocation")
    min_item = scalar_int(client, "SELECT MIN(item) AS m FROM AggregateItemLocation")
    max_item = scalar_int(client, "SELECT MAX(item) AS m FROM AggregateItemLocation")
    locations = list_locations(client)

    print(f"total_rows={total_rows}")
    print(f"item_range={min_item}..{max_item}")
    print(f"locations={len(locations)}")

    fieldnames = [
        "item",
        "itemid",
        "displayname",
        "itemtype",
        "location",
        "quantity_on_hand",
        "calculated_quantity_available",
        "last_transaction_date",
        "transaction_count",
    ]

    written = 0
    with open(out_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for index, location in enumerate(locations, start=1):
            loc_total = scalar_int(
                client,
                f"SELECT COUNT(*) AS c FROM AggregateItemLocation WHERE location = {location}",
            )
            ranges = split_ranges(client, location, min_item, max_item, max_rows=4500)
            loc_written = 0
            print(
                f"location[{index}/{len(locations)}]={location} "
                f"total={loc_total} ranges={len(ranges)}"
            )
            for r_index, (lo, hi, est) in enumerate(ranges, start=1):
                rows = fetch_rows(client, location, lo, hi)
                for row in rows:
                    writer.writerow({name: row.get(name, "") for name in fieldnames})
                loc_written += len(rows)
                written += len(rows)
                print(
                    f"  range[{r_index}/{len(ranges)}] {lo}-{hi}: "
                    f"rows={len(rows)} est={est} loc_written={loc_written} total_written={written}"
                )

            if loc_written != loc_total:
                raise RuntimeError(
                    f"Location {location} mismatch: wrote {loc_written}, expected {loc_total}"
                )

    if written != total_rows:
        raise RuntimeError(f"Global mismatch: wrote {written}, expected {total_rows}")

    print(f"OUTPUT_FILE={out_csv}")
    print(f"ROWS_WRITTEN={written}")
    print(f"API_CALLS={client.calls}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
