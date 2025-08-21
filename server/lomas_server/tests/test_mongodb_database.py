import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lomas_core.models.constants import PrivateDatabaseType
from lomas_core.models.requests import SmartnoiseSQLRequestModel
from lomas_core.models.responses import QueryResponse, SmartnoiseSQLQueryResult
from lomas_server.admin_database.mongodb_database import AdminMongoDatabase
from lomas_server.administration.mongodb_admin import add_dataset, add_user_with_budget, drop_collection
from lomas_server.models.config import Config


class TestMongoDBDatabase(unittest.TestCase):
    """
    Tests for the functions in mongodb_database.py.

    This is an integration test and requires a mongodb database
    to be started before being executed.
    """

    def setUp(self) -> None:
        """Connection to database."""
        self.mongo_config = Config().admin_database
        self.admin = AdminMongoDatabase(self.mongo_config)
        self.test_data_dir = str(Path(__file__).parent / "test_data")

        self.user = "BiancaCastafiore"
        self.dataset = "PENGUIN"
        email = "BiancaCastafiore@example.com"
        epsilon = 10
        delta = 0.02
        add_user_with_budget(self.mongo_config, self.user, email, self.dataset, epsilon, delta)

        database_type = PrivateDatabaseType.PATH
        dataset_path = "some_path"
        metadata_database_type = PrivateDatabaseType.PATH
        metadata_path = f"{self.test_data_dir}/metadata/penguin_metadata.yaml"
        add_dataset(
            self.mongo_config,
            self.dataset,
            database_type,
            metadata_database_type,
            dataset_path=dataset_path,
            metadata_path=metadata_path,
        )

    def tearDown(self) -> None:
        """Drop all data from database."""
        drop_collection(self.mongo_config, "metadata")
        drop_collection(self.mongo_config, "datasets")
        drop_collection(self.mongo_config, "users")
        drop_collection(self.mongo_config, "queries_archives")

    def test_save_and_get_small_query(self) -> None:
        """Queries below MAX_BSON_SIZE should be stored inline."""

        df = pd.DataFrame(
            {"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"], "passed": [True, False, True]}
        )
        snsql_request = SmartnoiseSQLRequestModel(
            dataset_name=self.dataset,
            query_str="SELECT * FROM df",
            epsilon=0.1,
            delta=0.001,
            mechanisms={"a": "laplace"},
        )
        result_obj = SmartnoiseSQLQueryResult(df=df)
        response = QueryResponse(requested_by=self.user, result=result_obj, epsilon=1.0, delta=0.01)

        self.admin.save_query(self.user, snsql_request, response)
        results = self.admin.get_user_previous_queries(self.user, self.dataset)

        assert len(results) == 1
        res = results[0]
        # Both stored inline (not GridFS)
        assert isinstance(res["client_input"], dict)
        assert isinstance(res["response"], dict)
        assert "gridfs_id" not in res["client_input"]
        assert "gridfs_id" not in res["response"]

    def test_save_and_get_large_query(self) -> None:
        """Queries above MAX_BSON_SIZE should be stored in GridFS and resolved automatically."""

        # Make big df
        rng = np.random.default_rng()
        n_rows = 100_000  # enough to comfortably exceed 16MB
        df_large = pd.DataFrame(
            {
                "id": np.arange(n_rows),
                "name": rng.choice(["Alice", "Bob", "Charlie", "David", "Eve"], size=n_rows),
                "score": rng.random(n_rows) * 100,
                "passed": rng.choice([True, False], size=n_rows),
                "notes": rng.choice(["Good", "Average", "Poor", "Excellent"], size=n_rows),
            }
        )

        snsql_request = SmartnoiseSQLRequestModel(
            dataset_name=self.dataset,
            query_str="SELECT * FROM df",
            epsilon=0.1,
            delta=0.001,
            mechanisms={"a": "laplace"},
        )
        result_obj = SmartnoiseSQLQueryResult(df=df_large)
        response = QueryResponse(requested_by=self.user, result=result_obj, epsilon=1.0, delta=0.01)

        self.admin.save_query(self.user, snsql_request, response)

        results = self.admin.get_user_previous_queries(self.user, self.dataset)
        assert len(results) == 1
        res = results[0]

        # Should have been resolved transparently from GridFS
        assert isinstance(res["client_input"], dict)
        assert isinstance(res["response"], dict)
        assert "gridfs_id" not in res["client_input"]
        assert "gridfs_id" not in res["response"]
