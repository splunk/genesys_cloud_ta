import re
import datetime

from typing import List, Tuple
from PureCloudPlatformClientV2.models import (
    Edge,
    Phone,
    Queue,
    Trunk,
    User
)

class GCBaseModel:
    def __init__(self, data: List[dict]) -> None:
        self.data = data

    def to_camelcase(self, s: str) -> str:
        return re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), s)

    def to_string(self, dt: datetime) -> str:
        formatting_str = "%d-%m-%YT%H:%M:%S.%f%z"
        return dt.strftime(formatting_str)

    def to_datetime(self, dt_string: str) -> datetime:
        formatting_str = "%Y-%m-%dT%H:%M:%S.%fZ"
        return datetime.datetime.strptime(dt_string, formatting_str).replace(tzinfo=datetime.timezone.utc)

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
    MAX_TRUNK_IDS: int = 100

    def __init__(self, trunks: List[Trunk]) -> None:
        super().__init__([trunk.to_dict() for trunk in trunks])

    @property
    def trunk_ids(self) -> List[str]:
        return [trunk["id"] for trunk in self.data]

    def get_trunk_ids(self, batch: int = 0) -> Tuple[List[str], bool]:
        factor = self.MAX_TRUNK_IDS * batch
        slice_limit = self.MAX_TRUNK_IDS + factor
        remaining_trunks = max(0, len(self.data) - factor)
        has_next_batch = remaining_trunks > self.MAX_TRUNK_IDS
        return [trunk["id"] for trunk in self.data[factor:slice_limit]], has_next_batch

    def get_trunk(self, tid: str) -> dict:
        ret_trunk = {}
        required_keys = [
            "id", "name", "date_created", "date_modified", "state",
            "trunk_type", "edge", "trunk_base", "in_service", "enabled",
            "connected_status", "ip_status"
        ]

        trunk = next((t for t in self.data if t["id"] == tid), None)
        if trunk is None:
            raise ValueError(f"Trunk {tid} not found")
        ret_trunk.update({k: trunk[k] for k in required_keys if k in trunk})
        return ret_trunk


class EdgeModel(GCBaseModel):
    MAX_EDGE_IDS: int = 100

    def __init__(self, edges: List[Edge]):
        super().__init__([edge.to_dict() for edge in edges])

    def get_edge_ids(self, batch: int = 0) -> Tuple[List[str], bool]:
        factor = self.MAX_EDGE_IDS*batch
        slice_limit = self.MAX_EDGE_IDS + factor
        remaining_edges = max(0, len(self.data) - factor)
        has_next_batch = remaining_edges > self.MAX_EDGE_IDS
        return [edge["id"] for edge in self.data[factor:slice_limit]], has_next_batch

    def get_edge(self, eid: str) -> dict:
        ret_edge = { "site": {} }
        required_keys = [
            "id", "name", "version", "description", "date_created", "date_modified",
            "state", "interfaces", "online_status",
            "serial_number", "physical_edge", "edge_deployment_type",
            "conversation_count", "os_name"
        ]

        edge = next((e for e in self.data if e["id"] == eid), None)
        if edge is None:
            raise ValueError(f"Edge {eid} not found")
        ret_edge.update({k: edge[k] for k in required_keys if k in edge})
        # Avoid indexing a lot of "null" values added
        # by the to_dict() SDK function for "site" data
        for key, value in edge["site"].items():
            if key in ["id", "name", "state"]:
                ret_edge["site"][key] = value
        return ret_edge


class PhoneModel(GCBaseModel):
    STATUS_TYPES = ["status", "secondary_status"]

    def __init__(self, phones: List[Phone]) -> None:
        super().__init__([phone.to_dict() for phone in phones])

    @property
    def statuses(self) -> List[dict]:
        statuses = []
        for phone in self.data:
            for s_type in self.STATUS_TYPES:
                statuses.append(phone.get(s_type))
        return statuses

    @property
    def extended_statuses(self) -> List[dict]:
        """ Returning statuses augmented with phones info """
        required_keys = ["name", "date_created", "date_modified", "state", "site"]
        statuses = []
        for phone in self.data:
            new_status = {k: phone[k] for k in required_keys if k in phone}
            for s_type in self.STATUS_TYPES:
                status = phone.get(s_type)
                if not isinstance(status, dict):
                    continue
                statuses.append({**status, **new_status})
        return statuses


class QueueModel(GCBaseModel):
    MAX_QUEUE_IDS: int = 200

    def __init__(self, queues: List[Queue]) -> None:
        super().__init__([queue.to_dict() for queue in queues])

    @property
    def queue_ids(self) -> List[str]:
        return [queue["id"] for queue in self.data]

    def get_queue_ids(self, batch: int = 0) -> Tuple[List[str], bool]:
        factor = self.MAX_QUEUE_IDS*batch
        slice_limit = self.MAX_QUEUE_IDS + factor
        remaining_queues = max(0, len(self.data) - factor)
        has_next_batch = remaining_queues > self.MAX_QUEUE_IDS
        return [queue["id"] for queue in self.data[factor:slice_limit]], has_next_batch

    def get_queue(self, qid: str) -> dict:
        ret_queue = {}
        required_keys = ["id", "name"]

        queue = next((q for q in self.data if q["id"] == qid), None)
        if queue is None:
            raise ValueError(f"Queue {qid} not found")
        ret_queue.update({k: queue[k] for k in required_keys if k in queue})
        return ret_queue


class UserModel(GCBaseModel):
    MAX_USER_IDS: int = 100

    def __init__(self, users: List[User]) -> None:
        super().__init__([user.to_dict() for user in users])

    @property
    def user_ids(self) -> List[str]:
        return [user["id"] for user in self.data]

    def get_user_ids(self, batch: int = 0) -> Tuple[List[str], bool]:
        factor = self.MAX_USER_IDS*batch
        slice_limit = self.MAX_USER_IDS + factor
        remaining_users = max(0, len(self.data) - factor)
        has_next_batch = remaining_users > self.MAX_USER_IDS
        return [user["id"] for user in self.data[factor:slice_limit]], has_next_batch

    def get_user(self, uid: str) -> dict:
        ret_user = {}
        required_keys = ["id", "name", "chat", "email", "division"]

        user = next((u for u in self.data if u["id"] == uid), None)
        if user is None:
            raise ValueError(f"User {uid} not found")
        ret_user.update({k: user[k] for k in required_keys if k in user})
        return ret_user