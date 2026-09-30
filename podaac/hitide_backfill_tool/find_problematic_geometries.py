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
import os
import sys
import threading
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dateutil.relativedelta import relativedelta
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CMR_URLS = {
    "ops": "https://cmr.earthdata.nasa.gov",
    "uat": "https://cmr.uat.earthdata.nasa.gov",
    "sit": "https://cmr.sit.earthdata.nasa.gov",
}

# Connection/query parameters shared across CMR requests.
CmrQuery = namedtuple("CmrQuery", ["base_url", "collection", "provider", "token", "page_size"])

print_lock = threading.Lock()


def create_session():
    """Build a requests Session with connection retries."""
    retry = Retry(connect=5, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session = Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def build_headers(token):
    """Build request headers, adding a Bearer token when provided."""
    return {"Authorization": f"Bearer {token}"} if token else {}


def is_global_bbox(bbox):
    """Check if a BoundingRectangle covers the entire globe."""
    return (
        bbox.get("WestBoundingCoordinate") == -180
        and bbox.get("EastBoundingCoordinate") == 180
        and bbox.get("NorthBoundingCoordinate") == 90
        and bbox.get("SouthBoundingCoordinate") == -90
    )


def is_problematic(item):
    """Return the concept ID if the granule has a global bbox and no GPolygons, else None."""
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


def extract_temporal_value(item):
    """Get a granule's start time, supporting both RangeDateTime and SingleDateTime."""
    temporal = item["umm"]["TemporalExtent"]
    if "RangeDateTime" in temporal:
        return temporal["RangeDateTime"]["BeginningDateTime"]
    return temporal["SingleDateTime"]


def get_collection_temporal_range(cfg):
    """Get the earliest and latest granule dates for the collection."""
    session = create_session()
    headers = build_headers(cfg.token)
    base = (
        f"{cfg.base_url}/search/granules.umm_json"
        f"?provider={cfg.provider}&short_name={cfg.collection}&page_size=1"
    )

    resp = session.get(f"{base}&sort_key[]=start_date", headers=headers)
    resp.raise_for_status()
    body = resp.json()
    total_hits = body.get("hits", 0)
    if total_hits == 0:
        return None, None, 0
    start = extract_temporal_value(body["items"][0])

    resp = session.get(f"{base}&sort_key[]=-start_date", headers=headers)
    resp.raise_for_status()
    end = extract_temporal_value(resp.json()["items"][0])

    return start, end, total_hits


def generate_monthly_ranges(start_str, end_str):
    """Split a time range into monthly chunks."""
    start = datetime.fromisoformat(start_str.replace("Z", "+00:00")).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
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


def iter_granules(cfg, start, end):
    """Yield all granule items in a temporal chunk, paging via cmr-search-after."""
    session = create_session()
    url = (
        f"{cfg.base_url}/search/granules.umm_json"
        f"?provider={cfg.provider}"
        f"&short_name={cfg.collection}"
        f"&page_size={cfg.page_size}"
        f"&sort_key[]=start_date"
        f"&temporal={start},{end}"
    )
    headers = build_headers(cfg.token)

    search_after = None
    while True:
        req_headers = dict(headers)
        if search_after:
            req_headers["cmr-search-after"] = search_after

        response = session.get(url, headers=req_headers)
        response.raise_for_status()

        items = response.json().get("items", [])
        if not items:
            break
        yield from items

        search_after = response.headers.get("cmr-search-after")
        if not search_after:
            break


def search_chunk(cfg, start, end):
    """Search a single temporal chunk and return (scanned IDs, problematic IDs)."""
    scanned_ids = []
    problematic_ids = []
    for item in iter_granules(cfg, start, end):
        scanned_ids.append(item.get("meta", {}).get("concept-id"))
        concept_id = is_problematic(item)
        if concept_id:
            problematic_ids.append(concept_id)
    return scanned_ids, problematic_ids


def process_chunks(cfg, monthly_ranges, workers, out_file):
    """Search all chunks in parallel, writing deduplicated problematic IDs.

    Monthly chunks share boundaries and CMR temporal matches are inclusive, so a
    granule at (or spanning) a boundary can appear in two chunks. Deduplicate by
    concept ID before writing and counting.
    """
    scanned_ids = set()
    problematic_written = set()
    completed = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(search_chunk, cfg, start, end): start
            for start, end in monthly_ranges
        }

        for future in as_completed(futures):
            start = futures[future]
            chunk_scanned_ids, chunk_problematic_ids = future.result()
            scanned_ids.update(chunk_scanned_ids)
            completed += 1

            new_problematic = 0
            for cid in chunk_problematic_ids:
                if cid not in problematic_written:
                    problematic_written.add(cid)
                    out_file.write(cid + "\n")
                    new_problematic += 1

            with print_lock:
                print(
                    f"  [{completed}/{len(monthly_ranges)}] {start[:7]}: "
                    f"{len(chunk_scanned_ids)} scanned, {new_problematic} problematic",
                    file=sys.stderr,
                )

    return len(scanned_ids), len(problematic_written)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Find granules that have BoundingRectangles but no GPolygons"
    )
    parser.add_argument(
        "-c", "--collection", required=True, help="Collection short name"
    )
    parser.add_argument(
        "-p", "--provider", default="POCLOUD", help="CMR provider (default: POCLOUD)"
    )
    parser.add_argument(
        "-e", "--env", default="ops", choices=CMR_URLS.keys(),
        help="CMR environment (default: ops)",
    )
    parser.add_argument(
        "-t", "--token", default=None,
        help="EDL Bearer token (default: reads EDL_TOKEN env var)",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output text file path (default: stdout)",
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=5,
        help="Number of parallel workers (default: 5)",
    )
    parser.add_argument(
        "--page-size", type=int, default=2000, help="CMR page size (default: 2000)"
    )
    return parser.parse_args()


def main():
    """Entry point: detect the temporal range and scan for problematic granules."""
    args = parse_args()
    token = args.token or os.environ.get("EDL_TOKEN")
    cfg = CmrQuery(CMR_URLS[args.env], args.collection, args.provider, token, args.page_size)

    print(f"Querying CMR at {cfg.base_url}", file=sys.stderr)
    print(f"Collection: {cfg.collection}  Provider: {cfg.provider}", file=sys.stderr)
    print("Detecting temporal range...", file=sys.stderr)

    start_str, end_str, total_hits = get_collection_temporal_range(cfg)
    if total_hits == 0:
        print("No granules found in collection.", file=sys.stderr)
        return

    print(f"Total granules in collection: {total_hits}", file=sys.stderr)
    print(f"Temporal range: {start_str} to {end_str}", file=sys.stderr)

    monthly_ranges = generate_monthly_ranges(start_str, end_str)
    print(
        f"Split into {len(monthly_ranges)} monthly chunks, using {args.workers} workers\n",
        file=sys.stderr,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as out_file:
            total_scanned, total_problematic = process_chunks(
                cfg, monthly_ranges, args.workers, out_file
            )
    else:
        total_scanned, total_problematic = process_chunks(
            cfg, monthly_ranges, args.workers, sys.stdout
        )

    print(f"\n{'='*50}", file=sys.stderr)
    print("SUMMARY", file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)
    print(f"Total granules scanned:              {total_scanned}", file=sys.stderr)
    print(f"Global bbox without GPolygons:        {total_problematic}", file=sys.stderr)
    clean = total_scanned - total_problematic
    print(f"Clean granules:                      {clean}", file=sys.stderr)

    if args.output:
        print(f"\nResults written to: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
