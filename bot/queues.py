from typing import Optional

from discord import Guild, Member, Message, CategoryChannel, NotFound

import mongo


class OHSession:
    def __init__(self, member: Member = None, request: str = None, announcement: Message = None, ta: Member = None,
                 room=None, role=None):
        self.member: Member = member
        self.request: str = request
        self.announcement: Message = announcement
        self.ta: Member = ta
        self.room: Optional[CategoryChannel] = room
        self.role = role

    def to_dict(self) -> dict:
        output = {
            "student": self.member.id,
            "request": self.request,
            "announcement": self.announcement.id,
            "TA": self.ta.id,
        }
        if self.role:
            output["role"] = self.role.id
        if self.room:
            output["room"] = self.room.id
        return output

    @staticmethod
    def from_dict(dictionary: dict, guild: Guild):
        return OHSession(
            member=guild.get_member(dictionary["student"]),
            request=dictionary["request"],
            announcement=dictionary["announcement"],
            ta=guild.get_member(dictionary["TA"]),
            room=guild.get_channel(dictionary["room"]),
            role=guild.get_role(dictionary["role"]),
        )


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

        return OHSession(member=self.guild.get_member(session[self.__MEMBER_ID_FIELD]),
                         request=session[self.__REQUEST_FIELD],
                         announcement=message,
                         ta=ta)

    # Return the position of the member in the queue. Returns -1 if not found.
    def get_queue_position_of(self, member: Member):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "open": True,
            }
            collection.insert(document)

        position = 0
        for queue_item in document["queue"]:
            if queue_item[self.__MEMBER_ID_FIELD] == member.id:
                return position
            position += 1

        return -1

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

    def is_office_hours_open(self) -> bool:
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document or not document["open"]:
            return False
        return True

    def open_office_hours(self):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "open": False,
            }
            collection.insert(document)

        document["queue"] = []
        document["open"] = True
        collection.replace_one({"_id": document["_id"]}, document)
