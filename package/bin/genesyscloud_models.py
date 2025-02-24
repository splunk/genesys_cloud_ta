import re
import datetime
from typing import List, Tuple
from PureCloudPlatformClientV2.models import Trunk, Edge


class GCBaseModel:
    data: List[dict] = []

    def __init__(self, data: List[dict]) -> None:
        self.data = data

    def to_camelcase(self, s: str) -> str:
        return re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), s)

    def to_string(self, dt: datetime) -> str:
        format = "%d-%m-%YT%H:%M:%S.%f%z"
        return dt.strftime(format)

    def to_datetime(self, dt_string: str) -> datetime:
        format = "%Y-%m-%dT%H:%M:%S.%fZ"
        return datetime.datetime.strptime(dt_string, format)

    def extract(self, idx: int, sub_key: str, keys_to_extract: list) -> dict:
        """
        Extract a sub-dictionary and specific key-value pairs from it.
        :param idx: The index of the item containing the sub_key.
        :param sub_key: The key containing the sub-dictionary.
        :param keys_to_extract: List of keys to extract from the sub-dictionary.
        :return: A new dictionary containing the extracted key-value pairs.
        """
        if sub_key not in self.data[idx] or not isinstance(self.data[idx][sub_key], dict):
            raise ValueError(f"Key '{sub_key}' not found or is not a dictionary")

        sub_dict = self.data[idx][sub_key]
        sub_key_cc = self.to_camelcase(sub_key)
        return {f"{sub_key_cc}{key.capitalize()}": sub_dict[key] for key in keys_to_extract if key in sub_dict}


class TrunkModel(GCBaseModel):
    def __init__(self, trunks: List[Trunk]) -> None:
        lst_trunks = []
        for trunk in trunks:
            lst_trunks.append(trunk.to_dict())
        super().__init__(lst_trunks)

    @property
    def trunks(self) -> List[dict]:
        trunks = []
        keys = ["id", "name", "state", "trunk_type", "in_service", "enabled"]
        nested_keys = ["id", "name"]
        for idx, trunk in enumerate(self.data):
            new_trunk = {self.to_camelcase(key): trunk[key] for key in keys}
            new_trunk["dateCreated"] = self.to_string(trunk["date_created"])
            new_trunk["dateModified"] = self.to_string(trunk["date_modified"])
            new_trunk.update(self.extract(idx, "trunk_base", nested_keys))
            new_trunk.update(self.extract(idx, "edge", nested_keys))
            if trunk["connected_status"]:
                new_trunk["connectedStatus"] = trunk["connected_status"]["connected"]
            # Adding a _key to avoid lookup duplicates
            new_trunk["_key"] = new_trunk["id"]
            trunks.append(new_trunk)
        return trunks

    @property
    def trunk_ids(self) -> List[str]:
        return [trunk["id"] for trunk in self.data]


class EdgeModel(GCBaseModel):
    MAX_EDGE_IDS: int = 100

    def __init__(self, edges: List[Edge]):
        lst_edges = []
        for e in edges:
            lst_edges.append(e.to_dict())
        super().__init__(lst_edges)

    @property
    def edges(self) -> List[dict]:
        edges = []
        keys = [
            "id", "name", "version", "description", "state", "online_status",
            "serial_number", "physical_edge", "managed", "edge_deployment_type",
            "conversation_count", "call_draining_state", "os_name"
        ]
        nested_keys = ["id", "name", "state"]
        # Cannot find:
        # - status as per ACTIVE, DISCONNECTED, media, lastConnectionTime, osVersion
        for idx, edge in enumerate(self.data):
            new_edge = {self.to_camelcase(key): edge[key] for key in keys}
            new_edge["dateCreated"] = self.to_string(edge["date_created"])
            new_edge["dateModified"] = self.to_string(edge["date_modified"])
            new_edge.update(self.extract(idx, "site", nested_keys))
            # Adding a _key to avoid lookup duplicates
            new_edge["_key"] = new_edge["id"]
            edges.append(new_edge)
        return edges

    def get_edge_ids(self, batch: int = 0) -> Tuple[List[str], bool]:
        factor = self.MAX_EDGE_IDS*batch
        slice = self.MAX_EDGE_IDS + factor
        remaining_edges = abs(len(self.data) - factor)
        has_next_batch = remaining_edges > self.MAX_EDGE_IDS
        return [edge["id"] for edge in self.data[factor:slice]], has_next_batch
