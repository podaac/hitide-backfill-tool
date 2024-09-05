"""Create Cumulus CNM message from granule."""

import json


class CnmMessageWriter:
    """Creates a Cumulus CNM message from granule."""

    # pylint: disable=too-many-instance-attributes,too-many-arguments

    def __init__(self,
                 message_config,
                 collection_config,
                 search_start,
                 search_end,
                 provider,
                 cli_execution_id,
                 user):
        """Create the CnmMessageWriter."""

        self.collection_name = collection_config["name"]
        self.collection_version = collection_config["version"]
        self.collection_config = collection_config
        self.provider = provider
        self.search_start = search_start
        self.search_end = search_end
        self.cli_execution_id = cli_execution_id
        self.user = user
        self.create_template(message_config, collection_config)

    def create_template(self, message_config, collection_config):
        """Create a message template from message config file and from a
        cumulus collection config file.
        """

        collection_name = collection_config["name"]

        meta = dict(message_config)
        meta["collection"] = collection_config
        meta["collection"]["dataType"] = collection_name
        meta["collection"]["files"].append({
            "bucket": "ia_public",
            "regex": "^.*\\.png$",
            "type": "metadata"
        })

        self.template = {
            "cumulus_meta": {
                "system_bucket": message_config["buckets"]["internal"]["name"]
            },
            "meta": meta,
        }

    def write(self, granule, needs_footprint, needs_image, needs_dmrpp, skip_cmr_opendap_update):
        """Return a CNM message string given granule information."""

        message = dict(self.template)

        s3_info = granule.s3_bucket_info()
        message["payload"] = {
            "granules": [{
                "cmrConceptId": granule.concept_id(),
                "granuleId": granule.native_id(),
                "dataType": self.collection_name,
                "files": [{
                    "bucket": s3_info["bucket"],
                    "key": s3_info["key"],
                    "fileName": s3_info["filename"],
                    "type": "data",
                    "size": granule.size(s3_info["filename"])
                }]
            }]
        }

        message["forge"] = needs_footprint
        message["tig"] = needs_image
        message["dmrpp"] = needs_dmrpp
        message["skip_cmr_opendap_update"] = skip_cmr_opendap_update

        message["cli_params"] = {
            "uuid": self.cli_execution_id,
            "collection_short_name": self.collection_name,
            "collection_version": self.collection_version,
            "provider": self.provider,
            "cmr_search_start": self.search_start,
            "cmr_search_end": self.search_end,
            "granule_start": granule.start_date(),
            "granule_end": granule.end_date(),
            "username": self.user
        }

        print(message["payload"])
        return json.dumps(message)
