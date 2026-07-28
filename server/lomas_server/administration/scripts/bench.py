#!/usr/bin/env python

from typing import Literal

import polars as pl
from pydantic import HttpUrl
from pydantic_settings import BaseSettings, CliApp, SettingsConfigDict

from lomas_client import Client

try:
    from rich.pretty import pprint
except ImportError:
    pprint = print


class BenchConfig(BaseSettings):
    model_config = SettingsConfigDict(
        cli_implicit_flags="toggle",
        cli_kebab_case="all",
        use_attribute_docstrings=True,
        cli_avoid_json=True,
        cli_hide_none_type=True,
        cli_shortcuts={
            "app-url": "s",
            "dataset-name": "d",
        },
    )

    idx: int = 0
    """Bench user number for parralel load (1 user may have only 1 query at time)."""
    app_url: HttpUrl = "http://localhost:48080"
    """The base URL for the API server."""
    dataset_name: str = "FSO_INCOME_SYNTHETIC"
    """The name of the dataset to be accessed or manipulated."""
    preset: Literal["smol", "medium", "large"] = "medium"

    def cli_cmd(self) -> None:
        client = Client(
            app_url=self.app_url,
            dataset_name=self.dataset_name,
            user_name=f"user-{self.idx}@bench.com",
            user_password=f"secret-{self.idx}",
        )
        client.get_dataset_metadata()

        for _ in range(10):
            client.get_dummy_dataset()

        plan = None
        match self.preset, self.dataset_name:
            # Benchmark 1: lomas-bench --preset smol -d penguin
            # Time (mean ± σ):      3.757 s ±  0.282 s    [User: 3.229 s, System: 0.245 s]
            # Range (min … max):    3.182 s …  4.078 s    10 runs
            case ("smol", "penguin"):
                plan = client.get_context(rho=0.1).query().select(pl.col("species").dp.len())

            # Benchmark 1: lomas-bench --preset medium -d penguin
            #   Time (mean ± σ):      4.453 s ±  0.902 s    [User: 3.821 s, System: 0.261 s]
            #   Range (min … max):    3.815 s …  6.872 s    10 runs
            case ("medium", "penguin"):
                plan = (
                    client.get_context(rho=0.1)
                    .query()
                    .group_by(["species", "island"])
                    .agg(
                        [
                            pl.col("bill_length_mm").dp.mean(bounds=(30, 65)),
                            pl.col("flipper_length_mm").dp.mean(bounds=(150, 250)),
                        ]
                    )
                )

            # Benchmark 2: lomas-bench --preset medium -d FSO_INCOME_SYNTHETIC
            #   Time (mean ± σ):     10.881 s ±  0.263 s    [User: 3.512 s, System: 0.252 s]
            #   Range (min … max):   10.558 s … 11.513 s    10 runs
            case ("medium", "FSO_INCOME_SYNTHETIC"):
                plan = (
                    client.get_context(rho=0.1)
                    .query()
                    .group_by(["profession", "sex"])
                    .agg([pl.col("age").dp.mean(bounds=(0, 100))])
                )

            # Benchmark 1: lomas-bench --preset large
            #   Time (mean ± σ):     18.349 s ±  3.288 s    [User: 3.226 s, System: 0.237 s]
            #   Range (min … max):   13.899 s … 22.893 s    10 runs
            case ("large", "FSO_INCOME_SYNTHETIC"):
                from diffprivlib import models  # noqa:PLC0415
                from sklearn.pipeline import Pipeline  # noqa:PLC0415

                feature_columns = ["age", "sex"]
                bounds = client.get_diffprivlib_bounds(feature_columns)
                dp_res = client.diffprivlib.query(
                    pipeline=Pipeline(
                        [
                            ("scaler", models.StandardScaler(epsilon=0.5, bounds=bounds)),
                            ("classifier", models.LogisticRegression(epsilon=1.0, data_norm=3)),
                        ]
                    ),
                    feature_columns=["age", "sex"],
                    target_columns=["education"],
                )
                pprint(dp_res)

            case _:
                raise ValueError("Incompatible parameters")

        if plan is not None:
            dummy_res = plan.release().collect()
            pprint(dummy_res)

            res = client.opendp.query(plan, epsilon=1.0, delta=1e-5)
            pprint(res)


def run() -> None:
    CliApp.run(BenchConfig)


if __name__ == "__main__":
    run()
