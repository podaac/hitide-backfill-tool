# find-swot-global-bounds

Queries CMR for a given collection and identifies granules that have a global BoundingRectangle (`-180/180` longitude, `-90/90` latitude) but no GPolygons in their UMM-G metadata. These granules are "problematic" because the global bounding box is a placeholder that does not reflect the actual spatial coverage of the data, and the absence of GPolygons means there is no precise footprint to fall back on.

The script automatically detects the full temporal range of the collection and splits it into monthly chunks, querying them in parallel for speed.

## Installation

The command is included as a console entry point in the backfill tool package. Once the package is installed, `find-swot-global-bounds` is available on your PATH:

```bash
pip install .
# or
poetry install
```

## Usage

```bash
find-swot-global-bounds \
  --collection <SHORT_NAME> \
  [--provider POCLOUD] \
  [--env ops|uat|sit] \
  [--token <EDL_BEARER_TOKEN>] \
  [--output <OUTPUT_FILE>] \
  [--workers 5] \
  [--page-size 2000]
```

## Arguments

| Argument | Default | Description |
|---|---|---|
| `-c`, `--collection` | *(required)* | Collection short name (e.g. `SWOT_L2_HR_Raster_D`) |
| `-p`, `--provider` | `POCLOUD` | CMR provider ID |
| `-e`, `--env` | `ops` | CMR environment: `ops`, `uat`, or `sit` |
| `-t`, `--token` | `None` | EDL Bearer token for authenticated searches |
| `-o`, `--output` | stdout | Path to output file |
| `-w`, `--workers` | `5` | Number of parallel workers |
| `--page-size` | `2000` | CMR page size per request |

## Examples

Write problematic granule concept IDs to a file:

```bash
find-swot-global-bounds \
  --collection SWOT_L2_HR_Raster_D \
  --output problematic_granules.txt \
  --workers 10
```

Print to stdout (pipe or redirect as needed):

```bash
find-swot-global-bounds \
  --collection MODIS_A-JPL-L2P-v2019.0
```

Query a non-production environment with a token:

```bash
find-swot-global-bounds \
  --collection SWOT_L2_HR_Raster_D \
  --env uat \
  --token "$EDL_TOKEN" \
  --output problematic_granules_uat.txt
```

## Output Format

The script writes one CMR granule concept ID per line:

```
G3847429803-POCLOUD
G3856012575-POCLOUD
G3849846979-POCLOUD
```

Progress and summary statistics are printed to stderr so they don't interfere with the output when writing to stdout.

## Using the Output with the Backfill Tool

The output file is designed to be passed directly to the backfill tool's `--granule-list-file` argument. This lets you target only the problematic granules for footprint regeneration instead of reprocessing an entire collection.

The file can contain either granule concept IDs (e.g. `G3847429803-POCLOUD`) or GranuleURs, one per line. The script outputs concept IDs.

### Example: Regenerate footprints for problematic granules

```bash
# Step 1: Find problematic granules
find-swot-global-bounds \
  --collection SWOT_L2_HR_Raster_D \
  --output problematic_granules.txt

# Step 2: Run the backfill tool against only those granules
backfill \
  --collection SWOT_L2_HR_Raster_D \
  --cumulus swot-ops \
  --footprint force \
  --granule-list-file problematic_granules.txt
```

Use `--preview` to do a dry run first:

```bash
backfill \
  --collection SWOT_L2_HR_Raster_D \
  --cumulus swot-ops \
  --footprint force \
  --granule-list-file problematic_granules.txt \
  --preview
```

When `--granule-list-file` is provided, the backfill tool skips its normal CMR date-range search and processes only the listed granules. This means `--start-date`, `--end-date`, and `--cycles` are ignored.
