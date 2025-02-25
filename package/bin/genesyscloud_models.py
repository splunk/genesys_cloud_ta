import re
import datetime
from typing import List
from PureCloudPlatformClientV2.models import Trunk, FlowAggregateQueryResponse
import logging


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


class ConversationsModel:
    _conversations: FlowAggregateQueryResponse = {}

    def __init__(self,logger:logging.Logger, conversations: FlowAggregateQueryResponse):
        self._conversations = conversations
        self.logger = logger
        logger.info(f"CLASS HAS BEEN INSTANTIATED WORKING6 {self._conversations}")

    @property
    def conversations(self) -> List[dict]:

        conversations = []
        process_data = self._conversations.to_dict()

        for result in process_data["results"]:

            self.logger.info(f"WORKING40 RESULTS = {result}")
            group = result.get("group", {})

            queue_id = group.get("queueId") 
            media_type = group.get("mediaType")

            self.logger.info(f"WORKING41 queueId = {queue_id} media_type = {media_type}")

            for data_entry in result.get("data", []):
                interval = data_entry.get("interval")

                for metric_entry in data_entry.get("metrics", []):
                    metric_name = metric_entry.get("metric")
                    stats = metric_entry.get("stats", {})

                    # Construimos un objeto plano con toda la información relevante
                    conversation_data = {
                        "queueId": queue_id,
                        "mediaType": media_type,
                        "interval": interval,
                        "metric": metric_name,
                        "max": stats.get("max"),
                        "min": stats.get("min"),
                        "count": stats.get("count"),
                        "count_negative": stats.get("count_negative"),
                        "count_positive": stats.get("count_positive"),
                        "sum": stats.get("sum"),
                        "current": stats.get("current"),
                        "ratio": stats.get("ratio"),
                        "numerator": stats.get("numerator"),
                        "denominator": stats.get("denominator"),
                        "target": stats.get("target"),
                        "p95": stats.get("p95"),
                        "p99": stats.get("p99"),
                    }
                    self.logger.info(f"WORKING42 {conversation_data}")
                    # Agregar al listado de conversaciones
                    conversations.append(conversation_data)

        return conversations

