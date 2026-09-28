#!/usr/bin/env python3
"""
Query CMR for a collection and find granules that have a global BoundingRectangle
(-180/180 lon, -90/90 lat) and no GPolygons in their UMM-G metadata.
Outputs concept IDs to a text file (one per line).

Splits the time range into monthly chunks and queries them in parallel for speed.

Usage:
  python scripts/find_problematic_geometries.py \
    --collection MODIS_A-JPL-L2P-v2019.0

  python scripts/find_problematic_geometries.py \
    --collection SWOT_L2_HR_Raster_D \
    --output problematic_granules.txt \
    --workers 10
"""

import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CMR_URLS = {
    "ops": "https://cmr.earthdata.nasa.gov",
    "uat": "https://cmr.uat.earthdata.nasa.gov",
    "sit": "https://cmr.sit.earthdata.nasa.gov",
}


def create_session():
    retry = Retry(connect=5, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session = Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def is_global_bbox(bbox):
    """Check if a BoundingRectangle covers the entire globe."""
    return (
        bbox.get("WestBoundingCoordinate") == -180
        and bbox.get("EastBoundingCoordinate") == 180
        and bbox.get("NorthBoundingCoordinate") == 90
        and bbox.get("SouthBoundingCoordinate") == -90
    )


def is_problematic(item):
    """Return the concept ID if the granule has a global BoundingRectangle and no GPolygons, else None."""
    geometry = (
        item.get("umm", {})
        .get("SpatialExtent", {})
        .get("HorizontalSpatialDomain", {})
        .get("Geometry", {})
    )

    bounding_rects = geometry.get("BoundingRectangles", [])
    gpolygons = geometry.get("GPolygons", [])

    has_global = any(is_global_bbox(br) for br in bounding_rects)
    has_gpolygons = len(gpolygons) > 0

    if has_global and not has_gpolygons:
        return item.get("meta", {}).get("concept-id")
    return None


def get_collection_temporal_range(session, base_url, collection, provider, token=None):
    """Get the earliest and latest granule dates for the collection."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    base_params = f"?provider={provider}&short_name={collection}&page_size=1"

    first_url = f"{base_url}/search/granules.umm_json{base_params}&sort_key[]=start_date"
    resp = session.get(first_url, headers=headers)
    resp.raise_for_status()
    body = resp.json()
    total_hits = body.get("hits", 0)
    if total_hits == 0:
        return None, None, 0
    first_item = body["items"][0]
    start = first_item["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]

    last_url = f"{base_url}/search/granules.umm_json{base_params}&sort_key[]=-start_date"
    resp = session.get(last_url, headers=headers)
    resp.raise_for_status()
    last_item = resp.json()["items"][0]
    end = last_item["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]

    return start, end, total_hits


def generate_monthly_ranges(start_str, end_str):
    """Split a time range into monthly chunks."""
    start = datetime.fromisoformat(start_str.replace("Z", "+00:00")).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

    ranges = []
    current = start
    while current <= end:
        next_month = current + relativedelta(months=1)
        ranges.append((
            current.strftime("%Y-%m-%dT%H:%M:%SZ"),
            next_month.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ))
        current = next_month
    return ranges


def search_chunk(base_url, collection, provider, start, end, token=None, page_size=2000):
    """Search a single temporal chunk and return problematic concept IDs."""
    session = create_session()

    url = (
        f"{base_url}/search/granules.umm_json"
        f"?provider={provider}"
        f"&short_name={collection}"
        f"&page_size={page_size}"
        f"&sort_key[]=start_date"
        f"&temporal={start},{end}"
    )

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    search_after = None
    problematic_ids = []
    scanned = 0

    while True:
        req_headers = dict(headers)
        if search_after:
            req_headers["cmr-search-after"] = search_after

        response = session.get(url, headers=req_headers)
        response.raise_for_status()
        body = response.json()

        items = body.get("items", [])
        if not items:
            break

        for item in items:
            scanned += 1
            concept_id = is_problematic(item)
            if concept_id:
                problematic_ids.append(concept_id)

        search_after = response.headers.get("cmr-search-after")
        if not search_after:
            break

    return scanned, problematic_ids


print_lock = threading.Lock()


def main():
    parser = argparse.ArgumentParser(
        description="Find granules that have BoundingRectangles but no GPolygons"
    )
    parser.add_argument("-c", "--collection", required=True, help="Collection short name")
    parser.add_argument("-p", "--provider", default="POCLOUD", help="CMR provider (default: POCLOUD)")
    parser.add_argument("-e", "--env", default="ops", choices=CMR_URLS.keys(), help="CMR environment (default: ops)")
    parser.add_argument("-t", "--token", default=None, help="EDL Bearer token (default: reads EDL_TOKEN env var)")
    parser.add_argument("-o", "--output", default=None, help="Output text file path (default: stdout)")
    parser.add_argument("-w", "--workers", type=int, default=5, help="Number of parallel workers (default: 5)")
    parser.add_argument("--page-size", type=int, default=2000, help="CMR page size (default: 2000)")
    args = parser.parse_args()

    if not args.token:
        args.token = os.environ.get("EDL_TOKEN")

    base_url = CMR_URLS[args.env]
    session = create_session()

    print(f"Querying CMR at {base_url}", file=sys.stderr)
    print(f"Collection: {args.collection}  Provider: {args.provider}", file=sys.stderr)
    print(f"Detecting temporal range...", file=sys.stderr)

    start_str, end_str, total_hits = get_collection_temporal_range(
        session, base_url, args.collection, args.provider, args.token
    )

    if total_hits == 0:
        print("No granules found in collection.", file=sys.stderr)
        return

    print(f"Total granules in collection: {total_hits}", file=sys.stderr)
    print(f"Temporal range: {start_str} to {end_str}", file=sys.stderr)

    monthly_ranges = generate_monthly_ranges(start_str, end_str)
    print(f"Split into {len(monthly_ranges)} monthly chunks, using {args.workers} workers\n", file=sys.stderr)

    out_file = open(args.output, "w") if args.output else sys.stdout

    total_scanned = 0
    total_problematic = 0
    completed_chunks = 0

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    search_chunk, base_url, args.collection, args.provider,
                    start, end, args.token, args.page_size
                ): (start, end)
                for start, end in monthly_ranges
            }

            for future in as_completed(futures):
                start, end = futures[future]
                scanned, problematic_ids = future.result()
                total_scanned += scanned
                total_problematic += len(problematic_ids)
                completed_chunks += 1

                for cid in problematic_ids:
                    out_file.write(cid + "\n")

                with print_lock:
                    month_label = start[:7]
                    status = f"  [{completed_chunks}/{len(monthly_ranges)}] {month_label}: {scanned} scanned, {len(problematic_ids)} problematic"
                    print(status, file=sys.stderr)
    finally:
        if args.output and out_file:
            out_file.close()

    print(f"\n{'='*50}", file=sys.stderr)
    print(f"SUMMARY", file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)
    print(f"Total granules scanned:              {total_scanned}", file=sys.stderr)
    print(f"Global bbox without GPolygons:        {total_problematic}", file=sys.stderr)
    print(f"Clean granules:                      {total_scanned - total_problematic}", file=sys.stderr)

    if args.output:
        print(f"\nResults written to: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
