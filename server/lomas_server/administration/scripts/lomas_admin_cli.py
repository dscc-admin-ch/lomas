import argparse
import os

from lomas_core.models.config import AdminConfig
from lomas_server.administration.lomas_admin import (
    add_lomas_user,
    add_lomas_user_with_budget,
    add_lomas_users_via_yaml,
    del_lomas_user,
    drop_lomas_collection,
)
from lomas_server.administration.mongodb_admin import (
    add_dataset,
    add_dataset_to_user,
    add_datasets_via_yaml,
    del_dataset,
    del_dataset_to_user,
    get_archives_of_user,
    get_collection,
    get_dataset,
    get_list_of_datasets,
    get_list_of_datasets_from_user,
    get_list_of_users,
    get_metadata_of_dataset,
    get_user,
    set_budget_field,
    set_may_query,
)


def add_kc_admin_args(arg_parser: argparse.ArgumentParser) -> None:
    """Adds all keycloak admin parameters to the argument parser.

    Args:
        arg_parser (argparse.ArgumentParser): The argument parser to add to.
    """
    arg_parser.add_argument("--kc_skip", default=bool(os.getenv("lomas_kc_skip", "False")), type=bool)
    arg_parser.add_argument("-kc_a", "--kc_address", default=os.getenv("lomas_kc_addr", "keycloak"), type=str)
    arg_parser.add_argument("-kc_p", "--kc_port", default=int(os.getenv("lomas_kc_port", "8080")), type=int)
    arg_parser.add_argument("-kc_r", "--kc_realm", default=os.getenv("lomas_kc_realm", "lomas"), type=str)
    arg_parser.add_argument(
        "-kc_cl", "--kc_client_id", default=os.getenv("lomas_kc_client_id", "lomas_admin"), type=str
    )
    arg_parser.add_argument(
        "-kc_s", "--kc_client_secret", default=os.getenv("lomas_kc_client_secret", "lomas_admin"), type=str
    )
    arg_parser.add_argument(
        "-kc_tls", "--kc_use_tls", default=bool(os.getenv("lomas_kc_use_tls", "True")), type=bool
    )


if __name__ == "__main__":

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--env_file", required=False, default="lomas_admin.env")

    ########################################################################
    ######################## MongoDB Administration ############ # noqa: E266
    ########################################################################
    parser = argparse.ArgumentParser(description="MongoDB administration script for the database")
    subparsers = parser.add_subparsers(title="subcommands", help="user database administration operations")

    ##########################  USERS  ########################## # noqa: E266
    # Create the parser for the "add_user" command
    add_user_parser = subparsers.add_parser(
        "add_user",
        help="add user to users collection",
        parents=[parent_parser],
    )
    add_user_parser.add_argument("-u", "--user", required=True, type=str)
    add_user_parser.add_argument("-m", "--email", required=True, type=str)
    add_user_parser.add_argument("-s", "--client_secret", required=False, type=str, default=None)

    # Create the parser for the "add_user_with_budget" command
    add_user_wb_parser = subparsers.add_parser(
        "add_user_with_budget",
        help="add user with budget to users collection",
        parents=[parent_parser],
    )
    add_user_wb_parser.add_argument("-u", "--user", required=True, type=str)
    add_user_wb_parser.add_argument("-m", "--email", required=True, type=str)
    add_user_wb_parser.add_argument("-s", "--client_secret", required=False, type=str, default=None)
    add_user_wb_parser.add_argument("-d", "--dataset", required=True, type=str)
    add_user_wb_parser.add_argument("-e", "--epsilon", required=True, type=float)
    add_user_wb_parser.add_argument("-del", "--delta", required=True, type=float)

    # Create the parser for the "del_user" command
    del_user_parser = subparsers.add_parser(
        "del_user",
        help="delete user from users collection",
        parents=[parent_parser],
    )
    del_user_parser.add_argument("-u", "--user", required=True, type=str)

    # Create the parser for the "add_dataset" command
    add_dataset_to_user_parser = subparsers.add_parser(
        "add_dataset_to_user",
        help="add dataset with initialized budget values for a user",
        parents=[parent_parser],
    )
    add_dataset_to_user_parser.add_argument("-u", "--user", required=True, type=str)
    add_dataset_to_user_parser.add_argument("-d", "--dataset", required=True, type=str)
    add_dataset_to_user_parser.add_argument("-e", "--epsilon", required=True, type=float)
    add_dataset_to_user_parser.add_argument("-del", "--delta", required=True, type=float)

    # Create the parser for the "del_dataset" command
    del_dataset_to_user_parser = subparsers.add_parser(
        "del_dataset_to_user",
        help="delete dataset for user in users collection",
        parents=[parent_parser],
    )
    del_dataset_to_user_parser.add_argument("-u", "--user", required=True, type=str)
    del_dataset_to_user_parser.add_argument("-d", "--dataset", required=True, type=str)

    # Create the parser for the "set_budget_field" command
    set_budget_field_parser = subparsers.add_parser(
        "set_budget_field",
        help="set budget field to given value for given user and dataset",
        parents=[parent_parser],
    )
    set_budget_field_parser.add_argument("-u", "--user", required=True, type=str)
    set_budget_field_parser.add_argument("-d", "--dataset", required=True, type=str)
    set_budget_field_parser.add_argument(
        "-f",
        "--field",
        required=True,
        choices=["initial_epsilon", "initial_delta"],
    )
    set_budget_field_parser.add_argument("-v", "--value", required=True, type=float)

    # Create the parser for the "set_may_query" command
    set_may_query_parser = subparsers.add_parser(
        "set_may_query",
        help="set may query field to given value for given user",
        parents=[parent_parser],
    )
    set_may_query_parser.add_argument("-u", "--user", required=True, type=str)
    set_may_query_parser.add_argument("-v", "--value", required=True, choices=["False", "True"])

    # Show the user
    get_user_parser = subparsers.add_parser(
        "get_user",
        help="show all metadata of user",
        parents=[parent_parser],
    )
    get_user_parser.add_argument("-u", "--user", required=True, type=str)

    # Create the parser for the "create_example_users" command
    users_collection_from_yaml_parser = subparsers.add_parser(
        "add_users_via_yaml",
        help="create users collection from yaml file",
        parents=[parent_parser],
    )
    users_collection_from_yaml_parser.add_argument(
        "-c",
        "--clean",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    users_collection_from_yaml_parser.add_argument(
        "-o",
        "--overwrite",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    users_collection_from_yaml_parser.add_argument("-yf", "--yaml_file", required=True, type=str)

    # Function: Show Archives of User
    get_archives_parser = subparsers.add_parser(
        "get_archives_of_user",
        help="show all previous queries from a user",
        parents=[parent_parser],
    )
    get_archives_parser.add_argument(
        "-u",
        "--user",
        required=True,
        type=str,
        help="username of the user to show archives",
    )

    # Function: Get List of Users
    get_users_parser = subparsers.add_parser(
        "get_list_of_users",
        help="get the list of all users in 'users' collection",
        parents=[parent_parser],
    )

    # Function: Get List of Datasets from User
    get_user_datasets_parser = subparsers.add_parser(
        "get_list_of_datasets_from_user",
        help="get the list of all datasets from a user",
        parents=[parent_parser],
    )
    get_user_datasets_parser.add_argument(
        "-u",
        "--user",
        required=True,
        type=str,
        help="username of the user to show datasets",
    )

    #######################  DATASETS  ####################### # noqa: E266
    # Create parser for dataset private database
    add_dataset_parser = subparsers.add_parser(
        "add_dataset",
        help="set in which database the dataset is stored",
        parents=[parent_parser],
    )
    # Dataset location
    add_dataset_parser.add_argument("-d", "--dataset_name", required=True)
    add_dataset_parser.add_argument("-db", "--database_type", required=True)
    add_dataset_parser.add_argument("-d_path", "--dataset_path", required=False)
    add_dataset_parser.add_argument("-s3b", "--bucket", required=False)
    add_dataset_parser.add_argument("-s3k", "--key", required=False)
    add_dataset_parser.add_argument("-s3_url", "--endpoint_url", required=False)
    add_dataset_parser.add_argument("-cred_n", "--credentials_name", required=False)
    # Metadata location
    add_dataset_parser.add_argument("-m_db", "--metadata_database_type", required=True)
    add_dataset_parser.add_argument("-mp", "--metadata_path", required=False)
    add_dataset_parser.add_argument("-m_s3b", "--metadata_bucket", required=False)
    add_dataset_parser.add_argument("-m_s3k", "--metadata_key", required=False)
    add_dataset_parser.add_argument("-m_s3_url", "--metadata_endpoint_url", required=False)
    add_dataset_parser.add_argument("-m_s3_ak", "--metadata_access_key_id", required=False)
    add_dataset_parser.add_argument("-m_s3_sak", "--metadata_secret_access_key", required=False)
    add_dataset_parser.add_argument("-m_cred_n", "--metadata_credentials_name", required=False)

    # Create the parser for the "add_datasets_via_yaml" command
    add_datasets_via_yaml_parser = subparsers.add_parser(
        "add_datasets_via_yaml",
        help="create dataset to database type collection",
        parents=[parent_parser],
    )
    add_datasets_via_yaml_parser.add_argument("-yf", "--yaml_file", required=True, type=str)
    add_datasets_via_yaml_parser.add_argument(
        "-c",
        "--clean",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    add_datasets_via_yaml_parser.add_argument(
        "-od",
        "--overwrite_datasets",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )
    add_datasets_via_yaml_parser.add_argument(
        "-om",
        "--overwrite_metadata",
        required=False,
        action="store_const",
        const=True,
        default=False,
    )

    # Create the parser for the "del_dataset" command
    del_dataset_parser = subparsers.add_parser(
        "del_dataset",
        help="delete dataset and metadata from " "datasets and metadata collection",
        parents=[parent_parser],
    )
    del_dataset_parser.add_argument("-d", "--dataset", required=True, type=str)

    # Function: Show Dataset
    get_dataset_parser = subparsers.add_parser(
        "get_dataset",
        help="show a dataset from the dataset collection",
        parents=[parent_parser],
    )
    get_dataset_parser.add_argument(
        "-d",
        "--dataset",
        required=True,
        type=str,
        help="name of the dataset to show",
    )

    # Function: Show Metadata of Dataset
    get_metadata_parser = subparsers.add_parser(
        "get_metadata_of_dataset",
        help="show metadata from the metadata collection",
        parents=[parent_parser],
    )
    get_metadata_parser.add_argument(
        "-d",
        "--dataset",
        required=True,
        type=str,
        help="name of the dataset of the metadata to show",
    )

    # Function: Get List of Datasets
    get_datasets_parser = subparsers.add_parser(
        "get_list_of_datasets",
        help="get the list of all datasets in 'datasets' collection",
        parents=[parent_parser],
    )

    #######################  COLLECTIONS  ####################### # noqa: E266
    # Create the parser for the "drop_collection" command
    drop_collection_parser = subparsers.add_parser(
        "drop_collection",
        help="delete collection from database",
        parents=[parent_parser],
    )
    drop_collection_parser.add_argument(
        "-c",
        "--collection",
        required=True,
        choices=["users", "datasets", "metadata", "queries_archives"],
    )

    # Create the parser for the "get_users_collection" command
    get_collection_parser = subparsers.add_parser(
        "get_collection",
        help="print a collection",
        parents=[parent_parser],
    )
    get_collection_parser.add_argument(
        "-c",
        "--collection",
        required=True,
        choices=["users", "datasets", "metadata", "queries_archives"],
    )

    args = parser.parse_args()

    #######################  FUNCTION CALL  ###################### # noqa: E266

    admin_config = AdminConfig(_env_file=args.env_file)

    function_map = {
        "add_user": lambda args: add_lomas_user(admin_config, args.user, args.email, args.client_secret),
        "add_user_with_budget": lambda args: add_lomas_user_with_budget(
            admin_config, args.user, args.email, args.dataset, args.epsilon, args.delta
        ),
        "del_user": lambda args: del_lomas_user(admin_config, args.user),
        "add_dataset_to_user": lambda args: add_dataset_to_user(
            admin_config.mongo_config, args.user, args.dataset, args.epsilon, args.delta
        ),
        "del_dataset_to_user": lambda args: del_dataset_to_user(
            admin_config.mongo_config, args.user, args.dataset
        ),
        "set_budget_field": lambda args: set_budget_field(
            admin_config.mongo_config, args.user, args.dataset, args.field, args.value
        ),
        "set_may_query": lambda args: set_may_query(admin_config.mongo_config, args.user, args.value),
        "get_user": lambda args: get_user(admin_config.mongo_config, args.user),
        "add_users_via_yaml": lambda args: add_lomas_users_via_yaml(
            admin_config, args.yaml_file, args.clean, args.overwrite
        ),
        "get_archives_of_user": lambda args: get_archives_of_user(admin_config.mongo_config, args.user),
        "get_list_of_users": lambda args: get_list_of_users(admin_config.mongo_config),
        "get_list_of_datasets_from_user": lambda args: get_list_of_datasets_from_user(
            admin_config.mongo_config, args.user
        ),
        "add_dataset": lambda args: add_dataset(
            admin_config.mongo_config,
            args.dataset_name,
            args.database_type,
            args.metadata_database_type,
            args.dataset_path,
            args.metadata_path,
            args.bucket,
            args.key,
            args.endpoint_url,
            args.credentials_name,
            args.metadata_bucket,
            args.metadata_key,
            args.metadata_endpoint_url,
            args.metadata_access_key_id,
            args.metadata_secret_access_key,
            args.metadata_credentials_name,
        ),
        "add_datasets_via_yaml": lambda args: add_datasets_via_yaml(
            admin_config.mongo_config,
            args.yaml_file,
            args.clean,
            args.overwrite_datasets,
            args.overwrite_metadata,
        ),
        "del_dataset": lambda args: del_dataset(admin_config.mongo_config, args.dataset),
        "get_dataset": lambda args: get_dataset(admin_config.mongo_config, args.dataset),
        "get_metadata_of_dataset": lambda args: get_metadata_of_dataset(
            admin_config.mongo_config, args.dataset
        ),
        "get_list_of_datasets": lambda args: get_list_of_datasets(admin_config.mongo_config),
        "drop_collection": lambda args: drop_lomas_collection(admin_config, args.collection),
        "get_collection": lambda args: get_collection(admin_config.mongo_config, args.collection),
    }
    function_map[args.func.__name__](args)
