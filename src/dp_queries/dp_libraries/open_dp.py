from fastapi import HTTPException

from opendp.mod import enable_features
from opendp_logger import make_load_json
from typing import List

from dp_queries.dp_logic import DPQuerier
from utils.constants import DUMMY_NB_ROWS, DUMMY_SEED
from utils.loggr import LOG

enable_features("contrib")

PT_TYPE = "^py_type:*"


class OpenDPQuerier(DPQuerier):
    def __init__(
        self,
        metadata,
        private_db,
        dummy: bool = False,
        dummy_nb_rows: int = DUMMY_NB_ROWS,
        dummy_seed: int = DUMMY_SEED,
    ) -> None:
        super().__init__(
            metadata, private_db, dummy, dummy_nb_rows, dummy_seed
        )

    def cost(self, query_json: dict) -> List[float]:
        opendp_pipe = make_load_json(query_json.opendp_json)

        try:
            epsilon, delta = opendp_pipe.map(d_in=1.0)
        except Exception:
            try:
                epsilon, delta = opendp_pipe.map(d_in=1)
            except Exception as e:
                LOG.exception(e)
                raise HTTPException(
                    400,
                    "Error obtaining privacy map for the chain. \
                        Please ensure methods return epsilon, \
                            and delta in privacy map. Error:"
                    + str(e),
                )
        return [epsilon, delta]

    def query(self, query_json: dict) -> str:
        opendp_pipe = make_load_json(query_json.opendp_json)

        try:
            # response, privacy_map = opendp_apply(opendp_pipe)
            release_data = opendp_pipe(self.df.to_csv())
        except HTTPException as he:
            LOG.exception(he)
            raise he
        except Exception as e:
            LOG.exception(e)
            raise HTTPException(
                400,
                "Failed when applying chain to data with error: " + str(e),
            )
        return str(release_data)
