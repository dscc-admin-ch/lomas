import argparse
import pymongo


def main(args):
    create_example_mongodb()



def create_example_mongodb():
    """
    Create a test MongoDB database that is running inside a container
    named mongodb
    """
    mongodb_client = pymongo.MongoClient(
        f"mongodb://mongodb:27017/"
    )
    db = mongodb_client["example_database"]
    db.users.insert_many(
        [
            {
                "user_name": "Alice",
                "datasets_list": [
                    {
                        "dataset_name": "IRIS",
                        "max_epsilon": 10,
                        "max_delta": 0.0001,
                        "current_epsilon": 1,
                        "current_delta": 0.000001,
                    },
                    {
                        "dataset_name": "IRIS",
                        "max_epsilon": 5,
                        "max_delta": 0.0005,
                        "current_epsilon": 0.2,
                        "current_delta": 0.0000001,
                    },
                ],
            },
            {
                "user_name": "Bob",
                "datasets_list": [
                    {
                        "dataset_name": "iris",
                        "max_epsilon": 10,
                        "max_delta": 0.0001,
                        "current_epsilon": 0,
                        "current_delta": 0,
                    }
                ],
            },
        ]
    )

    return db


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="MongoDB administration script for the SDD POC Server"
    )

    parser.add_argument(
        "-u",
        "--add_user",
        required=False,
        help="Adds a user to the database. Requires options -...",
    )

    args = parser.parse_args()

    main(args)
