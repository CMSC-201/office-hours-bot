import pymongo

from bot import get_props

client = pymongo.MongoClient(get_props()['mongodb-address'])

db = client["botdb"]
collection = db["queue_test"]

# collection.insert_one({
#     "user_id": "biff",
#     "age": 4,
# })

x = collection.find_one()

print(x)
