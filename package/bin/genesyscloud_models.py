import re
import datetime
from typing import List
from PureCloudPlatformClientV2.models import Trunk


def to_camelcase(s: str) -> str:
    return re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), s)

def to_string(dt: datetime) -> str:
    format = "%d-%m-%YT%H:%M:%S.%f%z"
    return dt.strftime(format)


class EdgeTrunkModel:
    _trunks: List[Trunk] = []

    def __init__(self, trunks: List[Trunk]):
        self._trunks = trunks

    @property
    def trunks(self) -> List[dict]:
        trunks = []
        keys = ["id", "name", "state", "trunk_type", "in_service", "enabled"]
        for trunk_obj in self._trunks:
            trunk = trunk_obj.to_dict()
            new_trunk = {to_camelcase(key): trunk[key] for key in keys}
            new_trunk["dateCreated"] = to_string(trunk["date_created"])
            new_trunk["dateModified"] = to_string(trunk["date_modified"])
            new_trunk["trunkbaseId"] = trunk["trunk_base"]["id"]
            new_trunk["trunkbaseName"] = trunk["trunk_base"]["name"]
            new_trunk["edgeGroupId"] = trunk["edge_group"]["id"]
            new_trunk["edgeGroupName"] = trunk["edge_group"]["name"]
            if trunk["connected_status"]:
                new_trunk["connectedStatus"] = trunk["connected_status"]["connected"]
            # Adding a _key to avoid lookup duplicates
            new_trunk["_key"] = new_trunk["id"]
            trunks.append(new_trunk)
        return trunks

    @property
    def trunk_ids(self) -> List[str]:
        return [trunk.id for trunk in self._trunks]

    @property
    def edges(self) -> List[dict]:
        edges = []
        keys = ["_key", "id", "name"]
        for trunk_obj in self._trunks:
            trunk = trunk_obj.to_dict()
            # Adding a _key to avoid lookup duplicates
            trunk["edge"]["_key"] = trunk["edge"]["id"]
            edges.append({key: trunk["edge"][key] for key in keys})
        return edges
