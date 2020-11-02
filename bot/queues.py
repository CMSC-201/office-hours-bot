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
        member = await guild.fetch_member(dictionary["student"])

        ta = await guild.fetch_member(dictionary["TA"])

        return OHSession(
            member=member,
            request=dictionary["request"],
            announcement=dictionary["announcement"],
            ta=ta,
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
                "available_tas": [],
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

        the_member = await self.guild.fetch_member(session[self.__MEMBER_ID_FIELD])

        return OHSession(member=the_member,
                         request=session[self.__REQUEST_FIELD],
                         announcement=message,
                         ta=ta)

    async def find_and_remove_by_user_id(self, student: Member):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            return None
        if not document["queue"]:
            return None

        output_session = None
        for i, session in enumerate(document["queue"]):
            if session[self.__MEMBER_ID_FIELD] == student.id:
                output_session = session
                del document["queue"][i]
                break

        # get the message object
        message: Optional[Message] = None
        for channel in self.guild.text_channels:
            try:
                m = await channel.fetch_message(output_session[self.__MESSAGE_ID_FIELD])
                if m:
                    message = m
            except NotFound:
                pass

        collection.replace_one({"_id": document["_id"]}, document)

        the_member = await self.guild.fetch_member(session[self.__MEMBER_ID_FIELD])
        return OHSession(member=the_member,
                         request=session[self.__REQUEST_FIELD],
                         announcement=message,
                         ta=None)

    def is_member_in_queue(self, member: Member):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "available_tas": [],
                "open": True,
            }
            collection.insert(document)

        for queue_item in document["queue"]:
            if queue_item[self.__MEMBER_ID_FIELD] == member.id:
                return True

        return False

    @staticmethod
    def queue_for_web():
        collection = mongo.db[QueueAuthority.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            return []
        else:
            return document["queue"]

    def retrieve_queue(self):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            return []
        else:
            return document["queue"]

    async def remove_all(self):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "available_tas": [],
                "open": False,
            }
            collection.insert(document)

        while len(document["queue"]) > 0:
            session = document["queue"][0]
            document["queue"] = document["queue"][1:]
            collection.replace_one({"_id": document["_id"]}, document)

            # delete the announcement
            for channel in self.guild.text_channels:
                try:
                    m: Optional[Message] = await channel.fetch_message(session[self.__MESSAGE_ID_FIELD])
                    if m:
                        await m.delete()
                except NotFound:
                    pass

        document["queue"] = []
        document["available_tas"] = []
        document["open"] = False
        collection.replace_one({"_id": document["_id"]}, document)

    def is_office_hours_open(self) -> bool:
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document or not document["open"]:
            return False
        return True

    def open_office_hours(self, ta_uid: int) -> bool:
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "available_tas": [],
                "open": True,
            }
            collection.insert(document)
        if "available_tas" not in document:
            document["available_tas"] = []
        # Check if this is a new queue beginning and if new TA queueing
        fresh_start, is_new_ta = False, False
        if document["open"]:
            # Only check existing TA if open

            if ta_uid not in document["available_tas"]:
                document["available_tas"].append(ta_uid)
                is_new_ta = True

        else:
            document["queue"] = []
            document["available_tas"] = [ta_uid]
            document["open"] = True
            fresh_start = True
            is_new_ta = True

        collection.replace_one({"_id": document["_id"]}, document)
        return fresh_start, is_new_ta

    def force_close_office_hours(self) -> int:
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "available_tas": [],
                "open": False,
            }
            collection.insert(document)

        document["queue"] = []
        document["available_tas"] = []
        document['open'] = False

        collection.replace_one({"_id": document["_id"]}, document)

    def close_office_hours(self, ta_uid: int) -> int:
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "available_tas": [],
                "open": False,
            }
            collection.insert(document)

        was_removed = False
        tas = len(document["available_tas"])
        if ta_uid in document["available_tas"]:
            document["available_tas"].remove(ta_uid)
            was_removed = True
            tas -= 1

        collection.replace_one({"_id": document["_id"]}, document)
        return document["open"], was_removed, tas

    def is_ta_on_duty(self, ta_uid: int) -> bool:
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "available_tas": [],
                "open": True,
            }
            collection.insert(document)

        if ta_uid in document["available_tas"]:
            return True

        return False
