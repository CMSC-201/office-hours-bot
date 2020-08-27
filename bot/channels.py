import json
import logging

from discord import Guild, TextChannel, Message, Client, CategoryChannel, PermissionOverwrite
from discord.abc import GuildChannel

import mongo
from queues import OHSession
from roles import RoleAuthority

logger = logging.getLogger("channels")


class ChannelAuthority:
    """
    Class that manages mongoDB records of channels "of interest," i.e. channels that the bot performs operations on
    NOTE:  Current a bot can only manage one guild because there is nothing in the channel authority that is currently
    guild-sensitive
    """
    __WAITING_CHANNEL_KEY = "waiting"
    __QUEUE_CHANNEL_KEY = "queue"
    __CHANNEL_COLLECTION = "channels"
    __OH_SESSION_KEY = "oh_sessions"
    __AUTH_CHANNEL_KEY = "auth"
    __BULLETIN_CHANNEL_KEY = "bulletin"
    __MAINT_CHANNEL_KEY = 'maint'
    __LAB_CATEGORY_NAME = 'Lab'

    def __init__(self, guild: Guild):
        self.waiting_channel: TextChannel = None
        self.queue_channel: TextChannel = None
        self.lab_sections = {}
        self.guild: Guild = guild
        self.oh_sessions = None
        self.lab_sections = {}
        channels = mongo.db[self.__CHANNEL_COLLECTION].find_one()
        if not channels:
            logger.warning("Unable to load channel authority!  Run setup!")
            return
        try:
            waiting_uuid = channels[self.__WAITING_CHANNEL_KEY]
            queue_uuid = channels[self.__QUEUE_CHANNEL_KEY]
            self.bulletin_category = self.guild.get_channel(channels[self.__BULLETIN_CHANNEL_KEY])
            self.auth_channel: TextChannel = self.guild.get_channel(channels[self.__AUTH_CHANNEL_KEY])
            self.waiting_channel = self.guild.get_channel(waiting_uuid)
            self.queue_channel = self.guild.get_channel(queue_uuid)

            # currently we will simply record all of the lab sections, rather than keeping them in the database.
            for channel in guild.channels:
                if self.__LAB_CATEGORY_NAME in channel.name:
                    self.lab_sections[channel.name] = channel
        except KeyError:
            logger.warning("Unable to load channel authority!  Run setup!")

    def save_channels(self, bulletin_category, waiting_channel, queue_channel, auth_channel, maintenance_channel) -> None:
        self.bulletin_category = bulletin_category
        self.waiting_channel = waiting_channel
        self.queue_channel = queue_channel
        self.maintenance_channel = maintenance_channel
        self.auth_channel = auth_channel
        collection = mongo.db[self.__CHANNEL_COLLECTION]
        document = {
            self.__BULLETIN_CHANNEL_KEY: self.bulletin_category.id,
            self.__WAITING_CHANNEL_KEY: self.waiting_channel.id,
            self.__QUEUE_CHANNEL_KEY: self.queue_channel.id,
            self.__AUTH_CHANNEL_KEY: self.auth_channel.id,
            self.__MAINT_CHANNEL_KEY: self.maintenance_channel.id,
        }

        collection.delete_many({})
        collection.insert(document)

    def update_channel(self, channel_name: str, channel: GuildChannel) -> None:
        collection = mongo.db[self.__CHANNEL_COLLECTION]
        document = collection.find_one()
        document[channel_name] = channel.id
        collection.replace_one({"_id": document["_id"]}, document)

    def remove_channel(self, channel_name: str) -> None:
        collection = mongo.db[self.__CHANNEL_COLLECTION]
        document = collection.find_one()
        del document[channel_name]
        collection.replace_one({"_id": document["_id"]}, document)

    async def start_lab(self, lab_name) -> None:
        ra: RoleAuthority = RoleAuthority(self.guild)
        # Make the category channel and make it inaccessible to unauthed nerds
        self.lab_category: CategoryChannel = await self.guild.create_category(self.__LAB_CATEGORY_NAME + lab_name,
                        overwrites={
                            ra.ta: PermissionOverwrite(read_messages=False),
                            ra.student: PermissionOverwrite(read_messages=False),
                            ra.un_authenticated: PermissionOverwrite(read_messages=False)
                        })

        await self.lab_category.create_text_channel("Main Discussion")
        await self.lab_category.create_voice_channel("Main Discussion")
        for i in range(5):
            await self.lab_category.create_voice_channel("Discussion Group {}".format(i + 1))

        self.update_channel(self.__LAB_CATEGORY_NAME, self.lab_category)

    def lab_running(self) -> bool:
        return self.lab_category is not None

    async def end_lab(self, section_name):
        for channel in self.lab_category.channels:
            await channel.delete()
        await self.lab_category.delete()
        self.lab_category = None

        self.remove_channel(self.__LAB_CATEGORY_NAME)

    def add_oh_session(self, session: OHSession):
        collection = mongo.db[self.__CHANNEL_COLLECTION]
        document = collection.find_one()
        if self.__OH_SESSION_KEY not in document:
            document[self.__OH_SESSION_KEY] = {}
        document[self.__OH_SESSION_KEY][str(session.room.id)] = session.to_dict()
        collection.replace_one({"_id": document["_id"]}, document)

    def get_oh_sessions(self):
        collection = mongo.db[self.__CHANNEL_COLLECTION]
        document = collection.find_one()
        sessions = []
        for room_id, values in document[self.__OH_SESSION_KEY].items():
            session_dict = dict(values)
            session_dict["room"] = room_id
            from_dict = OHSession.from_dict(values, self.guild)
            if from_dict and from_dict.room:  # the room can be null sometimes
                sessions.append(from_dict)
        return sessions

    def remove_oh_session(self, room_id):
        collection = mongo.db[self.__CHANNEL_COLLECTION]
        document = collection.find_one()
        if self.__OH_SESSION_KEY not in document:
            document[self.__OH_SESSION_KEY] = {}
        del document[self.__OH_SESSION_KEY][str(room_id)]
        collection.replace_one({"_id": document["_id"]}, document)

    def is_cleared_channel(self, channel: TextChannel) -> bool:
        if channel in self.bulletin_category.channels:
            logger.info("Admin message in {}.  Leaving it alone.".format(channel.name))
            return True
        else:
            return False

    def is_maintenance_channel(self, channel):
        collection = mongo.db[self.__CHANNEL_COLLECTION]
        channels = collection.find_one({})
        if channel.id == channels.get(self.__MAINT_CHANNEL_KEY, -1):
            return True

        return False

