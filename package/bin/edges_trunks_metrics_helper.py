"""Edges Trunks Metrics input handler."""

import json
from datetime import datetime, timezone

from genesys_cloud_ta.account import get_account_property
from genesys_cloud_ta.api.client import GenesysCloudClient
from genesys_cloud_ta.api.proxy import get_proxy_configuration
from genesys_cloud_ta.constants import (
    ADDON_NAME,
    SOURCETYPE_TELEPHONYPE_TRUNKS_METRICS,
)
from genesys_cloud_ta.models import TrunkModel
from genesys_cloud_ta.time_utils import get_start_date
from genesys_cloud_ta.utils import (
    configure_logger,
    logger_for_input,
)
from solnlib import log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi


def validate_input(definition: smi.ValidationDefinition):
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            configure_logger(logger, session_key)
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "edges_trunks_metrics_checkpointer",
                session_key,
                ADDON_NAME,
            )
            proxy_config = get_proxy_configuration(logger, session_key)
            if proxy_config is None:
                continue

            log.modular_input_start(logger, normalized_input_name)

            account_region = get_account_property(
                session_key, input_item.get("account"), "region"
            )
            client_id = get_account_property(
                session_key, input_item.get("account"), "client_id"
            )
            client_secret = get_account_property(
                session_key, input_item.get("account"), "client_secret"
            )
            # aws_region = input_item.get('region')

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_config
            )

            # Setting a default start date of 7 days ago from now
            now = datetime.now(timezone.utc)
            checkpointer_key_name = normalized_input_name
            current_checkpoint = kvstore_checkpointer.get(checkpointer_key_name)
            start_date_epoch = get_start_date(current_checkpoint, now).timestamp()

            t_model = TrunkModel(
                client.get(
                    "TelephonyProvidersEdgeApi", "get_telephony_providers_edges_trunks"
                )
            )

            # Max 100 trunkids supported
            metrics = []
            cnt = 0
            has_more = True
            while has_more:
                trunk_ids, has_more = t_model.get_trunk_ids(cnt)
                if trunk_ids:
                    data = client.get(
                        "TelephonyProvidersEdgeApi",
                        "get_telephony_providers_edges_trunks_metrics",
                        ",".join(trunk_ids),
                    )
                    metrics.extend(data)
                else:
                    logger.info(
                        f"{trunk_ids} trunk Ids found. Cannot fetch metrics. Skipping."
                    )
                cnt += 1
            logger.debug(f"Fetched '{len(metrics)}' metrics")

            event_counter = 0
            for metric_obj in metrics:
                event_time_epoch = metric_obj.event_time.timestamp()
                metric = metric_obj.to_dict()
                metric["event_time"] = t_model.to_string(metric_obj.event_time)
                try:
                    metric["trunk"] = t_model.get_trunk(metric_obj.trunk.id)
                except ValueError as ve:
                    logger.warning(
                        f"Could not get trunk information - {ve}. Skipping it."
                    )
                    metric["trunk"] = {}
                if event_time_epoch > start_date_epoch:
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(metric, ensure_ascii=False, default=str),
                            index=input_item.get("index"),
                            sourcetype=SOURCETYPE_TELEPHONYPE_TRUNKS_METRICS,
                        )
                    )
                    event_counter += 1

            # Updating checkpoint if data was indexed to avoid losing info
            if event_counter > 0:
                logger.debug(f"Indexed '{event_counter}' events")
                new_checkpoint = now.timestamp()
                logger.debug(f"Updating checkpointer to {new_checkpoint}")
                kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_TELEPHONYPE_TRUNKS_METRICS,
                event_counter,
                input_item.get("index"),
                account=input_item.get("account"),
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:  # noqa: BLE001
            log.log_exception(
                logger,
                e,
                "IngestionError",
                msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}",
            )
