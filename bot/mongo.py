import json
import logging

import pymongo

from globals import get_globals

logger = logging.getLogger('mongo')
db = None


def using_mongo():
    props = get_globals()["props"]
    return "mongodb-address" in props and props[
        "mongodb-address"]


if using_mongo():
    address = get_globals()["props"]['mongodb-address']
    client = pymongo.MongoClient(address)
    db_name = address.split("/")[-1]
    db = client[db_name]


def read_json(path):
    if using_mongo():
        collection = db[path]
        return collection.find()
    else:
        with open("../" + path + ".json", "r") as f:
            return json.load(f)


def write_json(path, data):
    if using_mongo():
        collection = db[path]
        collection.delete_many()
        collection.insert_many(data, ordered=True)
    else:
        with open("../" + path + ".json", "w+") as f:
            f.write(json.dumps(data))
