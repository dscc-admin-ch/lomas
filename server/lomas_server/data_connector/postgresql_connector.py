from typing import Optional

from sqlalchemy import create_engine
import pandas as pd

from data_connector.data_connector import DataConnector
from utils.collection_models import Metadata
from utils.config import PostgreSQLCredentialsConfig
from utils.error_handler import InternalServerException


class PostgreSQLConnector(DataConnector):
    """
    DataConnector for dataset in PostgreSQL database.
    """

    def __init__(
        self,
        credentials: PostgreSQLCredentialsConfig,
    ) -> None:
        """Initializer. Does not load the dataset yet.

        Args:
            credentials: informations to access PostgreSQL
        """

        self.postgres_conn = create_engine(
            f"postgresql://{credentials.user}:{credentials.password}@"
            f"{credentials.host}:{credentials.port}/{credentials.database}"
        )
        self.table = credentials.table
        self.df: Optional[pd.DataFrame] = None

    def get_pandas_df(self) -> pd.DataFrame:
        """Get the data in pandas dataframe format

        Raises:
            InternalServerException: If the dataset cannot be read.

        Returns:
            pd.DataFrame: pandas dataframe of dataset
        """
        if self.df is None:
            try:
                with self.postgres_conn.connect() as postgres_connect: 
                    df = pd.read_sql_table(self.table, postgres_connect)                    
            except Exception as err:
                raise InternalServerException(
                    "Error connecting to postgres and reading table "
                    f"{self.table} into a Pandas dataframe."
                )

            # Notify observer since memory usage has changed
            for observer in self.dataset_observers:
                observer.update_memory_usage()

        return self.df
