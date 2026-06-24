import pytest
import time
# import os
import json
import hashlib
import splunklib.results as splk_results

from .BaseTATest import BaseTATest

class TestGenesysCloudTA(BaseTATest):

    def setup_method(self, method):
        super(TestGenesysCloudTA, self).setup_method(method)

    def teardown_method(self, method):
        super(TestGenesysCloudTA, self).teardown_method(method)

    def _search_oneshot(self, search_query: str, base_sleep: int=2, timeout: int=40) -> list:
        """
        Run search to verify data ingestion.

        :param search_query: SPL to be executed.
        :param base_sleep: base seconds for backoff (doubles each retry).
        :param timeout: max seconds to cap on the wait between retries.
        :return: list of unique event results.
        """
        results: list[dict] = []
        # ci_factor = 3 if os.getenv("CI", "").lower() == "true" else 1
        kwargs = {
            "earliest_time": 0,
            "latest_time": "now",
            "output_mode": "json",
            "count": 0
        }

        for attempt in range(self.MAX_RETRIES):
            oneshot = self.splunk_client.jobs.oneshot(search_query, **kwargs)
            reader = splk_results.JSONResultsReader(oneshot)

            for res in reader:
                results.append(res)

            if len(results) > 0 or attempt == (self.MAX_RETRIES - 1):
                self.logger.debug(f"Attempt {attempt+1}, results {len(results)}")
                break

            # Exponential backoff: base * 2^attempt, capped at timeout
            wait = min(base_sleep * (2 ** (attempt+1)), timeout)
            # wait = min((3 * (attempt+1)) * ci_factor, timeout)
            self.logger.debug(f"Attempt {attempt+1}, waiting {wait}s")
            time.sleep(wait)

        self.logger.debug(f"Splunk search returned {len(results)} results")
        return results

    # @pytest.mark.skip(reason="already tested")
    def test_input_chat_observations(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:analytics:flows:metrics"
        source = "conversations_metrics://chat_observations"
        spl = f"search index={self.INDEX} sourcetype={sourcetype} source={source}"
        results = self._search_oneshot(search_query=spl)
        assert len(results) > 0 and len(results) <= 60

    def test_input_conversations_details(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:analytics:conversations:details"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        results = self._search_oneshot(search_query=spl)
        assert len(results) > 0 and len(results) <= 114
        assert results[0]["source"] == "conversations_details://conversations_details"

    def test_input_conversations_metrics(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:analytics:flows:metrics"
        source = "conversations_metrics://conversations_metrics"
        spl = f"search index={self.INDEX} sourcetype={sourcetype} source={source}"
        results = self._search_oneshot(search_query=spl)
        assert len(results) > 0 and len(results) <= 55

    def test_input_user_routing_status(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:users:users:routingstatus"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        results = self._search_oneshot(search_query=spl, base_sleep=3, timeout=100)
        assert len(results) > 0 and len(results) <= 358
        assert results[0]["source"] == "user_routing_status://user_routing_status"

    def test_input_edges_metrics(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:telephonyprovidersedge:edges:metrics"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        results = self._search_oneshot(search_query=spl)

        # Each event is split into 2: status and secondary status
        assert len(results) > 0 and len(results) <= 157
        assert results[0]["source"] == "edges_metrics://edges_metrics"

    # @pytest.mark.skip(reason="already tested")
    def test_input_edges_phones(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:telephonyprovidersedge:edges:phones"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        results = self._search_oneshot(search_query=spl, base_sleep=3, timeout=60)

        # Each event is split into 2: status and secondary status
        assert len(results) > 0 and len(results) <= 2 * 25
        assert results[0]["source"] == "edges_phones://edges_phones"

    def test_input_edges_trunks_metrics(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:telephonyprovidersedge:trunks:metrics"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        results = self._search_oneshot(search_query=spl, base_sleep=3, timeout=60)
        assert len(results) > 0 and len(results) <= 14
        assert results[0]["source"] == "edges_trunks_metrics://edges_trunks_metrics"

    def test_input_queue_observations(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:analytics:queues:observations"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        results = self._search_oneshot(search_query=spl)
        assert len(results) > 0 and len(results) <= 4082
        assert results[0]["source"] == "queue_observations://queue_observations"

    def test_input_user_aggregates(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:users:users:aggregates"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        results = self._search_oneshot(search_query=spl)
        assert len(results) > 0 and len(results) <= 716
        assert results[0]["source"] == "user_aggregates://user_aggregates"

    def test_input_actions_metrics(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:analytics:actions:metrics"
        source = "actions_metrics://actions_metrics"
        spl = f"search index={self.INDEX} sourcetype={sourcetype} source={source}"
        results = self._search_oneshot(search_query=spl)
        assert len(results) > 0 and len(results) <= 5
        assert results[0]["source"] == source

    def test_input_audit_query(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:operational:audits"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        results = self._search_oneshot(search_query=spl)

        # The mock returns ~5 entities -> ~5 events
        assert len(results) > 0 and len(results) <= 50
