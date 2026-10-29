from solnlib import conf_manager

ADDON_NAME = "genesys_cloud_ta"


def get_account_property(session_key: str, account_name: str, property_name: str):
    """Retrieve a specific property for a given Genesys Cloud account."""
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{ADDON_NAME}_account",
    )
    account_conf_file = cfm.get_conf("genesys_cloud_ta_account")
    return account_conf_file.get(account_name).get(property_name)
