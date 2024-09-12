import unittest
from typing import Any, Dict

import opendp

from dp_queries.dp_libraries.opendp import (
    get_global_params,
    get_lf_domain,
    update_params_by_grouping,
)


class TestMarginDomain(unittest.TestCase):
    """
    Tests for margin update with lazyframe domain
    """

    def test_opendp_margin(self) -> None:  # pylint: disable=R0915
        """test opendp margin. Partitions parameters"""
        metadata: Dict[str, Any] = {
            "max_ids": 1,
            "rows": 100,
            "columns": {
                "column_int": {
                    "type": "int",
                    "precision": 32,
                    "upper": 10,
                    "lower": 1,
                },
                "column_category": {
                    "type": "string",
                    "categories": [1, 2, 3, 4, 5],
                    "cardinality": 5,
                    # 'max_partition_length' : 60, # proportion max
                    # 'max_influenced_partitions': 1,
                    # 'max_partition_contributions': 1,
                },
                "column_category_2": {
                    "type": "string",
                    "categories": [1, 2, 3, 4, 5],
                    "cardinality": 5,
                    # 'max_partition_length' : 10, # proportion max
                    # 'max_influenced_partitions': 1,
                    # 'max_partition_contributions': 1,
                },
            },
        }

        # No grouping (only global)
        by_config = []
        params = get_global_params(metadata)
        self.assertEqual(params["max_num_partitions"], 1)
        self.assertEqual(params["max_partition_length"], 100)

        # Fail if no rows in metadata
        del metadata["rows"]
        with self.assertRaises(KeyError):
            params = get_global_params(metadata)

        # Single grouping, default params
        metadata["rows"] = 100
        by_config = ["column_category"]
        params = update_params_by_grouping(metadata, by_config, params)
        self.assertEqual(params["max_num_partitions"], 5)
        self.assertEqual(params["max_partition_length"], 100)
        with self.assertRaises(KeyError):
            params["max_influenced_partitions"]  # pylint: disable=W0104
        with self.assertRaises(KeyError):
            params["max_partition_contributions"]  # pylint: disable=W0104

        # Single grouping, max_partition_length
        metadata["columns"]["column_category"]["max_partition_length"] = 60
        params = update_params_by_grouping(
            metadata, by_config, get_global_params(metadata)
        )
        self.assertEqual(params["max_partition_length"], 60)

        # Single grouping, max_influenced_partitions
        metadata["columns"]["column_category"]["max_influenced_partitions"] = 3
        metadata["max_ids"] = 2
        params = update_params_by_grouping(
            metadata, by_config, get_global_params(metadata)
        )
        # equal to 2 since max_ids is 2 (cannot appear more than max_ids)
        self.assertEqual(params["max_influenced_partitions"], 2)

        metadata["max_ids"] = 6
        params = update_params_by_grouping(
            metadata, by_config, get_global_params(metadata)
        )
        self.assertEqual(params["max_influenced_partitions"], 3)

        # Single grouping, max_partition_contributions
        del metadata["columns"]["column_category"]["max_influenced_partitions"]
        metadata["columns"]["column_category"][
            "max_partition_contributions"
        ] = 8
        params = update_params_by_grouping(
            metadata, by_config, get_global_params(metadata)
        )
        self.assertEqual(params["max_partition_contributions"], 6)

        metadata["max_ids"] = 10
        params = update_params_by_grouping(
            metadata, by_config, get_global_params(metadata)
        )
        self.assertEqual(params["max_partition_contributions"], 8)

        # Single grouping, max_partition_contributions, max_influenced_partitions
        metadata["max_ids"] = 5
        metadata["columns"]["column_category"]["max_influenced_partitions"] = 3
        metadata["columns"]["column_category"][
            "max_partition_contributions"
        ] = 8
        params = update_params_by_grouping(
            metadata, by_config, get_global_params(metadata)
        )
        self.assertEqual(params["max_partition_contributions"], 5)
        self.assertEqual(params["max_influenced_partitions"], 3)

        # Test lf_domain creation
        lf_domain = get_lf_domain(metadata, by_config)
        self.assertEqual(type(lf_domain), opendp.mod.Domain)

        # Multiple grouping
        by_config = ["column_category", "column_category_2"]
        metadata["max_ids"] = 30

        # column2 without info on partitions
        metadata["columns"]["column_category"]["max_influenced_partitions"] = 1
        metadata["columns"]["column_category"][
            "max_partition_contributions"
        ] = 2
        params = update_params_by_grouping(
            metadata, by_config, get_global_params(metadata)
        )
        self.assertEqual(params["max_partition_contributions"], 2)
        self.assertEqual(params["max_influenced_partitions"], 1)
        self.assertEqual(params["max_partition_length"], 60)
        self.assertEqual(params["max_num_partitions"], 25)

        # column2 with info on partitions
        metadata["columns"]["column_category"]["max_influenced_partitions"] = 1
        metadata["columns"]["column_category"][
            "max_partition_contributions"
        ] = 2
        metadata["columns"]["column_category_2"][
            "max_influenced_partitions"
        ] = 3
        metadata["columns"]["column_category_2"][
            "max_partition_contributions"
        ] = 4
        params = update_params_by_grouping(
            metadata, by_config, get_global_params(metadata)
        )
        self.assertEqual(params["max_partition_contributions"], 8)
        self.assertEqual(params["max_influenced_partitions"], 3)
        self.assertEqual(params["max_partition_length"], 60)

        # multiple, above max_ids for max_partition, multiple partition_length
        metadata["columns"]["column_category_2"][
            "max_partition_contributions"
        ] = 20
        metadata["columns"]["column_category_2"]["max_partition_length"] = 10
        params = update_params_by_grouping(
            metadata, by_config, get_global_params(metadata)
        )
        self.assertEqual(
            params["max_partition_contributions"], 30
        )  # 40 > max_ids (30)
        self.assertEqual(params["max_partition_length"], 10)

        # Test lf_domain creation
        lf_domain = get_lf_domain(metadata, by_config)
        self.assertEqual(type(lf_domain), opendp.mod.Domain)

        # test without categories / cardinality
        del metadata["columns"]["column_category"]["categories"]
        del metadata["columns"]["column_category"]["cardinality"]
        del metadata["columns"]["column_category"][
            "max_partition_contributions"
        ]
        del metadata["columns"]["column_category"]["max_influenced_partitions"]
        # test with single grouping
        by_config = ["column_category"]
        params = update_params_by_grouping(
            metadata, by_config, get_global_params(metadata)
        )
        self.assertEqual(params["max_num_partitions"], None)
        lf_domain = get_lf_domain(metadata, by_config)
        self.assertEqual(type(lf_domain), opendp.mod.Domain)
        # test with multiple grouping
        by_config = ["column_category", "column_category_2"]
        metadata["columns"]["column_category_2"]["cardinality"] = 4
        params = update_params_by_grouping(
            metadata, by_config, get_global_params(metadata)
        )
        self.assertEqual(params["max_num_partitions"], 4)
        lf_domain = get_lf_domain(metadata, by_config)
        self.assertEqual(type(lf_domain), opendp.mod.Domain)
