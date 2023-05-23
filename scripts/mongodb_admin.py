import argparse
import pymongo


def main(args):
    print(args.add_user)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="MongoDB administration script for the SDD POC Server")

    parser.add_argument("-u", "--add_user", required=False,
                        help="Adds a user to the database. Requires options -...")
    
    args = parser.parse_args()

    main(args)