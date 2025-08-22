import json
import sys

from bson import json_util
from gridfs import GridFS
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from pymongo import MongoClient, ReturnDocument, WriteConcern
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, WriteConcernError
from pymongo.results import _WriteResult

from lomas_core.error_handler import InternalServerException, InvalidQueryException
from lomas_core.models.collections import DSInfo, Metadata
from lomas_core.models.requests import LomasRequestModel
from lomas_core.models.responses import QueryResponse
from lomas_server.admin_database.admin_database import (
    AdminDatabase,
    dataset_must_exist,
    user_must_exist,
    user_must_have_access_to_dataset,
)
from lomas_server.admin_database.constants import MAX_BSON_SIZE, WRITE_CONCERN_LEVEL, BudgetDBKey
from lomas_server.models.config import MongoDBConfig
from lomas_server.utils.metrics import (
    MONGO_ERROR_COUNTER,
    MONGO_INSERT_COUNTER,
    MONGO_QUERY_COUNTER,
    MONGO_UPDATE_COUNTER,
)


def get_mongodb(mongo_config: MongoDBConfig) -> Database:
    """Get MongoClient of the administration MongoDB.

    Args:
        config (MongoDBConfig): An instance of MongoDBConfig.

    Returns:
        MongoDBConfig: A client object directly

    Raises:
        InternalServerException: If the connection to the MongoDB failed.
    """

    db = MongoClient(mongo_config.url_with_options)[mongo_config.db_name]

    try:
        # Verify connection to database is possible (credentials verification included)
        db.list_collection_names()
    except ConnectionFailure as e:
        raise InternalServerException("Connection to MongoDB failed.") from e

    return db


class AdminMongoDatabase(AdminDatabase):
    """Overall MongoDB database management for server state."""

    def __init__(self, config: MongoDBConfig) -> None:
        """Connect to database.

        Args:
            connection_string (str): Connection string to the mongodb
            database_name (str): Mongodb database name.
        """
        PymongoInstrumentor().instrument()
        self.db: Database = get_mongodb(config)
        self.fs = GridFS(self.db)

    def does_user_exist(self, user_name: str) -> bool:
        """Checks if user exist in the database.

        Args:
            user_name (str): name of the user to check

        Returns:
            bool: True if the user exists, False otherwise.
        """
        MONGO_QUERY_COUNTER.add(1, {"operation": "does_user_exist"})
        doc_count = self.db.users.count_documents({"id.name": user_name})
        return doc_count > 0

    def does_dataset_exist(self, dataset_name: str) -> bool:
        """Checks if dataset exist in the database.

        Args:
            dataset_name (str): name of the dataset to check

        Returns:
            bool: True if the dataset exists, False otherwise.
        """
        MONGO_QUERY_COUNTER.add(1, {"operation": "does_dataset_exist"})
        collection_query = self.db.datasets.find({})
        for document in collection_query:
            if document["dataset_name"] == dataset_name:
                return True

        return False

    @dataset_must_exist
    def get_dataset_metadata(self, dataset_name: str) -> Metadata:
        """Returns the metadata dictionnary of the dataset.

        Wrapped by :py:func:`dataset_must_exist`.

        Args:
            dataset_name (str): name of the dataset to get the metadata

        Returns:
            Metadata: The metadata model.
        """
        MONGO_QUERY_COUNTER.add(1, {"operation": "get_dataset_metadata"})
        metadatas = self.db.metadata.find_one({dataset_name: {"$exists": True}})
        return Metadata.model_validate(metadatas[dataset_name])

    @user_must_exist
    def set_may_user_query(self, user_name: str, may_query: bool) -> None:
        """Sets if a user may query the server.

        (Set False before querying and True after updating budget)

        Wrapped by :py:func:`user_must_exist`.

        Args:
            user_name (str): name of the user
            may_query (bool): flag give or remove access to user

        Raises:
            WriteConcernError: If the result is not acknowledged.
        """
        MONGO_UPDATE_COUNTER.add(1, {"operation": "set_may_user_query"})
        res = self.db.users.with_options(
            write_concern=WriteConcern(w=WRITE_CONCERN_LEVEL, j=True)
        ).update_one(
            {"id.name": user_name},
            {"$set": {"may_query": may_query}},
        )
        check_result_acknowledged(res)

    @user_must_exist
    def get_and_set_may_user_query(self, user_name: str, may_query: bool) -> bool:
        """
        Atomic operation to check and set if the user may query the server.

        (Set False before querying and True after updating budget)

        Wrapped by :py:func:`user_must_exist`.

        Args:
            user_name (str): name of the user
            may_query (bool): flag give or remove access to user

        Returns:
            bool: The may_query status of the user before the update.
        """
        MONGO_UPDATE_COUNTER.add(1, {"operation": "get_and_set_may_user_query"})
        res = self.db.users.with_options(
            write_concern=WriteConcern(w=WRITE_CONCERN_LEVEL, j=True)
        ).find_one_and_update(
            {"id.name": user_name},
            {"$set": {"may_query": may_query}},
            projection={"may_query": 1},
            return_document=ReturnDocument.BEFORE,
        )

        return res["may_query"]

    @user_must_exist
    def has_user_access_to_dataset(self, user_name: str, dataset_name: str) -> bool:
        """Checks if a user may access a particular dataset.

        Wrapped by :py:func:`user_must_exist`.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            bool: True if the user has access, False otherwise.
        """
        MONGO_QUERY_COUNTER.add(1, {"operation": "has_user_access_to_dataset"})
        if not self.does_dataset_exist(dataset_name):
            raise InvalidQueryException(
                f"Dataset {dataset_name} does not exist. "
                + "Please, verify the client object initialisation.",
            )
        doc_count = self.db.users.count_documents(
            {
                "id.name": user_name,
                "datasets_list.dataset_name": f"{dataset_name}",
            }
        )
        return doc_count > 0

    def get_epsilon_or_delta(self, user_name: str, dataset_name: str, parameter: BudgetDBKey) -> float:
        """Get total spent epsilon or delta by a user on dataset.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            parameter (BudgetDBKey): One of BudgetDBKey.

        Returns:
            float: The requested budget value.
        """
        return next(
            iter(
                self.db.users.aggregate(
                    [
                        {"$unwind": "$datasets_list"},
                        {
                            "$match": {
                                "id.name": user_name,
                                "datasets_list.dataset_name": f"{dataset_name}",
                            }
                        },
                    ]
                )
            )
        )["datasets_list"][parameter]

    def update_epsilon_or_delta(
        self,
        user_name: str,
        dataset_name: str,
        parameter: str,
        spent_value: float,
    ) -> None:
        """Update current budget of user with the last spent budget.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset
            parameter (str): "current_epsilon" or "current_delta"
            spent_value (float): spending of epsilon or delta on last query

        Raises:
            WriteConcernError: If the result is not acknowledged.
        """
        res = self.db.users.with_options(
            write_concern=WriteConcern(w=WRITE_CONCERN_LEVEL, j=True)
        ).update_one(
            {
                "id.name": user_name,
                "datasets_list.dataset_name": dataset_name,
            },
            {"$inc": {f"datasets_list.$.{parameter}": spent_value}},
        )
        check_result_acknowledged(res)

    @dataset_must_exist
    def get_dataset(self, dataset_name: str) -> DSInfo:
        """
        Get dataset access info based on dataset_name.

        Wrapped by :py:func:`dataset_must_exist`.

        Args:
            dataset_name (str): Name of the dataset.

        Returns:
            Dataset: The dataset model.
        """
        dataset = self.db.datasets.find_one({"dataset_name": dataset_name})
        dataset.pop("_id", None)
        dataset.pop("id", None)
        return DSInfo.model_validate(dataset)

    def _resolve_gridfs(self, field: dict) -> dict:
        """
        If the field is a GridFS reference, load it, otherwise return as is.

        Args:
        field (dict): A dictionary that may either be the original stored value
                      or a GridFS reference in the form {"gridfs_id": ObjectId}.

        Returns:
            dict: The original dictionary stored inline, or the dictionary loaded
                from GridFS if it was stored as a reference.
        """
        if isinstance(field, dict) and "gridfs_id" in field:
            data = self.fs.get(field["gridfs_id"]).read().decode("utf-8")
            return json.loads(data)
        return field

    @user_must_have_access_to_dataset
    def get_user_previous_queries(
        self,
        user_name: str,
        dataset_name: str,
    ) -> list[dict]:
        """Retrieves and return the queries already done by a user.

        Wrapped by :py:func:`user_must_have_access_to_dataset`.

        Args:
            user_name (str): name of the user
            dataset_name (str): name of the dataset

        Returns:
            List[dict]: List of previous queries.
        """
        queries = self.db.queries_archives.find(
            {
                "user_name": user_name,
                "dataset_name": f"{dataset_name}",
            },
            {"_id": 0},
        )

        results = []
        for q in queries:
            q["client_input"] = self._resolve_gridfs(q["client_input"])
            q["response"] = self._resolve_gridfs(q["response"])
            results.append(q)

        return results

    def _store_if_too_large(self, field_value: dict, filename: str) -> dict:
        """
        Store a dictionary either inline or in GridFS if it exceeds MongoDB's document size limit.

        This method checks the serialized size of the given dictionary. If it is smaller
        than MongoDB's maximum BSON document size (16 MB), the dictionary is returned
        unchanged. If it exceeds the limit, the data is stored as a JSON file in GridFS
        and a lightweight reference containing the GridFS file ID is returned instead.

        Args:
            field_value (dict): The dictionary to be stored.
            filename (str): A descriptive filename for storing the object in GridFS.

        Returns:
            dict: The original dictionary if it fits within MongoDB's size limit,
                  otherwise a reference in the form {"gridfs_id": ObjectId}.
        """
        json_str = json_util.dumps(field_value)
        size_bytes = sys.getsizeof(json_str)

        if size_bytes >= MAX_BSON_SIZE:
            file_id = self.fs.put(json_str.encode("utf-8"), filename=filename)
            return {"gridfs_id": file_id}
        return field_value

    def save_query(self, user_name: str, query: LomasRequestModel, response: QueryResponse) -> None:
        """
        Save queries of user on datasets in a separate collection (table).

        Args:
            user_name (str): name of the user
            query (LomasRequestModel): Request object received from client
            response (QueryResponse): Response object sent to client

        Raises:
            WriteConcernError: If the result is not acknowledged.
        """
        MONGO_INSERT_COUNTER.add(1, {"operation": "save_query"})
        to_archive = super().prepare_save_query(user_name, query, response)

        # Check big fields before saving
        to_archive["client_input"] = self._store_if_too_large(to_archive["client_input"], "query.json")
        to_archive["response"] = self._store_if_too_large(to_archive["response"], "response.json")

        res = self.db.with_options(
            write_concern=WriteConcern(w=WRITE_CONCERN_LEVEL, j=True)
        ).queries_archives.insert_one(to_archive)
        check_result_acknowledged(res)


def check_result_acknowledged(res: _WriteResult) -> None:
    """Raises an exception if the result is not acknowledged.

    Args:
        res (_WriteResult): The PyMongo WriteResult to check.

    Raises:
        WriteConcernError: If the result is not acknowledged.
    """
    if not res.acknowledged:
        MONGO_ERROR_COUNTER.add(1, {"operation": "write_error"})
        raise WriteConcernError(
            "Write request not acknowledged by MongoDB database."
            + " Please contact the administrator of the server."
        )
