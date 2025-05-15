import pytest
import time
import json
import hashlib
import sys
import splunklib.results as results

from .BaseTATest import BaseTATest

class TestGenesysCloudTA(BaseTATest):

    def setup_method(self, method):
        super(TestGenesysCloudTA, self).setup_method(method)

    def teardown_method(self, method):
        super(TestGenesysCloudTA, self).teardown_method(method)

    def _search(self, search_query: str, run_counter: int=0, timeout: int=40, sleep_interval: int=5) -> list:
        """
        Run search to verify data ingestion
        :param search_query: SPL to be executed
        :param run_counter: counter to keep track of retries and calculate timeout accordingly
        :param timeout: total seconds waited to get the response streamed back
        :param sleep_interval: inteval
        :return: list of events
        """
        hashes = []
        lst_results = []
        elapsed_time = 0
        kwargs = {
            "earliest_time": "0",
            "latest_time": "now",
            "output_mode": "json"
        }
        # +1min timeout each retry
        tot_timeout = timeout + (run_counter  * 60)

        while elapsed_time < tot_timeout:
            oneshot = self.splunk_client.jobs.export(search_query, **kwargs)
            reader = results.JSONResultsReader(oneshot)
            for result in reader:
                if not isinstance(result, dict):
                    # Diagnostic messages may be returned in the results
                    continue
                str_result = json.dumps(result["_raw"])
                md5_hash = hashlib.md5(str_result.encode()).hexdigest()
                if md5_hash not in hashes:
                    hashes.append(md5_hash)
                    lst_results.append(result)

            time.sleep(sleep_interval)
            elapsed_time += sleep_interval

        assert reader.is_preview == False
        self.logger.debug(f"_search() - Returning {len(lst_results)} results")
        return lst_results


    # @pytest.mark.skip(reason="already tested")
    def test_input_chat_observations(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:analytics:flows:metrics"
        source = "conversations_metrics://chat_observations"
        spl = f"search index={self.INDEX} sourcetype={sourcetype} source={source}"
        for attempt in range(self.RETRY):
            results = self._search(search_query=spl, run_counter=attempt)
            if len(results) > 0 or attempt == (self.RETRY - 1):
                self.logger.debug(f"Results {len(results)} and attempt: {attempt}")
                break
            time.sleep(2)
        assert len(results) > 0 and len(results) <= 60

    def test_input_conversations_details(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:analytics:conversations:details"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        for attempt in range(self.RETRY):
            results = self._search(search_query=spl, run_counter=attempt)
            if len(results) > 0 or attempt == (self.RETRY - 1):
                self.logger.debug(f"Results {len(results)} and attempt: {attempt}")
                break
            time.sleep(2)
        assert len(results) > 0 and len(results) <= 114
        assert results[0]["source"] == "conversations_details://conversations_details"

    def test_input_conversations_metrics(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:analytics:flows:metrics"
        source = "conversations_metrics://conversations_metrics"
        spl = f"search index={self.INDEX} sourcetype={sourcetype} source={source}"
        for attempt in range(self.RETRY):
            results = self._search(search_query=spl, run_counter=attempt)
            if len(results) > 0 or attempt == (self.RETRY - 1):
                self.logger.debug(f"Results {len(results)} and attempt: {attempt}")
                break
            time.sleep(2)
        assert len(results) > 0 and len(results) <= 55

    def test_input_user_routing_status(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:users:users:routingstatus"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        for attempt in range(self.RETRY):
            results = self._search(search_query=spl, run_counter=attempt, timeout=100)
            if len(results) > 0 or attempt == (self.RETRY - 1):
                self.logger.debug(f"Results {len(results)} and attempt: {attempt}")
                break
            time.sleep(2)
        assert len(results) > 0 and len(results) <= 358
        assert results[0]["source"] == "user_routing_status://user_routing_status"

    def test_input_edges_metrics(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:telephonyprovidersedge:edges:metrics"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        for attempt in range(self.RETRY):
            results = self._search(search_query=spl, run_counter=attempt, timeout=100)
            if len(results) > 0 or attempt == (self.RETRY - 1):
                self.logger.debug(f"Results {len(results)} and attempt: {attempt}")
                break
            time.sleep(2)

        # Each event is split into 2: status and secondary status
        assert len(results) > 0 and len(results) <= 157
        assert results[0]["source"] == "edges_metrics://edges_metrics"

    def test_input_edges_phones(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:telephonyprovidersedge:edges:phones"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"

        for attempt in range(self.RETRY):
            results = self._search(search_query=spl, run_counter=attempt)
            if len(results) > 0 or attempt == (self.RETRY - 1):
                self.logger.debug(f"Results {len(results)} and attempt: {attempt}")
                break
            time.sleep(2)

        # Each event is split into 2: status and secondary status
        assert len(results) > 0 and len(results) <= 2 * 25
        assert results[0]["source"] == "edges_phones://edges_phones"

    def test_input_edges_trunks_metrics(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:telephonyprovidersedge:trunks:metrics"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        for attempt in range(self.RETRY):
            results = self._search(search_query=spl, run_counter=attempt, timeout=100)
            if len(results) > 0 or attempt == (self.RETRY - 1):
                self.logger.debug(f"Results {len(results)} and attempt: {attempt}")
                break
            time.sleep(2)
        assert len(results) > 0 and len(results) <= 14
        assert results[0]["source"] == "edges_trunks_metrics://edges_trunks_metrics"

    def test_input_queue_observations(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:analytics:queues:observations"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        for attempt in range(self.RETRY):
            results = self._search(search_query=spl, run_counter=attempt, timeout=100)
            if len(results) > 0 or attempt == (self.RETRY - 1):
                self.logger.debug(f"Results {len(results)} and attempt: {attempt}")
                break
            time.sleep(2)

        assert len(results) > 0 and len(results) <= 4082
        assert results[0]["source"] == "queue_observations://queue_observations"

    def test_input_user_aggregates(self):
        """
        This test will check whether data was successfully indexed
        """
        sourcetype = "genesyscloud:users:users:aggregates"
        spl = f"search index={self.INDEX} sourcetype={sourcetype}"
        for attempt in range(self.RETRY):
            results = self._search(search_query=spl, run_counter=attempt)
            if len(results) > 0 or attempt == (self.RETRY - 1):
                self.logger.debug(f"Results {len(results)} and attempt: {attempt}")
                break
            time.sleep(2)
        assert len(results) > 0 and len(results) <= 716
        assert results[0]["source"] == "user_aggregates://user_aggregates"
