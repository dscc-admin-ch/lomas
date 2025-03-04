import logging

import yaml
from mantelo import HttpException, KeycloakAdmin

from lomas_core.models.collections import UserCollection
from lomas_core.models.config import KeycloakClientConfig


def get_kc_admin(kc_config: KeycloakClientConfig) -> KeycloakAdmin:
    """Builds the Keycloak Admin from the provided config.

    Args:
        kc_config (KeycloakClientConfig): A KeycloakClientConfig

    Returns:
        KeycloakAdmin: The built keycloak admin instance.
    """
    url_protocol = "https" if kc_config.use_tls else "http"

    kc_admin = KeycloakAdmin.from_client_credentials(
        server_url=f"{url_protocol}://{kc_config.address}:{kc_config.port}",
        realm_name=kc_config.realm,
        client_id=kc_config.client_id,
        client_secret=kc_config.client_secret,
        authentication_realm_name=kc_config.realm,
    )

    return kc_admin


def add_kc_user(
    kc_config: KeycloakClientConfig, user_name: str, user_email: str, client_secret: str | None = None
) -> None:
    """Adds a new lomas user to keycloak.

    Also creates corresponding client with same email attribute for authenticating
    when using the lomas library.

    Args:
        kc_config (KeycloakClientConfig): A KeycloakClientConfig
        user_name (str): The name of the user to add.
        user_email (str): The email of the user to add.
        client_secret (str | None): Optional, the client secret for authenticating with the
            lomas client library.

    Raises:
        HTTPException: If any of the calls to keycloak fails
    """
    kc_admin = get_kc_admin(kc_config)

    try:
        # TODO remove this? or update when federation is activated. see issue #408
        kc_admin.users.post({"username": user_name, "email": user_email, "enabled": True})

        # Create client for user
        client_dict = {
            "clientId": user_name,
            "name": user_name,
            "clientAuthenticatorType": "client-secret",
            "standardFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": True,
            "publicClient": False,
            "protocol": "openid-connect",
            "defaultClientScopes": [],
            "optionalClientScopes": [],
            "attributes": {
                "lomas_user_client": True  # flag to indicate this client is linked to a lomas user.
            },
        }

        if client_secret is not None:
            client_dict["secret"] = client_secret

        kc_admin.clients.post(client_dict)

        # Add attributes to linked service account user
        user_client_uid = kc_admin.clients.get(clientId=user_name)[0]["id"]  # type: ignore
        user_service_account_uid = kc_admin.clients(user_client_uid).service_account_user.get()[
            "id"  # type: ignore
        ]

        kc_admin.users(user_service_account_uid).put(
            {
                # "email": user_email, -> We do not set this to avoid conflicts with user created above.
                "attributes": {
                    "lomas_user_client": True,  # flag to indicate this client is linked to a lomas user.
                    "user_name": user_name,
                    "user_email": user_email,
                }
            }
        )

        # Map attributes into OIDC claims
        kc_admin.clients(user_client_uid).protocol_mappers.models.post(
            {
                "name": "user_attribute_user_email",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-attribute-mapper",
                "config": {
                    "user.attribute": "user_email",
                    "claim.name": "user_email",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true",
                },
            }
        )
        kc_admin.clients(user_client_uid).protocol_mappers.models.post(
            {
                "name": "user_attribute_user_name",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-attribute-mapper",
                "config": {
                    "user.attribute": "user_name",
                    "claim.name": "user_name",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true",
                },
            }
        )

        logging.info(f"Added keycloak user {user_name} and associated client.\n")

    except HttpException as e:
        raise RuntimeError("Could not add user to keycloak. Please contact the service administrator.") from e


def del_kc_user(kc_config: KeycloakClientConfig, user: str) -> None:
    """Removes the keycloak user and client associated to the user name.

    Args:
        kc_config (KeycloakClientConfig): A KeycloakClientConfig
        user (str): The name of the user to remove.

    Raises:
        HTTPException: If any of the calls to keycloak fails
    """
    kc_admin = get_kc_admin(kc_config)

    # Delete user
    user_id = kc_admin.users.get(username=user)[0]["id"]  # type: ignore
    kc_admin.users(user_id).delete()
    # Delete client
    user_client_uid = kc_admin.clients.get(clientId=user)[0]["id"]  # type: ignore
    kc_admin.clients(user_client_uid).delete()

    logging.info(f"Deleted keycloak user {user} and associated client.\n")


def del_all_kc_users(kc_config: KeycloakClientConfig) -> None:
    """Removes all keycloak users and clients associated to lomas users.

    Args:
        kc_config (KeycloakClientConfig): A KeycloakClientConfig

    Raises:
        HTTPException: If any of the calls to keycloak fails
    """
    kc_admin = get_kc_admin(kc_config)

    users = kc_admin.users.get()
    for user in users:
        user_id = user["id"]  # type: ignore
        kc_admin.users(user_id).delete()

    logging.info("Removed all keycloak users. \n")

    clients = kc_admin.clients.get()
    for client in clients:
        if (
            "lomas_user_client" in client["attributes"]  # type: ignore
            and client["attributes"]["lomas_user_client"]  # type: ignore
        ):
            client_id = client["id"]  # type: ignore
            kc_admin.clients(client_id).delete()

    logging.info("Removed all keycloak clients associated to users. \n")


def add_kc_users_via_yaml(
    kc_config: KeycloakClientConfig, yaml_file: str | dict, clean: bool, overwrite: bool
) -> None:
    """Adds new lomas users to keycloak.

    Also creates corresponding clients with same email attribute for authenticating
    when using the lomas library.

    Args:
        kc_config (KeycloakClientConfig): A KeycloakClientConfig
        yaml_file (str, dict): File name to load the users from if a string.
            Otherwise dict representing a UserCollection.
        clean (bool): Whether to remove existing users and start with a clean state.
        overwrite(bool): Whether to overwrite existing users.

    Raises:
        HTTPException: If any of the calls to keycloak fails
    """
    kc_admin = get_kc_admin(kc_config)

    # Remove all existing users if asked to do so
    if clean:
        del_all_kc_users(kc_config)

    # Load yaml data and insert it
    if isinstance(yaml_file, str):
        with open(yaml_file, encoding="utf-8") as f:
            raw_dict: dict = yaml.safe_load(f)
    else:
        raw_dict = yaml_file
    user_list = UserCollection(**raw_dict)

    for user in user_list.users:
        # Remove user with same name if it already exists.
        if overwrite and not clean:
            kc_users = kc_admin.users.get(username=user.id.name)
            for kc_user in kc_users:
                kc_user_id = kc_user["id"]  # type: ignore
                kc_admin.users(kc_user_id).delete()

            kc_clients = kc_admin.clients.get(userId=user.id.name)
            for kc_client in kc_clients:
                if (
                    "lomas_user_client" in kc_client["attributes"]  # type: ignore
                    and kc_client["attributes"]["lomas_user_client"]  # type: ignore
                ):  # type: ignore
                    kc_client_id = kc_client["id"]  # type: ignore
                    kc_admin.clients(kc_client_id).delete()

            logging.info(f"Overwriting user {user.id.name}. \n")

        add_kc_user(kc_config, user.id.name, user.id.email, user.id.client_secret)

    logging.info("Added keycloak users from yaml file.")


def get_kc_user_client_secret(kc_config: KeycloakClientConfig, user_name: str) -> str:
    """Gets the client secret for making api calls with the client library for a given user.

    Args:
        kc_config (KeycloakClientConfig): A KeycloakClientConfig
        user_name (str): The user name.

    Returns:
        str: The requested client secret
    """
    kc_admin = get_kc_admin(kc_config)

    user_client_uid = kc_admin.clients.get(clientId=user_name)[0]["id"]  # type: ignore
    user_client_secret: str = kc_admin.clients(user_client_uid).client_secret.get()["value"]  # type: ignore

    logging.info(f"Accessing keycloak user client secret for user {user_name}.\n")

    return user_client_secret


def set_kc_user_client_secret(
    kc_config: KeycloakClientConfig, user_name: str, client_secret: str | None = None
) -> None:
    """Sets a (new) client secret for making api calls with the client libary for a given user.

    Args:
        kc_config (KeycloakClientConfig): A KeycloakClientConfig
        user_name (str): The user name.
        client_secret (str | None): The client secret. If None, secret is automatically generated by Keycloak.
    """
    kc_admin = get_kc_admin(kc_config)
    user_client_uid = kc_admin.clients.get(clientId=user_name)[0]["id"]  # type: ignore

    # Make Keycloak set it if it is None
    if client_secret is None:
        kc_admin.clients(user_client_uid).client_secret.post({"type": "secret"})
    else:
        client_dict = {"clientId": user_name, "secret": client_secret}

        kc_admin.clients(user_client_uid).put(client_dict)

    logging.info(f"Set new secret for client associated to user {user_name}.")
