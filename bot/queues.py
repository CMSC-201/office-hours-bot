from typing import Optional
from discord import Guild, Member, Message, CategoryChannel, NotFound
from datetime import datetime
import discord.utils
import mongo, logging

logger = logging.getLogger(__name__)

class OHSession:
    __MEMBER_ID_FIELD = "member-id"

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
            self.__MEMBER_ID_FIELD: self.member.id,
            "request": self.request,
            "announcement": self.announcement.id,
            "TA": self.ta.id,
        }
        if self.role:
            output["role"] = self.role.id
        if self.room:
            output["room"] = self.room.id
        return output

    def __repr__(self):
        return "Member {}, Message {}, TA {}".format(self.member, self.request, self.ta)

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
    __REQUEST_TIME = 'request-time'

    def __init__(self, guild: Guild):
        self.guild = guild

    def insert_in_queue(self, session):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "available_tas": [],
                "open": True,
            }
            collection.insert_one(document)
        # doesn't work of course
        pass

    def add_to_queue(self, member: Member, request: str, announcement: Message):
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "available_tas": [],
                "open": True,
            }
            collection.insert_one(document)

        print(member.id)
        document["queue"].append({
            self.__MEMBER_ID_FIELD: member.id,
            self.__REQUEST_FIELD: request,
            self.__MESSAGE_ID_FIELD: announcement.id,
            self.__REQUEST_TIME: datetime.now()
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
        return OHSession(member=self.guild.get_member(output_session[self.__MEMBER_ID_FIELD]),
                         request=output_session[self.__REQUEST_FIELD],
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
            collection.insert_one(document)

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
            collection.insert_one(document)

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

    """
	Adds the given ta_uid to the active TA list, and gives the TA the active TA
	 role. If the role does not exist, it is created, and is placed above TA
	 role.
    """
    async def open_office_hours(self, ta_uid: int) -> bool:
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "available_tas": [],
                "active_role": 0,
                "open": True,
            }
            collection.insert_one(document)
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

        ## Create "Active/on-duty TA" role, if needed
        if "active_role" not in document:
            document["active_role"] = 0

        active_role: Role = discord.utils.get(self.guild.roles, id=document["active_role"])
        if not active_role:
            active_role: Role = await self.guild.create_role(name="On-duty TA", hoist=True)
            document["active_role"] = active_role.id
            logger.info("Created on-duty TA role")

            ## Find TA role and place "On-duty" role above it, but below upper roles
            move_roles = False
            ta_pos = 0
            for i,role in enumerate(self.guild.roles, 0):
                #logger.info("Role: '%s' @ %d" % (role, role.position))
                # If we've found the TA role and there is no empty position index, move remaining roles up
                if ta_pos and (role.position - ta_pos) < 2:
                    move_roles = True
                    break
                elif role.name == "TA" and not ta_pos:
                    ta_pos = role.position
                    #logger.info("Found TA role with id %d at index %d!" % (role.id, i))

            ## Update role positions for correct ordering
            to_move = [active_role] # Active role needs to move regardless
            to_pos = [ta_pos + 1]

            # Add existing roles to move if necessary
            if move_roles:
                existing_roles = self.guild.roles[ta_pos+1:]
                to_move.extend(existing_roles)
                to_pos.extend([(r.position+1) for r in existing_roles])

                logger.info("Adding %d existing roles to move.." % (len(existing_roles)))

            move = dict(zip(to_move, to_pos)) # Dictionary of roles and new positions

            # Attempt positions update
            try:
                await self.guild.edit_role_positions(positions=move)

                logger.info("Moved on-duty role up")
            except BaseException as e:
                logger.error("Error updating roles: %s" % (e))

            #for i,role in enumerate(self.guild.roles, 0):
            #    logger.info("Role: '%s' @ %d" % (role, role.position))

        # Add TA to role
        await self.guild.get_member(ta_uid).add_roles(active_role)

        collection.replace_one({"_id": document["_id"]}, document)
        return fresh_start, is_new_ta

    """
	Closes office hours, and removes the active TA role from all remaining TAs.
    """
    async def force_close_office_hours(self) -> int:
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "available_tas": [],
                "open": False,
            }
            collection.insert_one(document)

        # Remove active roles
        active_role: Role = discord.utils.get(self.guild.roles, id=document["active_role"])
        if active_role:
            for ta_uid in document["available_tas"]:
                await self.guild.get_member(ta_uid).remove_roles(active_role)

        document["queue"] = []
        document["available_tas"] = []
        document['open'] = False

        collection.replace_one({"_id": document["_id"]}, document)

    """
	If present, removes given ta_uid from available TAs and removes the active
	 TA role from the TA.
    """
    async def close_office_hours(self, ta_uid: int) -> int:
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()
        if not document:
            document = {
                "queue": [],
                "available_tas": [],
                "open": False,
            }
            collection.insert_one(document)

        was_removed = False
        tas = len(document["available_tas"])
        if ta_uid in document["available_tas"]:
            document["available_tas"].remove(ta_uid)
            was_removed = True
            tas -= 1

            # Remove active role
            active_role: Role = discord.utils.get(self.guild.roles, id=document["active_role"])
            await self.guild.get_member(ta_uid).remove_roles(active_role)

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
            collection.insert_one(document)

        if ta_uid in document["available_tas"]:
            return True

        return False

    """ Returns list of Member IDs of the checked-in TAs
    """
    def on_duty_ta_list(self) -> list:
        collection = mongo.db[self.__QUEUE_COLLECTION]
        document = collection.find_one()

        if not document:
            return []

        return document["available_tas"]
