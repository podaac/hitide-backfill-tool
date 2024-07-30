
from podaac.hitide_backfill_tool.cmr.cmr_granule import CmrGranule
from podaac.hitide_backfill_tool.file_util import load_json_file

sample_granules = load_json_file(
    'resources/cmr_search_test_granules.json', relative_to=__file__)


def test_granule_has_footprint____has_BoundingRect___default_behavior():
    granule = CmrGranule(sample_granules["granule_with_bounding_rectangle"])
    assert not granule.has_footprint()


def test_granule_has_footprint____has_BoundingRect___BoundingRectangles_acceptable():
    granule = CmrGranule(
        sample_granules["granule_with_bounding_rectangle_and_gpolygon"], footprint_geometries=["BoundingRectangles"])
    assert granule.has_footprint()


def test_granule_has_opendap_url____has_OpenDapURL_acceptable():
    granule = CmrGranule(
        sample_granules["granule_that_has_opendap_url"])
    assert granule.has_opendap_url()


def test_granule_missing_opendap_url____missing_OpenDapURL():
    granule = CmrGranule(
        sample_granules["granule_with_bounding_rectangle_and_gpolygon"])
    assert not granule.has_opendap_url()


def test_granule_has_footprint____has_footprint():
    granule = CmrGranule(
        sample_granules["granule_with_bounding_rectangle_and_gpolygon"])
    assert granule.has_footprint()


def test_granule_has_image___has_image():
    granule = CmrGranule(
        sample_granules["granule_with_related_urls_and_one_is_image"])
    assert granule.has_image()


def test_granule_has_image___has_no_image():
    granule = CmrGranule(
        sample_granules["granule_with_related_urls_but_no_image"])
    assert not granule.has_image()


def test_functions_return_false_when_data_is_missing_from_granule():
    granule = CmrGranule({})
    assert not granule.has_footprint()
    assert not granule.has_image()


##### S3 Bucket Info Tests #####

def test_gets_s3_bucket_info__from_s3_url__with_one_directory():
    # The sample granule has an s3 url of s3://bucket-name/directory1/filename.nc
    granule = CmrGranule(sample_granules["granule_that_has_s3_url_with_one_directory"])
    bucket_info = granule.s3_bucket_info()

    assert bucket_info["bucket"] == "bucket-name"
    assert bucket_info["key"] == "directory1/filename.nc"
    assert bucket_info["filename"] == "filename.nc"


def test_gets_s3_bucket_info__from_s3_url__with_2_directories():
    # The sample granule has an s3 url of s3://bucket-name/directory1/directory2/filename.nc
    granule = CmrGranule(sample_granules["granule_that_has_s3_url_with_two_directories"])
    bucket_info = granule.s3_bucket_info()

    assert bucket_info["bucket"] == "bucket-name"
    assert bucket_info["key"] == "directory1/directory2/filename.nc"
    assert bucket_info["filename"] == "filename.nc"


def test_gets_s3_bucket_info__from_data_url__with_one_directory():
    # The sample granule has a data url of https://server-name.com/bucket-name/directory1/filename.nc
    granule = CmrGranule(sample_granules["granule_that_has_data_url_with_one_directory"], can_use_data_url_for_s3_bucket_info=True)
    bucket_info = granule.s3_bucket_info()

    assert bucket_info["bucket"] == "bucket-name"
    assert bucket_info["key"] == "directory1/filename.nc"
    assert bucket_info["filename"] == "filename.nc"


def test_gets_s3_bucket_info__from_data_url__with_two_directories():
    # The sample granule has a data url of https://server-name.com/bucket-name/directory1/directory2/filename.nc
    granule = CmrGranule(sample_granules["granule_that_has_data_url_with_two_directories"], can_use_data_url_for_s3_bucket_info=True)
    bucket_info = granule.s3_bucket_info()

    assert bucket_info["bucket"] == "bucket-name"
    assert bucket_info["key"] == "directory1/directory2/filename.nc"
    assert bucket_info["filename"] == "filename.nc"
