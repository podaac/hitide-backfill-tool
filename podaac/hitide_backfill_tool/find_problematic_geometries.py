#!/usr/bin/env python3
"""
Query CMR for a collection and find granules that have a global BoundingRectangle
(-180/180 lon, -90/90 lat) and no GPolygons in their UMM-G metadata.
Outputs concept IDs to a text file (one per line).

Splits the time range into monthly chunks and queries them in parallel for speed.

Usage:
  python -m podaac.hitide_backfill_tool.find_problematic_geometries \
    --collection MODIS_A-JPL-L2P-v2019.0

  python -m podaac.hitide_backfill_tool.find_problematic_geometries \
    --collection SWOT_L2_HR_Raster_D \
    --output problematic_granules.txt \
    --workers 10

  # Reuse a backfill .cfg (reads cmr/collection/provider/edl_token/page_size);
  # any CLI arg overrides the config value.
  python -m podaac.hitide_backfill_tool.find_problematic_geometries \
    --config backfill_uat.cfg \
    --collection SWOT_L2_LR_SSH_BASIC_2.0 \
    --output problematic_granules.txt
"""

import argparse
import netrc
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

try:
    from podaac.hitide_backfill_tool.file_util import load_yaml_file
except ModuleNotFoundError:
    # Allow running this file directly (python .../find_problematic_geometries.py)
    # by putting the package root on sys.path.
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from podaac.hitide_backfill_tool.file_util import load_yaml_file

CMR_URLS = {
    "ops": "https://cmr.earthdata.nasa.gov",
    "uat": "https://cmr.uat.earthdata.nasa.gov",
    "sit": "https://cmr.sit.earthdata.nasa.gov",
}

# Earthdata Login (URS) hosts per environment, used to resolve a bearer token
# from .netrc credentials.
URS_URLS = {
    "ops": "https://urs.earthdata.nasa.gov",
    "uat": "https://uat.urs.earthdata.nasa.gov",
    "sit": "https://sit.urs.earthdata.nasa.gov",
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


def get_netrc_credentials(urs_host):
    """Return (username, password) for the URS host from .netrc, or None."""
    try:
        auth = netrc.netrc().authenticators(urs_host)
    except (FileNotFoundError, netrc.NetrcParseError):
        return None
    if not auth:
        return None
    username, _, password = auth
    if not username or not password:
        return None
    return username, password


def get_token_from_netrc(env):
    """Resolve an EDL bearer token from .netrc credentials via the URS tokens API.

    Reuses an existing token if the account has one, otherwise creates a new one.
    Returns the token string, or None if credentials or the token cannot be obtained.
    """
    urs_url = URS_URLS[env]
    urs_host = urs_url.split("//", 1)[1]
    creds = get_netrc_credentials(urs_host)
    if not creds:
        print(
            f"No .netrc credentials found for {urs_host}; proceeding unauthenticated.",
            file=sys.stderr,
        )
        return None

    session = create_session()
    try:
        resp = session.get(f"{urs_url}/api/users/tokens", auth=creds)
        resp.raise_for_status()
        tokens = resp.json()
        if tokens:
            return tokens[0].get("access_token")

        # No existing token; create one.
        resp = session.post(f"{urs_url}/api/users/token", auth=creds)
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Could not obtain EDL token from .netrc: {exc}", file=sys.stderr)
        return None


def resolve_token(args):
    """Resolve a bearer token: --token, then EDL_TOKEN env var, then .netrc."""
    token = args.token or os.environ.get("EDL_TOKEN")
    if token:
        return token
    return get_token_from_netrc(args.env)


def apply_config(args):
    """Fill in unset args from a backfill .cfg (YAML) file, CLI taking precedence.

    Reuses the same config files as the backfill tool. Maps the backfill keys
    `cmr` -> env, `edl_token` -> token, and shares `collection`, `provider`,
    and `page_size`.
    """
    if not args.config:
        return args

    config = load_yaml_file(args.config)

    if args.env is None:
        args.env = config.get("cmr")
    if args.collection is None:
        args.collection = config.get("collection")
    if args.provider is None:
        args.provider = config.get("provider")
    if args.token is None:
        args.token = config.get("edl_token")
    if args.page_size is None:
        args.page_size = config.get("page_size")

    return args


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
        "--config", default=None,
        help="Backfill .cfg file to read cmr/collection/provider/edl_token/page_size from "
             "(CLI args override its values)",
    )
    parser.add_argument(
        "-c", "--collection", default=None, help="Collection short name"
    )
    parser.add_argument(
        "-p", "--provider", default=None, help="CMR provider (default: POCLOUD)"
    )
    parser.add_argument(
        "-e", "--env", default=None, choices=CMR_URLS.keys(),
        help="CMR environment (default: ops)",
    )
    parser.add_argument(
        "-t", "--token", default=None,
        help="EDL Bearer token (default: EDL_TOKEN env var, then .netrc credentials)",
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
        "--page-size", type=int, default=None, help="CMR page size (default: 2000)"
    )

    args = parser.parse_args()
    args = apply_config(args)

    # Fall back to defaults for anything neither the CLI nor the config set.
    if args.env is None:
        args.env = "ops"
    if args.provider is None:
        args.provider = "POCLOUD"
    if args.page_size is None:
        args.page_size = 2000
    if args.env not in CMR_URLS:
        parser.error(f"invalid env/cmr '{args.env}' (choose from {', '.join(CMR_URLS)})")
    if not args.collection:
        parser.error("--collection is required (via CLI or config file)")

    return args


def main():
    """Entry point: detect the temporal range and scan for problematic granules."""
    args = parse_args()
    token = resolve_token(args)
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
