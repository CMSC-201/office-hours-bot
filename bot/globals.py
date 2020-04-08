import json
import os


def get_globals():
    global token
    global prefix
    global uuids

    info = {}
    if os.path.exists('../uuids.json'):
        with open('../uuids.json', 'r') as f:
            info['uuids'] = json.load(f)
    else:
        info['uuids'] = {}

    if os.path.exists('../prop.json'):
        with open('../prop.json', 'r') as f:
            info['props'] = json.load(f)
    else:
        info['props'] = {
            "token": os.environ.get("BOT_TOKEN"),
            "prefix": os.environ.get("BOT_PREFIX"),
            "mongodb-address": os.environ.get("MONGODB_URI"),
            "queue_url": os.environ.get("QUEUE_URL"),
        }

    return info