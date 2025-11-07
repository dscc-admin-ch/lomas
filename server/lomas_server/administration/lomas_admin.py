from pathlib import Path

from lomas_server.administration.keycloak_admin import (
    add_kc_user,
    add_kc_users_via_yaml,
    del_all_kc_users,
    del_kc_user,
)
from lomas_server.models.config import AdminConfig


def add_lomas_user(
    admin_config: AdminConfig, user_name: str, user_email: str, client_secret: str | None = None
) -> None:
    """Adds a user to the lomas application.

    Only adds a user to keycloak if the kc_config is not null.

    Args:
        admin_config (AdminConfig): The administration config.
        user_name (str): The name of the user.
        user_email (str): The email of the user.
        client_secret (str | None, optional):
            The client secret for the user in case one wants to specify it. Defaults to None.
    """
    admin_config.database.add_user(user_name, user_email)

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
        user_name (str): username to be added
        user_email (str): email to be added
        dataset (str): name of the dataset to add to user
        epsilon (float): epsilon value for initial budget of user
        delta (float): delta value for initial budget of user
        client_secret (str | None, optional):
            The client secret for the user in case one wants to specify it. Defaults to None.
    """
    admin_config.database.add_user(user_name, user_email, dataset, epsilon, delta)

    if admin_config.kc_config is not None:
        add_kc_user(admin_config.kc_config, user_name, user_email, client_secret)


def del_lomas_user(admin_config: AdminConfig, user_name: str) -> None:
    """Deletes the lomas user.

    Only removes the keycload user and client in keycloak if the kc_config is not null.

    Args:
        admin_config (AdminConfig): The adinistration config
        user_name (str): The name of the user to be deleted.
    """
    admin_config.database.del_user(user_name)

    if admin_config.kc_config is not None:
        del_kc_user(admin_config.kc_config, user_name)


def add_lomas_users_via_yaml(admin_config: AdminConfig, yaml_file: Path, clean: bool) -> None:
    """Add all users from a yaml file.

    Only adds the keycloak users if the kc_config is not None.

    Args:
        admin_config (AdminConfig): The administration config.
        yaml_file (Path): a path to the YAML file location
        clean (bool): boolean flag
            True if drop current user collection
            False if keep current user collection
    """
    admin_config.database.add_users_via_yaml(yaml_file, clean)

    if admin_config.kc_config is not None:
        # TODO: do we want to expose KC clean ?
        add_kc_users_via_yaml(admin_config.kc_config, yaml_file, clean=False, overwrite=True)


def drop_lomas_collection(admin_config: AdminConfig, collection: str) -> None:
    """Drops the given collection from the administration database.

    Only deletes all keycloak users and clients if the kc_config is not None
    and the collection to drop is "users"

    Args:
        admin_config (AdminConfig): _description_
        collection (str): The collection to drop.
    """
    admin_config.database.drop_collection(collection)

    if collection == "users" and admin_config.kc_config is not None:
        del_all_kc_users(admin_config.kc_config)
