"""Search for CMR granules"""

import ast
import json
import logging
from requests import Session
from requests.exceptions import RequestException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .cmr_granule import CmrGranule


class GranuleSearch:
    """Searches for CMR granules, with paging"""

    # pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-locals

    def __init__(self,
                 base_url,
                 collection_short_name,
                 start_date=None,
                 end_date=None,
                 provider='pocloud',
                 edl_token=None,
                 launchpad_token=None,
                 page_size=2000,
                 page_limit=5,
                 logger=logging,
                 cmr_search_after=None,
                 cycles=None,
                 sort_order="ascending"):
        """Create GranuleSearch object"""

        self._base_url = base_url
        self._collection_short_name = collection_short_name
        self._start_date = start_date
        self._end_date = end_date
        self._provider = provider
        self._edl_token = edl_token
        self._launchpad_token = launchpad_token
        self._page_size = page_size
        self._page_limit = page_limit
        self._cmr_search_after = cmr_search_after
        self._granules = []
        self._total_matching_granules = 0
        self._pages_loaded = 0
        self._logger = logger
        self.cycles = cycles

        if sort_order == "descending":
            self.sort_order = "-start_date"
        else:
            self.sort_order = "start_date"

        if sort_order == "descending":
            self.sort_order = "-start_date"
        else:
            self.sort_order = "start_date"

        retry = Retry(connect=10, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)

        self.session = Session()
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def granule_generator(self):
        """Return iterable that provides all matching granules across multipl pages"""

        while not self.is_done():
            self.get_next_page()
            if len(self.granules()) == 0:
                return "Problem reading granules"
            for granule in self.granules():
                yield CmrGranule(granule)
        return "Finished reading granules"

    def get_next_page(self):
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        """Retrieve the first or next page of granule search results and
        return True if granules received, False otherwise
        """

        if self.is_done():
            self._logger.warning(
                "-- trying to get_next_page after search is done --")
            self._granules = []
            return False

        url = (f"{self._base_url}/search/granules.umm_json?provider={self._provider}"
               f"&page_size={self._page_size}&sort_key[]={self.sort_order}")
        url += f"&short_name={self._collection_short_name}"
        url += _temporal_param(self._start_date, self._end_date)

        if self.cycles:
            try:
                cycle_list = ast.literal_eval(self.cycles)
                cycles_output = ""
                if isinstance(cycle_list, list):
                    for cycle in cycle_list:
                        cycles_output += f"cycle[]={cycle}&"
                    cycles_output = cycles_output[:-1]
                else:
                    cycles_output = f"cycle[]={cycle_list}"
            except (ValueError, SyntaxError):
                print("Invalid input. Please provide a valid list or a single number.")

            url += f"&{cycles_output}"

        headers = {}
        if self._cmr_search_after:
            headers["cmr-search-after"] = self._cmr_search_after
        if self._edl_token:
            headers["Authorization"] = f"Bearer {self._edl_token}"
        elif self._launchpad_token:
            headers["Authorization"] = self._launchpad_token

        if self._pages_loaded == 0:
            print("\nRequesting first CMR page...", end='', flush=True)
        else:
            print("Requesting next CMR page...", end='', flush=True)

        body = {}
        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()

            body = json.loads(response.text)
        except RequestException as exc:
            self._logger.error(f"Error requesting CMR: {exc}")
        except json.JSONDecodeError as exc:
            self._logger.error(f"Error decoding CMR JSON response: {exc}")

        # Error message if there is a problem
        if response.status_code >= 400 or body.get("hits") is None or body.get("items") is None:
            last_granule_message = "No granules received"
            if len(self._granules) > 0:
                last_granule = CmrGranule(self._granules[-1])
                last_granule_message = (f"{last_granule.concept_id()} {last_granule.native_id()}"
                                        f" {last_granule.start_date()} {last_granule.end_date()}")
            self._logger.error(
                f"\nCMR problem:\n"
                f"url: {url}\n"
                f"cmr-search-after: {headers.get('cmr-search-after')}\n"
                f"----------\n"
                f"http_code: {response.status_code}\n"
                f"body: {response.text}\n"
                f"----------\n"
                f"last_granule: {last_granule_message}\n"
            )
            raise Exception("CMR error")

        # Update to latest page received
        self._cmr_search_after = response.headers.get("cmr-search-after")
        self._total_matching_granules = body["hits"]
        self._granules = body["items"]
        self._pages_loaded += 1

        self._logger.info(
            f"\nCMR PAGE LOAD # {self.pages_loaded()}:\n"
            f"url: {url}\n"
            f"cmr-search-after: {headers.get('cmr-search-after')}\n"
            f"---------\n"
            f"http_code: {response.status_code}\n"
            f"hits: {body.get('hits')}\n"
            f"granules in page: {len(self.granules())}\n"
        )

        return bool(self.granules)

    def is_done(self):
        """Return True if all pages have been retrieved, or if page_limit reached"""

        return (
            # reached page limit
            (self._page_limit and self._pages_loaded >= self._page_limit) or
            # all pages have been loaded
            (not self._cmr_search_after and self._pages_loaded > 0)
        )

    def granules(self):
        """Return the most recently loaded page of granules"""
        return self._granules

    def total_matching_granules(self):
        """Return the total number of granules that match the search criteria (across all pages)"""

        return self._total_matching_granules

    def pages_loaded(self):
        """Return the total number of granule search pages that have been loaded up to this point"""
        return self._pages_loaded

#
#   Helpers
#


def _temporal_param(start_date, end_date):
    """Convert start/end dates to formatted temporal url param for granule search"""
    if not start_date and not end_date:
        return ""
    param = "&temporal="
    if start_date:
        param += start_date
    param += ","
    if end_date:
        param += end_date
    return param
