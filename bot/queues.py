from discord import Guild, Member

import mongo


class QueueAuthority:
    __QUEUE_COLLECTION = 'queues'
    __MEMBER_ID_FIELD = "member-id"
    __REQUEST_FIELD = "request"

    def __init__(self, guild: Guild):
        self.guild = guild

    def add_to_queue(self, member: Member, request: str):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": []
            }
            collection.insert(document)

        document["queue"].append({
            self.__MEMBER_ID_FIELD: member.id,
            self.__REQUEST_FIELD: request,
        })
        collection.replace_one({"_id": document["_id"]}, document)
