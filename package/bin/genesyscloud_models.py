import re
import datetime
import json

from typing import List, Tuple
from PureCloudPlatformClientV2.models import (
    Edge,
    Phone,
    Queue,
    Trunk,
    User
)

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

    def extract(self, idx: int, sub_key: str, keys_to_extract: list, enable_camelcase: bool = False) -> dict:
        """
        Extract a sub-dictionary and specific key-value pairs from it.
        :param idx: The index of the item containing the sub_key.
        :param sub_key: The key containing the sub-dictionary.
        :param keys_to_extract: List of keys to extract from the sub-dictionary.
        :param enable_camelcase: Enable key format to camelcase.
        :return: A new dictionary containing the extracted key-value pairs.
        """
        if sub_key not in self.data[idx] or not isinstance(self.data[idx][sub_key], dict):
            raise ValueError(f"Key '{sub_key}' not found or is not a dictionary")

        sub_dict = self.data[idx][sub_key]
        sub_key_cc = self.to_camelcase(sub_key) if enable_camelcase else sub_key
        return {
            f"{sub_key_cc}{key.capitalize()}" if enable_camelcase else f"{sub_key}_{key}": sub_dict[key] for key in keys_to_extract if key in sub_dict
        }


class TrunkModel(GCBaseModel):
    def __init__(self, trunks: List[Trunk]) -> None:
        lst_trunks = []
        for trunk in trunks:
            lst_trunks.append(trunk.to_dict())
        super().__init__(lst_trunks)

    @property
    def trunk_ids(self) -> List[str]:
        return [trunk["id"] for trunk in self.data]

    def get_trunk(self, tid: str) -> dict:
        ret_trunk = {}
        required_keys = [
            "id", "name", "date_created", "date_modified", "state",
            "trunk_type", "edge", "trunk_base", "in_service", "enabled",
            "connected_status", "ip_status"
        ]

        trunk = [t for t in self.data if t["id"] == tid][0]
        for key, value in trunk.items():
            ret_trunk.update({k: trunk[k] for k in required_keys})
        return ret_trunk


class EdgeModel(GCBaseModel):
    MAX_EDGE_IDS: int = 100

    def __init__(self, edges: List[Edge]):
        lst_edges = []
        for e in edges:
            lst_edges.append(e.to_dict())
        super().__init__(lst_edges)

    def _parse_interfaces(self, interfaces: List[dict], targeted_key: str) -> str:
        ret = ""
        for interface in interfaces:
            ret = f"{interface[targeted_key]},"
        return ret[:-1]

    @property
    def edges(self) -> List[dict]:
        edges = []
        keys = [
            "id", "name", "version", "description", "state", "online_status",
            "serial_number", "physical_edge", "edge_deployment_type",
            "conversation_count", "os_name"
        ]
        nested_keys = ["id", "name", "state"]
        # Cannot find:
        # - status as per ACTIVE, DISCONNECTED, media, lastConnectionTime, osVersion
        for idx, edge in enumerate(self.data):
            # new_edge = {self.to_camelcase(key): edge[key] for key in keys}
            new_edge = {key: edge[key] for key in keys}
            new_edge["date_created"] = self.to_string(edge["date_created"])
            new_edge["date_modified"] = self.to_string(edge["date_modified"])
            new_edge.update(self.extract(idx, "site", nested_keys))
            new_edge["mac_address"] = self._parse_interfaces(edge["interfaces"], "mac_address")
            new_edge["ip_address"] = self._parse_interfaces(edge["interfaces"], "ip_address")
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


class PhoneModel(GCBaseModel):
    def __init__(self, phones: List[Phone]) -> None:
        lst_phones = []
        for phone in phones:
            lst_phones.append(phone.to_dict())
        super().__init__(lst_phones)

    @property
    def phones(self) -> List[dict]:
        phones = []
        keys = ["id", "name", "state"]
        nested_keys = ["id", "name"]
        for idx, phone in enumerate(self.data):
            # new_phone = {self.to_camelcase(key): phone[key] for key in keys}
            new_phone = {key: phone[key] for key in keys}
            new_phone["date_created"] = self.to_string(phone["date_created"])
            new_phone["date_modified"] = self.to_string(phone["date_modified"])
            new_phone.update(self.extract(idx, "site", nested_keys))
            # Adding a _key to avoid lookup duplicates
            new_phone["_key"] = new_phone["id"]
            phones.append(new_phone)
        return phones

    @property
    def statuses(self) -> List[dict]:
        statuses = []
        for phone in self.data:
            statuses.append(phone["status"])
            statuses.append(phone["secondary_status"])
        return statuses


class QueueModel(GCBaseModel):
    def __init__(self, queues: List[Queue]) -> None:
        lst_queues = []
        for queue in queues:
            lst_queues.append(queue.to_dict())
        super().__init__(lst_queues)

    @property
    def queues(self) -> List[dict]:
        queues = []
        for queue in self.data:
            new_queue = {
                "id": queue["id"],
                "name": queue["name"],
                "_key": queue["id"]
            }
            queues.append(new_queue)
        return queues

    @property
    def queue_ids(self) -> List[str]:
        return [queue["id"] for queue in self.data]


class UserModel(GCBaseModel):
    MAX_USER_IDS: int = 100

    def __init__(self, users: List[User]) -> None:
        lst_users = []
        for user in users:
            lst_users.append(user.to_dict())
        super().__init__(lst_users)

    @property
    def user_ids(self) -> List[str]:
        return [user["id"] for user in self.data]

    def get_user_ids(self, batch: int = 0) -> Tuple[List[str], bool]:
        factor = self.MAX_USER_IDS*batch
        slice = self.MAX_USER_IDS + factor
        remaining_users = abs(len(self.data) - factor)
        has_next_batch = remaining_users > self.MAX_USER_IDS
        return [user["id"] for user in self.data[factor:slice]], has_next_batch

    def get_user(self, uid: str) -> dict:
        ret_user = {}
        required_keys = ["id", "name", "chat", "email", "division"]

        user = [u for u in self.data if u["id"] == uid][0]
        for key, value in user.items():
            ret_user.update({k: user[k] for k in required_keys})
        return ret_user