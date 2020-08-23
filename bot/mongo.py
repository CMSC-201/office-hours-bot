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

    port_number = get_globals()['props'].get('mongo-db-port', 0)

    address = address.split("?")[0]
    # change back for deployment on server
    client = pymongo.MongoClient('localhost', 27017)
    # client = pymongo.MongoClient(address + '?retryWrites=false&w=majority')

    db_name = address.split("/")[-1]
    db = client[db_name]