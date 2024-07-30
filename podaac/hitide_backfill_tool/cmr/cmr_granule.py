"""Extract information from CMR umm_json formatted granule metadata."""
from urllib.parse import urlparse
from podaac.hitide_backfill_tool.dmrpp_utils import get_dmrpp_version, parse_version, DmrppState
from podaac.hitide_backfill_tool.args import default_config


class CmrGranule:
    """Extracts information from CMR umm_json formatted granule metadata."""

    # Disable broad-except since many types of error indicate the absense
    #   of data when attempting access (e.g. TypeError, IndexError, KeyError, ...)
    # pylint: disable=broad-except

    # pylint: disable=too-many-instance-attributes
    # pylint: disable-next=too-many-arguments
    def __init__(self,
                 umm_granule,
                 s3=None,
                 footprint_geometries=None,
                 can_use_data_url_for_s3_bucket_info=False,
                 image_processing="on",
                 footprint_processing="on",
                 dmrpp_processing="off",
                 dmrpp_min_version=parse_version(default_config["dmrpp_min_version"])):
        """Create the CmrGranule object from granule and settings."""
        # pylint: disable=C0103

        self.umm_granule = umm_granule
        self.s3 = s3
        self.footprint_geometries = footprint_geometries or ["GPolygons", "Lines"]
        self.can_use_data_url_for_s3_bucket_info = can_use_data_url_for_s3_bucket_info
        self.image_processing = image_processing
        self.footprint_processing = footprint_processing
        self.dmrpp_processing = dmrpp_processing
        self.dmrpp_min_version = dmrpp_min_version

    def has_footprint(self):
        """Returns True if granule has footprint, otherwise False."""
        try:
            granule_geometries = self.umm_granule["umm"]["SpatialExtent"]["HorizontalSpatialDomain"]["Geometry"]  # pylint: disable=line-too-long
            for geometry_name in granule_geometries:
                geometry = granule_geometries[geometry_name]
                if geometry_name in self.footprint_geometries and isinstance(geometry, list) and len(geometry) > 0:  # pylint: disable=line-too-long
                    return True
        except Exception:
            pass
        return False

    def has_footprint_and_bbox(self):
        """Returns True if granule has footprint and bounding rectangle, otherwise False."""
        try:
            granule_geometries = self.umm_granule["umm"]["SpatialExtent"]["HorizontalSpatialDomain"]["Geometry"]  # pylint: disable=line-too-long
            if 'BoundingRectangles' in granule_geometries:
                for geometry_name in granule_geometries:
                    geometry = granule_geometries[geometry_name]
                    if geometry_name in self.footprint_geometries and isinstance(geometry, list) and len(geometry) > 0:  # pylint: disable=line-too-long
                        return True
        except Exception:
            pass
        return False

    def needs_footprint(self):
        """Returns True if granule needs to have a footprint generated, otherwise False."""

        return self.footprint_processing == "force" or (self.footprint_processing == "on" and not self.has_footprint())  # pylint: disable=line-too-long

    def has_image(self):
        """Returns True if the granule has a thumbnail image link, otherwise False."""

        try:
            urls = self.umm_granule["umm"]["RelatedUrls"]
            for url in urls:
                if url["Type"] == "GET RELATED VISUALIZATION":
                    return True
        except Exception:
            pass
        return False

    def has_opendap_url(self):
        """Returns True if the granule has an OpenDAP URL link, otherwise False."""

        try:
            url = self.opendap_url()

            if url:
                return True
        except Exception:
            pass

        return False

    def get_dmrpp_state(self, s3_dmrpp_url):
        """Returns DmrppState of the granule's dmrpp file.  It downloads the dmrpp file from the
        S3 bucket and checks the version against the dmrpp_min_version.  Returns one of four
        different possible states."""

        state = DmrppState.MISSING_VERSION

        try:
            dmrpp_version = get_dmrpp_version(self.s3, s3_dmrpp_url)

            if dmrpp_version != "":
                version = parse_version(dmrpp_version)
                if version < self.dmrpp_min_version:
                    state = DmrppState.OLDER_VERSION
                elif version > self.dmrpp_min_version:
                    state = DmrppState.NEWER_VERSION
                else:
                    state = DmrppState.MATCHED_VERSION
        except Exception:
            pass
        return state

    def needs_image(self):
        """Returns True if the granule needs to have thumbnail images generated, otherwise False."""

        return self.image_processing == "force" or (self.image_processing == "on" and not self.has_image())  # pylint: disable=line-too-long

    def native_id(self):
        """Returns the native_id."""

        return self.umm_granule["meta"]["native-id"]

    def concept_id(self):
        """Returns the concept_id."""

        return self.umm_granule["meta"]["concept-id"]

    def s3_url(self):
        """Returns a link to the granule in S3 if provided, otherwise returns None."""

        try:
            urls = self.umm_granule["umm"]["RelatedUrls"]
            for url in urls:
                if url["Type"] == "GET DATA VIA DIRECT ACCESS" and "s3://" in url["URL"]:
                    return url["URL"]
        except Exception:
            pass
        return None

    def opendap_url(self):
        """Returns an OpenDAP link to the granule if provided, otherwise returns None."""

        try:
            urls = self.umm_granule["umm"]["RelatedUrls"]
            for url in urls:
                if "Subtype" in url and url["Subtype"] == "OPENDAP DATA" and "opendap" in \
                        url["URL"]:
                    return url["URL"]
        except Exception:
            pass
        return None

    def start_date(self):
        """Returns the start_date if provided, otherwise returns None."""

        try:
            return self.umm_granule["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
        except Exception:
            return None

    def end_date(self):
        """Returns the end_date if provided, otherwise returns None."""

        try:
            return self.umm_granule["umm"]["TemporalExtent"]["RangeDateTime"]["EndingDateTime"]
        except Exception:
            return None

    def raw(self):
        """Returns the raw umm_json formatted granule metadata."""

        return self.umm_granule

    def data_url(self):
        """Returns the http link to the granule file if provided, otherwise returns None."""

        try:
            urls = self.umm_granule["umm"]["RelatedUrls"]
            for url in urls:
                if url["Type"] == "GET DATA" and "https://" in url["URL"]:
                    return url["URL"]
        except Exception:
            pass
        return None

    def size(self, filename):
        """Returns the size of the data granule"""
        umm = self.umm_granule.get('umm', {})
        data_granule = umm.get('DataGranule', {})
        files = data_granule.get('ArchiveAndDistributionInformation', [])
        file = next((file for file in files if file.get('Name') == filename), None)
        return file.get('SizeInBytes', 0) if file else 0

    def s3_bucket_info(self):
        """Returns the S3 bucket name, key, and the filename for the granule.

        Example return value for granule with s3://bucket-name/directory1/directory2/filename.nc
        {
            "bucket": "bucket-name",
            "key": "directory1/directory2/filename.nc",
            "filename": "filename.nc"
        }

        This information will come from the S3 bucket link if provided, or from
        the data url if 'can_use_data_url_for_s3_bucket_info' == True.
        Otherwise returns None.
        """
        try:
            if self.s3_url():
                # Assume s3 url with structure ->
                # s3://bucket-name/directory1[/directory2]/filename.nc
                parsed = urlparse(self.s3_url(), allow_fragments=False)
                return {
                    "bucket": parsed.netloc,
                    "key": parsed.path.lstrip('/'),
                    "filename": parsed.path.split('/')[-1]
                }

            if self.can_use_data_url_for_s3_bucket_info and self.data_url():
                # Assume data url with structure ->
                # https://hostname.com/bucket-name/directory1[/directory2]/filename.nc
                path = self.data_url().partition("//")[2].partition('/')[2]
                bucket, _, key = path.partition('/')
                filename = key.rpartition('/')[2]

                return {
                    "bucket": bucket,
                    "key": key,
                    "filename": filename
                }
        except Exception:
            pass
        return None
