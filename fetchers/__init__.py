from .ashby import fetch_ashby
from .generic import fetch_generic
from .greenhouse import fetch_greenhouse
from .lever import fetch_lever
from .workable import fetch_workable


FETCHERS = {
    "ashby": fetch_ashby,
    "generic": fetch_generic,
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "workable": fetch_workable,
}

