from podaac.hitide_backfill_tool.cmr.search import GranuleSearch


def test_granule_search_with_multiple_pages():
  search = GranuleSearch(
    base_url="https://cmr.uat.earthdata.nasa.gov",
    collection_short_name="MODIS_A-JPL-L2P-v2019.0",
    provider="pocloud",
    page_size=3,
    page_limit=2
  )

  count = 0
  while not search.is_done():
    search.get_next_page()
    for granule in search.granules():
      count += 1

  assert count == 6


def test_granule_search_generator():
  search = GranuleSearch(
    base_url="https://cmr.uat.earthdata.nasa.gov",
    collection_short_name="MODIS_A-JPL-L2P-v2019.0",
    provider="pocloud",
    page_size=3,
    page_limit=2
  )
  
  granule_count = 0
  for granule in search.granule_generator():
    granule_count += 1
    assert type(granule.native_id()) == str

  assert granule_count == 6

