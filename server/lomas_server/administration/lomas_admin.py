from typing import Dict

from lomas_core.models.config import AdminConfig
from lomas_server.administration.keycloak_admin import (
    add_kc_user,
    add_kc_users_via_yaml,
    del_all_kc_users,
    del_kc_user,
)
from lomas_server.administration.mongodb_admin import (
    add_user,
    add_user_with_budget,
    add_users_via_yaml,
    del_user,
    drop_collection,
)


def add_lomas_user(
    admin_config: AdminConfig, user_name: str, user_email: str, client_secret: str | None = None
):
    """Adds a user to the lomas application.

    Only adds a user to keycloak if the kc_config is not null.

    Args:
        admin_config (AdminConfig): The administration config.
        user_name (str): The name of the user.
        user_email (str): The email of the user.
        client_secret (str | NoneType, optional):
            The client secret for the user in case one wants to specify it. Defaults to None.
    """
    add_user(admin_config.mg_config, user_name, user_email)

    if admin_config.kc_config is not None:
        add_kc_user(admin_config.kc_config, user_name, user_email, client_secret)


def add_lomas_user_with_budget(
    admin_config: AdminConfig,
    user_name: str,
    user_email: str,
    dataset: str,
    epsilon: float,
    delta: float,
    client_secret: str | None = None,
) -> None:
    """Adds a new user with an associated budget for a given dataset.

    Only adds a user to keycloak if the kc_config is not null.

    Args:
        admin_config (AdminConfig): The administration config
        user (str): username to be added
        email (str): email to be added
        dataset (str): name of the dataset to add to user
        epsilon (float): epsilon value for initial budget of user
        delta (float): delta value for initial budget of user
    """
    add_user_with_budget(admin_config.mg_config, user_name, user_email, dataset, epsilon, delta)

    if admin_config.kc_config is not None:
        add_kc_user(admin_config.kc_config, user_name, user_email, client_secret)


def del_lomas_user(admin_config: AdminConfig, user_name: str) -> None:
    """Deletes the lomas user.

    Only removes the keycload user and client in keycloak if the kc_config is not null.

    Args:
        admin_config (AdminConfig): The adinistration config
        user_name (str): The name of the user to be deleted.
    """
    del_user(admin_config.mg_config, user_name)

    if admin_config.kc_config is not None:
        del_kc_user(admin_config.kc_config, user_name)


def add_lomas_users_via_yaml(
    admin_config: AdminConfig, yaml_file: str | Dict, clean: bool, overwrite: bool
) -> None:
    """Add all users from a yaml file.

    Only adds the keycloak users if the kc_config is not None.

    Args:
        admin_config (AdminConfig): The administration config.
        yaml_file (Union[str, Dict]):
            if str: a path to the YAML file location
            if Dict: a dictionnary containing the collection data
        clean (bool): boolean flag
            True if drop current user collection
            False if keep current user collection
        overwrite (bool): boolean flag
            True if overwrite already existing users
            False errors if new values for already existing users
    """
    add_users_via_yaml(admin_config.mg_config, yaml_file, clean, overwrite)

    if admin_config.kc_config is not None:
        add_kc_users_via_yaml(admin_config.kc_config, yaml_file, clean, overwrite)


def drop_lomas_collection(admin_config: AdminConfig, collection: str) -> None:
    """Drops the given collection from the administration database.

    Only deletes all keycloak users and clients if the kc_config is not None
    and the collection to drop is "users"

    Args:
        admin_config (AdminConfig): _description_
        collection (str): The collection to drop.
    """

    drop_collection(admin_config.mg_config, collection)

    if collection == "users" and admin_config.kc_config is not None:
        del_all_kc_users(admin_config.kc_config)
