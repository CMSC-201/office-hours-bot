from typing import Optional

from discord import Guild, Member, Message, CategoryChannel, TextChannel, NotFound

import mongo


class OHSession:
    def __init__(self, member: Member = None, request: str = None, announcement: Message = None, ta: Member = None):
        self.member: Member = member
        self.request: str = request
        self.announcement: Message = announcement
        self.ta: Member = ta
        self.room: Optional[CategoryChannel] = None

    def to_dict(self) -> dict:
        output = {
            "student": self.member.id,
            "request": self.request,
            "announcement": self.announcement.id,
            "TA": self.ta.id,
        }
        if self.room:
            output["room"] = self.room.id
        return output


# TODO: migrate to using a document for each queue entry (not sure about ordering atm)
class QueueAuthority:
    __QUEUE_COLLECTION = 'queues'
    __MEMBER_ID_FIELD = "member-id"
    __REQUEST_FIELD = "request"
    __MESSAGE_ID_FIELD = "announcement"

    def __init__(self, guild: Guild):
        self.guild = guild

    def add_to_queue(self, member: Member, request: str, announcement: Message):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "open": True,
            }
            collection.insert(document)

        document["queue"].append({
            self.__MEMBER_ID_FIELD: member.id,
            self.__REQUEST_FIELD: request,
            self.__MESSAGE_ID_FIELD: announcement.id
        })
        collection.replace_one({"_id": document["_id"]}, document)

    async def dequeue(self, ta: Member) -> Optional[OHSession]:
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            return None
        if not document["queue"]:
            return None
        session = document["queue"][0]
        document["queue"] = document["queue"][1:]
        collection.replace_one({"_id": document["_id"]}, document)

        # get the message object
        message: Optional[Message] = None
        for channel in self.guild.text_channels:
            try:
                m = await channel.fetch_message(session[self.__MESSAGE_ID_FIELD])
                if m:
                    message = m
            except NotFound:
                pass

        return OHSession(self.guild.get_member(session[self.__MEMBER_ID_FIELD]),
                         session[self.__REQUEST_FIELD],
                         message,
                         ta)

    def retrieve_queue(self):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            return []
        else:
            return document["queue"]

    def remove_all(self):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "open": False,
            }
            collection.insert(document)

        document["queue"] = []
        document["open"] = False
        collection.replace_one({"_id": document["_id"]}, document)
