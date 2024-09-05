"""Script for backfilling granule images and footprints"""

# pylint: disable=line-too-long

from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Lock
import logging
import sys
import uuid
import copy
import json
from datetime import datetime, timezone
import requests

from podaac.hitide_backfill_tool.cmr.search import GranuleSearch
from podaac.hitide_backfill_tool.cmr.cmr_granule import CmrGranule
from podaac.hitide_backfill_tool.cmr.helpers import cmr_base_url
from podaac.hitide_backfill_tool.cnm_message_writer import CnmMessageWriter
from podaac.hitide_backfill_tool.sns_message_sender import SnsMessageSender, FileMessageSender
from podaac.hitide_backfill_tool.config import get_collection_config, get_message_config
from podaac.hitide_backfill_tool.args import parse_args
from podaac.hitide_backfill_tool.file_util import make_absolute
from podaac.hitide_backfill_tool.dmrpp_utils import parse_version, DmrppState
from podaac.hitide_backfill_tool.s3_reader import S3Reader


def logger_from_args(args):
    """Return configured logger from parsed cli args."""

    if args.log_file:
        logging.basicConfig(filename=make_absolute(args.log_file))
    logger = logging.getLogger("backfill")
    logger.setLevel(getattr(logging, args.log_level))
    logger.addHandler(logging.StreamHandler(sys.stdout))
    return logger


def object_to_str(obj):
    """Return formatted string, given a python object."""

    vars_dict = vars(obj)
    vars_string = ""
    for key in vars_dict.keys():
        vars_string += f"  {key} -> {vars_dict[key]}\n"
    return vars_string


def safe_log_args(logger, args):
    """Log the parsed cli args object without showing tokens."""

    args_copy = copy.copy(args)
    if args_copy.edl_token:
        args_copy.edl_token = "********"
    if args_copy.launchpad_token:
        args_copy.launchpad_token = "********"
    logger.debug(f"\nCLI args:\n{object_to_str(args_copy)}\n")


def granule_search_from_args(args, logger):
    """Return configured GranuleSearch object from parsed cli args and logger."""

    return GranuleSearch(
        base_url=cmr_base_url(args.cmr),
        collection_short_name=args.collection,
        provider=args.provider,
        start_date=args.start_date,
        end_date=args.end_date,
        page_size=args.page_size,
        page_limit=args.page_limit,
        logger=logger,
        edl_token=args.edl_token,
        launchpad_token=args.launchpad_token,
        cmr_search_after=args.cmr_search_after,
        cycles=args.cycles,
        sort_order=args.sort_order
    )


def message_writer_from_args(args, logger):
    """Return configured message writer from parsed cli args and logger."""

    message_config = get_message_config(args.cumulus, args.default_message_config)
    collection_config = get_collection_config(
        args.cumulus_configurations, args.collection, args.cumulus, logger)
    message_writer = CnmMessageWriter(message_config, collection_config,
                                      args.start_date, args.end_date, args.provider, args.cli_execution_id, args.user)
    return message_writer


def message_senders_from_args(args, logger):
    """Return list of configured message senders from parsed cli args and logger."""

    message_senders = []

    if args.message_file and not args.preview:
        file_message_sender = FileMessageSender(args.message_file)
        message_senders.append(file_message_sender)
    if args.sns_arn and not args.preview:
        message_senders.append(SnsMessageSender(
            topic_arn=args.sns_arn,
            aws_profile=args.aws_profile,
            logger=logger
        ))
    return message_senders


def granule_options_from_args(args):
    """Return kwargs dict will be passed to CmrGranule constructor along with granule umm_json."""

    return {
        "footprint_geometries": args.geometries,
        "footprint_processing": args.footprint,
        "image_processing": args.image,
        "dmrpp_processing": args.dmrpp,
        "dmrpp_min_version": parse_version(args.dmrpp_min_version),
        "can_use_data_url_for_s3_bucket_info": args.use_data_url
    }


class Backfiller:
    """Perform a backfill operation"""

    # Disable broad-except since many types of error indicate the absense
    #   of data when attempting access (e.g. TypeError, IndexError, KeyError, ...)
    # pylint: disable=broad-except

    # pylint: disable=too-many-instance-attributes,too-many-arguments

    def __init__(self, search, message_writer, message_senders, granule_options, logger,
                 message_limit, cli_execution_id, s3, collection):
        # pylint: disable=C0103

        # dependencies
        self.search = search
        self.message_writer = message_writer
        self.message_senders = message_senders
        self.granule_options = granule_options
        self.logger = logger
        self.message_limit = message_limit
        self.cli_execution_id = cli_execution_id
        self.s3 = s3
        self.collection = collection

        # statistics
        self.granules_analyzed = 0
        self.granule_range_start = None
        self.granule_range_end = None
        self.footprints_that_couldnt_be_processed = 0
        self.images_that_couldnt_be_processed = 0
        self.dmrpp_that_couldnt_be_processed = 0
        self.granules_needing_footprint = 0
        self.granules_needing_image = 0
        self.granules_needing_dmrpp = 0
        self.granules_with_footprint_and_bbox = 0
        self.footprint_messages_sent = 0
        self.image_messages_sent = 0
        self.dmrpp_messages_sent = 0
        self.monthly_results = {}
        self.concept_ids_needing_image = []
        self.concept_ids_needing_footprint = []
        self.concept_ids_needing_dmrpp = []

        # dmrpp status
        self.dmrpp_unprocessed = 0
        self.dmrpp_missing_version = 0
        self.dmrpp_update_cmr_opendap = 0
        self.dmrpp_older_version = 0
        self.dmrpp_newer_version = 0

        # forge-tig configuration
        self.forge_tig_configuration = None

        # destination_message used in logging
        destination_message = []
        for message_sender in message_senders:
            destination_message.append(message_sender.name)
        if len(destination_message) == 0:
            destination_message.append('nowhere')
        self.destination_message = f"Messages being sent to {', '.join(destination_message)}"

        # for thread-safe operations
        self.lock = Lock()

    def process_granules(self):
        """Loop through granules (in parallel) from granule-search and call the process_one_granule() method."""

        while self.search.get_next_page():
            print("Processing granules...", end='', flush=True)
            with ThreadPoolExecutor() as executor:
                executor.map(self.process_one_granule, self.search.granules())
            print("done.")
            if self.message_limit_reached():
                self.logger.info("\n**** Message limit reached ****")
                return
            self.log_stats()

    def print_monthly_results_table(self):
        """Function to print out monthly stats"""

        if not self.message_senders:
            print("** NOTE: When in preview mode, the messages sent count may not be accurate since it's only simulating sending messages. ** \n")

        print("Monthly Counts Summary:\n")
        header = f"{'Date':<10} {'Granules':<10} {'Need Image':<12} {'Need Footprint':<16} {'Both FP & BBox':<16} {'Need DMRPP':<12}"

        print(header)

        current_year = None

        separator = "========== ========== ============ ================ ================ ============"

        for date, result in self.monthly_results.items():
            date_obj = datetime.strptime(date, "%Y-%m")
            month_name = date_obj.strftime("%b")

            # Check if the year has changed
            year = date_obj.year
            if year != current_year:
                print(separator)
                current_year = year

            row = f"{date[:4]}-{month_name:<5} {len(result['granules']):<10} {result['needs_image']:<12} {result['needs_footprint']:<16} {result['both_footprint_and_bbox']:<16} {result['needs_dmrpp']:<12}"   # noqa
            print(row)
        print()

    def process_one_granule(self, umm_granule):
        """Create and send messages for one granule.  Thread-safe method using lock."""
        try:
            if self.message_limit_reached():
                return

            granule = CmrGranule(umm_granule, self.s3, **self.granule_options)

            with self.lock:
                if not self.granule_range_start:
                    self.granule_range_start = granule.start_date()
                self.granule_range_end = granule.end_date()

            date = granule.start_date()[:7]
            with self.lock:
                if date not in self.monthly_results:
                    self.monthly_results[date] = {
                        'granules': [copy.deepcopy(granule.umm_granule)],
                        'needs_image': 0,
                        'needs_footprint': 0,
                        'both_footprint_and_bbox': 0,
                        'needs_dmrpp': 0
                    }
                else:
                    self.monthly_results[date]['granules'].append(copy.deepcopy(granule.umm_granule))

            # footprint
            if granule.needs_footprint():
                self.update_footprint(granule)

            # image
            if granule.needs_image():
                self.update_image(granule)

            # both bbox and footprint
            if granule.has_footprint_and_bbox():
                with self.lock:
                    self.granules_with_footprint_and_bbox += 1

                    self.monthly_results[date]['both_footprint_and_bbox'] += 1

            # dmrpp
            if self.granule_options['dmrpp_processing'] == "force":
                self.update_dmrpp(granule)
            elif self.granule_options['dmrpp_processing'] == "on":
                self.check_dmrpp(granule)

            with self.lock:
                self.granules_analyzed += 1
        except Exception as exc:
            self.logger.error(f"Error: {str(exc)}\n")

    def update_image(self, granule):
        """Create and send messages for one granule's image update."""

        with self.lock:
            self.granules_needing_image += 1
            self.concept_ids_needing_image.append(granule.concept_id())

            date = granule.start_date()[:7]
            self.monthly_results[date]['needs_image'] += 1
        if granule.s3_bucket_info():
            if not self.message_limit_reached():
                with self.lock:
                    self.image_messages_sent += 1
                message = self.message_writer.write(granule, needs_footprint=False,
                                                    needs_image=True, needs_dmrpp=False,
                                                    skip_cmr_opendap_update=True)
                for sender in self.message_senders:
                    sender.send(message)
        else:
            with self.lock:
                self.images_that_couldnt_be_processed += 1
            raise Exception(
                f"Could not process image for granule {granule.native_id()} because of missing S3 "
                f"bucket info")

    def update_footprint(self, granule):
        """Create and send messages for one granule's footprint update."""

        with self.lock:
            self.granules_needing_footprint += 1
            self.concept_ids_needing_footprint.append(granule.concept_id())

            date = granule.start_date()[:7]
            self.monthly_results[date]['needs_footprint'] += 1
        if granule.s3_bucket_info():
            if not self.message_limit_reached():
                with self.lock:
                    self.footprint_messages_sent += 1
                message = self.message_writer.write(granule, needs_footprint=True,
                                                    needs_image=False, needs_dmrpp=False,
                                                    skip_cmr_opendap_update=True)
                for sender in self.message_senders:
                    sender.send(message)
        else:
            with self.lock:
                self.footprints_that_couldnt_be_processed += 1
            raise Exception(
                f"Could not process footprint for granule {granule.native_id()} because of "
                f"missing S3 bucket info")

    def check_dmrpp(self, granule):
        """Check if dmrpp needs updating based on the dmrpp file state, and update if so."""

        s3_bucket_info = granule.s3_bucket_info()
        if s3_bucket_info:
            dmrpp_state = granule.get_dmrpp_state(f's3://{s3_bucket_info["bucket"]}'
                                                  f'/{s3_bucket_info["key"]}.dmrpp')
            if dmrpp_state == DmrppState.OLDER_VERSION:
                self.update_dmrpp(granule)
                with self.lock:
                    self.dmrpp_older_version += 1
            elif dmrpp_state == DmrppState.MISSING_VERSION:
                self.update_dmrpp(granule)
                with self.lock:
                    self.dmrpp_missing_version += 1
            elif dmrpp_state == DmrppState.MATCHED_VERSION:
                with self.lock:
                    self.dmrpp_unprocessed += 1
            elif dmrpp_state == DmrppState.NEWER_VERSION:
                with self.lock:
                    self.dmrpp_newer_version += 1
        else:
            with self.lock:
                self.dmrpp_that_couldnt_be_processed += 1
            raise Exception(
                f"Could not process dmrpp for granule {granule.native_id()} because of "
                f"missing S3 bucket info")

    def update_dmrpp(self, granule):
        """Create and send messages for one granule's dmrpp update."""

        with self.lock:
            self.granules_needing_dmrpp += 1
            self.concept_ids_needing_dmrpp.append(granule.concept_id())

            date = granule.start_date()[:7]
            self.monthly_results[date]['needs_dmrpp'] += 1
        if granule.s3_bucket_info():
            with self.lock:
                skip_cmr_opendap_update = granule.has_opendap_url()
                if not skip_cmr_opendap_update:
                    self.dmrpp_update_cmr_opendap += 1
            if not self.message_limit_reached():
                with self.lock:
                    self.dmrpp_messages_sent += 1
                message = self.message_writer.write(granule, needs_footprint=False,
                                                    needs_image=False, needs_dmrpp=True,
                                                    skip_cmr_opendap_update=skip_cmr_opendap_update)
                for sender in self.message_senders:
                    sender.send(message)
        else:
            with self.lock:
                self.dmrpp_that_couldnt_be_processed += 1
            raise Exception(
                f"Could not process dmrpp for granule {granule.native_id()} because of missing S3 "
                f"bucket info")

    def log_stats(self):
        """Log info about backfilling process"""
        self.logger.info(
            "\n==============================================================\n"
            f"Execution id: {self.cli_execution_id}\n"
            f"Matching granules: {self.search.total_matching_granules()}\n"
            f"Granules analyzed: {self.granules_analyzed}\n"
            f"  in time range: {self.granule_range_start or '-'} to {self.granule_range_end or '-'}\n\n"

            f"{self.granules_needing_footprint} granules need footprints\n"
            f"{self.footprints_that_couldnt_be_processed} footprints couldn't be processed because of missing s3 info\n"
            f"{self.footprint_messages_sent} footprint messages were sent\n\n"

            f"{self.granules_needing_image} granules need images\n"
            f"{self.images_that_couldnt_be_processed} images couldn't be processed because of missing s3 info\n"
            f"{self.image_messages_sent} image messages were sent\n\n"

            f"{self.granules_with_footprint_and_bbox} granules with both footprint and bbox\n"
        )
        if self.granule_options['dmrpp_processing'] == "on" or self.granule_options['dmrpp_processing'] == "force":
            self.logger.info(
                f"{self.granules_needing_dmrpp} granules need dmrpp\n"
                f"{self.dmrpp_that_couldnt_be_processed} dmrpp couldn't be processed because of missing s3 info\n"
                f"{self.dmrpp_messages_sent} dmrpp messages were sent\n"
            )
        if self.granule_options['dmrpp_processing'] == "on":
            self.logger.info(
                f" dmrpp details:\n"
                f"  {self.dmrpp_unprocessed} unprocessed\n"
                f"  {self.dmrpp_newer_version} with newer version\n"
                f"  {self.dmrpp_missing_version} missing version\n"
                f"  {self.dmrpp_older_version} with older version\n"
                f"  {self.dmrpp_update_cmr_opendap} missing cmr opendap url\n"
            )
        self.logger.info(
            f"-- {self.destination_message} --\n"
            "==============================================================\n"
        )
        if len(self.concept_ids_needing_image) > 0:
            self.logger.info(f"Granule IDs needing images (showing first 100):\n"
                             f" {self.concept_ids_needing_image[:100]}\n"
                             )
        if len(self.concept_ids_needing_footprint) > 0:
            self.logger.info(f"Granule IDs needing footprints (showing first 100):\n"
                             f" {self.concept_ids_needing_footprint[:100]}\n"
                             )
        if len(self.concept_ids_needing_dmrpp) > 0:
            self.logger.info(f"Granule IDs needing dmrpp (showing first 100):\n"
                             f" {self.concept_ids_needing_dmrpp[:100]}\n"
                             )
        self.print_monthly_results_table()

    def message_limit_reached(self):
        """Returns True if there is a message limit and it has been reached, otherwise False"""
        if self.message_limit is None:
            return False
        return self.footprint_messages_sent + self.image_messages_sent + self.dmrpp_messages_sent >= self.message_limit

    def get_forge_tig_configuration(self):
        """Function to get forge tig configuration of a collection"""

        config_url = "https://hitide.podaac.earthdatacloud.nasa.gov/dataset-configs/"
        collection_url = f"{config_url}{self.collection}.cfg"
        result = requests.get(collection_url, timeout=120)
        if result.status_code == 200:
            self.forge_tig_configuration = json.loads(result.content)
        else:
            self.forge_tig_configuration = None


def main(args=None):
    """Main script for backfilling from the cli"""

    # Disable pylint broad-except - So that a user friendly message can be displayed. Only used at top level
    # Disable pylint bare-except - So that after ctrl-C, a final status message can be logged. Only used at top level
    # pylint: disable=broad-except,bare-except

    # load args
    args = parse_args(args)
    args.cli_execution_id = str(uuid.uuid4())

    # setup dependencies
    try:
        logger = logger_from_args(args)

        logger.info(f"Started backfill: "                                 # pylint: disable=W1203
                    f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}")

        safe_log_args(logger, args)
        search = granule_search_from_args(args, logger)
        message_writer = message_writer_from_args(args, logger)
        message_senders = message_senders_from_args(args, logger)
        granule_options = granule_options_from_args(args)
        s3 = S3Reader(logger, args.aws_profile)    # pylint: disable=C0103
        collection = args.collection
    except Exception as exc:
        logger.error(f"Error: {str(exc)}\n")
        return

    # setup backfiller
    backfiller = Backfiller(search, message_writer, message_senders,
                            granule_options, logger, args.message_limit, args.cli_execution_id, s3, collection)

    # Check forge configurations before running backfill
    backfiller.get_forge_tig_configuration()

    if granule_options['footprint_processing'] != "off":
        if backfiller.forge_tig_configuration is None:
            raise Exception("There is no footprint settings for this collection, please disable footprint for backfilling")
        footprint_settings = backfiller.forge_tig_configuration.get('footprint')
        if not footprint_settings:
            raise Exception("There is no footprint settings for this collection, please disable footprint for backfilling")

    if granule_options['dmrpp_processing'] != "off":
        files = message_writer.collection_config.get('files', [])
        has_dmrpp_regex = False
        for file in files:
            if file.get('regex', "").endswith(".dmrpp$"):
                has_dmrpp_regex = True
                break
        if has_dmrpp_regex is False:
            raise Exception(f"There is no DMRPP regex in cumulus collection configuration for {message_writer.collection_name}")

    # run backfiller
    try:
        backfiller.process_granules()
    except Exception as exc:
        logger.error(exc)
    except:  # noqa: E722 - to catch ctrl-C
        logger.warning("keyboard interrupt")

    # close things up
    for message_sender in message_senders:
        message_sender.close()

    backfiller.log_stats()

    logger.info(f"Finished backfill: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}")  # pylint: disable=W1203


if __name__ == "__main__":
    main()
