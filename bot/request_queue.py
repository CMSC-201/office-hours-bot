import json

import pymongo

from bot import get_globals


def using_mongo():
    return "mongodb-address" in get_globals() and get_globals()[
        "mongodb-address"]


if using_mongo():
    client = pymongo.MongoClient(get_globals()['mongodb-address'])

    db = client["botdb"]


def read_json(path):
    if using_mongo():
        collection = db[path]
        return collection.find()
    else:
        with open(path, "r") as f:
            return json.load(f)


def write_json(path, data):
    if using_mongo():
        collection = db[path]
        collection.delete_many()
        collection.insert_many(data, ordered=True)
    else:
        with open(path, "w+") as f:
            f.write(json.dumps(data))
