"""Helper functions for dealing with CMR search"""


def cmr_base_url(env):
    """Given an environment name, return the CMR base url"""

    if env == "ops":
        return "https://cmr.earthdata.nasa.gov"
    if env == "uat":
        return "https://cmr.uat.earthdata.nasa.gov"
    if env == "sit":
        return "https://cmr.sit.earthdata.nasa.gov"
    raise ValueError("Improper environment specified: " + str(env))
