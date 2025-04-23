import pytest
import uuid

from .GenesysCloudTATest import GenesysCloudTATest


class TestGenesysCloudClient(GenesysCloudTATest):
    """Test Class for Genesys Cloud Client Component"""


    @pytest.mark.parametrize("api_name, func_name, expected_result",
        [
            ("TelephonyProvidersEdgeApi", "get_telephony_providers_edges", 157),
            ("TelephonyProvidersEdgeApi", "get_telephony_providers_edges_trunks", 14),
            ("RoutingApi", "get_routing_queues", 157),
            ("UsersApi", "get_users", 358)
        ],
    )
    def test_GET(self, api_name, func_name, expected_result):
        """Test regular GET calls"""

        response = self.gc_client.get(
            api_name,
            func_name
        )
        assert len(response) == expected_result


    @pytest.mark.parametrize("api_name, func_name, params",
        [
            ("TelephonyProvidersEdgeApi", "get_telephony_providers_edges_phones", dict(expand="site,status")),
            ("TelephonyProvidersEdgeApi", "get_telephony_providers_edges_trunks_metrics", [str(uuid.uuid4()), str(uuid.uuid4())]),
            ("TelephonyProvidersEdgeApi", "get_telephony_providers_edges_metrics", [str(uuid.uuid4()), str(uuid.uuid4())]),
            ("UsersApi", "get_user_routingstatus", [str(uuid.uuid4())]),
        ],
    )
    def test_GET_w_params(self, api_name, func_name, params):
        """Test GET calls passing parameters"""
        if isinstance(params, dict):
            response = self.gc_client.get(
                api_name,
                func_name,
                **params
            )
            assert len(response) == 25
            d_response = response[0].to_dict()
            assert d_response.get("status"), "Entities do not contain 'status' extra data"
            assert d_response.get("secondary_status"), "Entities do not contain 'secondary status' extra data"
            assert d_response.get("site",{}).get("name"), "Entities do not contain 'site' extra data"

        else:
            response = self.gc_client.get(
                api_name,
                func_name,
                ','.join(params)
            )
            assert len(response) == 2 if len(params) > 1 else len(response) == 1


    @pytest.mark.parametrize("api_name, func_name",
        [
            ("TelephonyProvidersEdgeApi", "get_telephony_providers_edges_trunks_metrics"),
            ("UsersApi", "get_user_routingstatus")
        ],
    )
    def test_GET_missing_params(self, api_name, func_name):
        """Test GET calls throwing error for lack of function arguments"""

        with pytest.raises(TypeError) as excinfo:
            response = self.gc_client.get(
                api_name,
                func_name
            )
        assert "missing 1 required positional argument: " in str(excinfo.value)


    @pytest.mark.parametrize("api_name, func_name, param",
        [
            ("UsersApi", "get_user_routingstatus", "WrongId"),
            ("UsersApi", "get_user_routingstatus", "1235"),
            ("TelephonyProvidersEdgeApi", "get_telephony_providers_edges_trunks_metrics", "12,3457,asd")
        ],
    )
    def test_GET_wrong_param(self, api_name, func_name, param):
        """Test GET calls throwing error for unexpected value of a param"""

        response = self.gc_client.get(
            api_name,
            func_name,
            param
        )
        assert len(response) == 0


    @pytest.mark.parametrize("api_name, func_name, model_name, expected_result, direction",
        [
            ("ConversationsApi", "post_analytics_conversations_aggregates_query", "ConversationAggregationQuery", 4, "inbound,outbound"),
            ("ConversationsApi", "post_analytics_conversations_aggregates_query", "ConversationAggregationQuery", 10, "inbound"),
            ("ConversationsApi", "post_analytics_conversations_details_query", "ConversationQuery", 114, ""),
        ],
    )
    def test_POST_conversations(self, body_conversations, api_name, func_name, model_name, expected_result, direction):
        """Test POST calls to query conversations data"""
        _filter = None
        directions = direction.split(",")
        directions = list(filter(None, directions))
        predicates = [{"dimension": "direction", "value": d} for d in directions]

        if len(directions) > 0:
            _filter = {
                "type": "and",
                "clauses": [
                    {
                        "type": "or",
                        "predicates": predicates
                    }
                ]
            }

        basic = "aggregates" in func_name

        response = self.gc_client.post(
            api_name,
            func_name,
            model_name,
            body_conversations(basic, _filter)
        )
        if isinstance(response, list):
            lst_response = self.gc_client.convert_response(response, "conversations")
            assert len(lst_response) == expected_result
        else:
            results = response.to_dict().get("results", [])
            assert len(results) == expected_result


    @pytest.mark.parametrize("api_name, func_name, model_name",
        [
            ("RoutingApi", "post_analytics_queues_observations_query", "QueueObservationQuery"),
            ("UsersApi", "post_analytics_users_aggregates_query", "UserAggregationQuery"),
        ],
    )
    def test_POST_others(self, body_routing_queues, body_users, api_name, func_name, model_name):
        """Test POST calls to query routing and users data"""
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        if "Routing" in api_name:
            body = body_routing_queues(ids)
            expected_result = 7*len(ids)
        else:
            body = body_users(ids)
            expected_result = len(ids)

        response = self.gc_client.post(
            api_name,
            func_name,
            model_name,
            body
        )
        assert len(response.to_dict().get("results", [])) == expected_result


    @pytest.mark.parametrize("api_name, func_name, model_name",
        [
            ("RoutingApi", "post_analytics_queues_observations_query", "QueueObservationQuery"),
            ("UsersApi", "post_analytics_users_aggregates_query", "UserAggregationQuery"),
        ],
    )
    def test_POST_wrong_body(self, body_routing_queues, body_users, api_name, func_name, model_name):
        """Test POST calls throwing error for unexpected body"""
        if "Routing" in api_name:
            body = body_routing_queues(None)
        else:
            body = body_users(None)

        response = self.gc_client.post(
            api_name,
            func_name,
            model_name,
            body
        )
        assert response == None
