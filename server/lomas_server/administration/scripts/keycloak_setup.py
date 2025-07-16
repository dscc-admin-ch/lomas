import logging
import os

from mantelo import HttpException, KeycloakAdmin
from pydantic import Field, HttpUrl, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Config model for keycloak setup script."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="lomas_kc_setup_",
        env_file=".env.lomas_kc_setup",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    keycloak_url: HttpUrl
    keycloak_authentication_realm: str
    keycloak_admin_client_id: str
    keycloak_admin_user: str
    keycloak_admin_pwd: str

    lomas_realm: str = "lomas"

    lomas_gateway_url: HttpUrl
    lomas_gateway_client_id: str = "lomas_oauth_proxy"
    lomas_gateway_client_secret: str

    lomas_admin_client_id: str = "lomas_admin"
    lomas_admin_client_secret: str

    lomas_api_client_id: str = "lomas_api"
    lomas_api_client_secret: str

    overwrite_realm: bool = Field(default=True)

    @computed_field
    def keycloak_use_tls(self) -> bool:
        """Using TLS ?"""
        return self.keycloak_url.scheme == "https"


def get_admin_session(config: Config) -> KeycloakAdmin:
    """Returns a keycloak admin session using the.

    Args:
        config (Config): The config to create the connection.

    Returns:
        KeycloakAdmin: KeycloakAdmin session.
    """

    return KeycloakAdmin.from_username_password(
        server_url=config.keycloak_url,
        realm_name=config.keycloak_authentication_realm,
        client_id=config.keycloak_admin_client_id,
        username=config.keycloak_admin_user,
        password=config.keycloak_admin_pwd,
        authentication_realm_name=config.keycloak_authentication_realm,
    )


def create_realm(config: Config, kc_admin: KeycloakAdmin) -> None:
    """Creates the application realm if it does not already exist.

    This removes any existing realms with the same name if they already exist!

    This does not reset the application realm!

    Args:
        config (Config): Config for creating the realm.
        kc_admin (KeycloakAdmin): A KeycloakAdmin session.
    """
    try:
        kc_admin.realms.post({"realm": config.lomas_realm, "enabled": True})
        logging.info("Created application realm")
    except HttpException as e:
        if e.status_code == 409 and "Conflict detected" in e.json["errorMessage"]:
            logging.info("Application realm already exists.")
            if config.overwrite_realm:
                kc_admin.realms(config.lomas_realm).delete()
                kc_admin.realms.post({"realm": config.lomas_realm, "enabled": True})
                logging.info("Replaced existing with new application realm.")


def create_lomas_clients(config: Config, kc_admin: KeycloakAdmin) -> None:
    """Creates clients for the lomas application:

        - lomas_admin
        - lomas_api

    Args:
        config (Config): Config for creating the clients.
        kc_admin (KeycloakAdmin): A KeycloakAdmin session.
    """

    create_confidential_client(
        kc_admin,
        config.lomas_admin_client_id,
        config.lomas_admin_client_secret,
        {"realm-management": ["manage-users", "manage-clients"]},
    )
    create_confidential_client(kc_admin, config.lomas_api_client_id, config.lomas_api_client_secret)

    create_gateway_client(
        kc_admin, config.lomas_gateway_client_id, config.lomas_gateway_client_secret, config.lomas_gateway_url
    )


def create_confidential_client(
    kc_admin: KeycloakAdmin, client_id: str, client_secret: str, roles: dict[str, list[str]] = {}
) -> None:
    """Creates a confidential client with an associated service account.

    Allows only for the client credentials flow and assigns the roles
    listed in the provided dictionary.

    Only creates the account if it does not already exist.

    Args:
        kc_admin (KeycloakAdmin): A KeycloakAdmin session.
        client_id (str): The client id to use.
        client_secret (str): The client secret to use.
        roles (Dict[str, List[str]]): A dictionary mapping of (realm, list of roles) pairs
            to assign to the associated service account.
    """
    # Create client
    kc_admin.clients.post(
        {
            "clientId": client_id,
            "secret": client_secret,
            "name": "test_client",
            "clientAuthenticatorType": "client-secret",
            "standardFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": True,
            "publicClient": False,
            "protocol": "openid-connect",
            "defaultClientScopes": [],
            "optionalClientScopes": [],
        }
    )

    # Fetch service account uid
    lomas_admin_uid = kc_admin.clients.get(clientId="lomas_admin")[0]["id"]
    lomas_admin_service_account_uid = kc_admin.clients(lomas_admin_uid).service_account_user.get()["id"]

    for client, roles_list in roles.items():
        # Fetch realm management and manage-clients role uids
        client_uid = kc_admin.clients.get(clientId=client)[0]["id"]

        # Create role config for user and client combination
        roles_to_add = []
        for role in roles_list:
            role_uid = kc_admin.clients(client_uid).roles(role).get()["id"]
            roles_to_add.append({"id": role_uid, "name": role})

        kc_admin.users(lomas_admin_service_account_uid).role_mappings.clients(client_uid).post(roles_to_add)

    logging.info("Created new confidential client.")


def create_gateway_client(
    kc_admin: KeycloakAdmin, client_id: str, client_secret: str, gateway_hostname: HttpUrl
) -> None:
    """Create a confidential client for the gateway.

    This client will handle auth of the admin users to the various dashboards.

    Args:
        kc_admin (KeycloakAdmin): The KeycloakAdmin instance.
        client_id (str): The client id.
        client_secret (str): The client secret.
        gateway_hostname (HttpUrl): The hostname (url) of the gateway.
    """
    kc_admin.clients.post(
        {
            "clientId": client_id,
            "secret": client_secret,
            "name": client_id,
            "rootUrl": str(gateway_hostname),
            "clientAuthenticatorType": "client-secret",
            "redirectUris": ["/oauth2/callback"],
            "webOrigins": ["/*"],
            "standardFlowEnabled": True,
            "implicitFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": False,
            "publicClient": False,
            "frontchannelLogout": True,
            "protocol": "openid-connect",
            "attributes": {
                "realm_client": "false",
                "oidc.ciba.grant.enabled": "false",
                "backchannel.logout.session.required": "true",
                "frontchannel.logout.session.required": "true",
                "display.on.consent.screen": "false",
                "oauth2.device.authorization.grant.enabled": "false",
                "backchannel.logout.revoke.offline.tokens": "false",
            },
            "fullScopeAllowed": True,
            "protocolMappers": [
                {
                    "name": "aud-mapper",
                    "protocol": "openid-connect",
                    "protocolMapper": "oidc-audience-mapper",
                    "consentRequired": False,
                    "config": {
                        "id.token.claim": "true",
                        "lightweight.claim": "false",
                        "access.token.claim": "true",
                        "introspection.token.claim": "true",
                    },
                }
            ],
        }
    )

    logging.info("Created client for lomas gateway.")


def kc_setup() -> None:
    """Lomas keycloak setup script."""
    # Load config and get admin session
    config = Config()
    if not config.keycloak_use_tls:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    kc_admin = get_admin_session(config)

    # 1. Create realm
    create_realm(config, kc_admin)

    # Switch realm
    kc_admin.realm_name = config.lomas_realm

    # 2. Create clients
    create_lomas_clients(config, kc_admin)


if __name__ == "__main__":
    logging.basicConfig()
    logging.root.setLevel(logging.DEBUG)

    kc_setup()
