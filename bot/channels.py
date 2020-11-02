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
    __LAB_CATEGORY_CHANNEL = "lab"
    __OH_SESSION_KEY = "oh_sessions"
    __AUTH_CHANNEL_KEY = "auth"
    __BULLETIN_CHANNEL_KEY = "bulletin"

    def __init__(self, guild: Guild):
        self.waiting_channel: TextChannel = None
        self.queue_channel: TextChannel = None
        self.lab_category: CategoryChannel = None
        self.guild = guild
        self.oh_sessions = None
        channels = mongo.db[self.__CHANNEL_COLLECTION].find_one()
        if not channels:
            logger.warning("Unable to load channel authority!  Run setup!")
            return
        try:
            waiting_uuid = channels[self.__WAITING_CHANNEL_KEY]
            queue_uuid = channels[self.__QUEUE_CHANNEL_KEY]

            if self.__LAB_CATEGORY_CHANNEL in channels:
                self.lab_category = self.guild.get_channel(channels[self.__LAB_CATEGORY_CHANNEL])

            self.bulletin_category = self.guild.get_channel(channels[self.__BULLETIN_CHANNEL_KEY])
            self.auth_channel: TextChannel = self.guild.get_channel(channels[self.__AUTH_CHANNEL_KEY])
            self.waiting_channel = self.guild.get_channel(waiting_uuid)
            self.queue_channel = self.guild.get_channel(queue_uuid)
        except KeyError:
            logger.warning("Unable to load channel authority!  Run setup!")

    def save_channels(self, bulletin_category, waiting_channel, queue_channel, auth_channel) -> None:
        self.bulletin_category = bulletin_category
        self.waiting_channel = waiting_channel
        self.queue_channel = queue_channel
        self.auth_channel = auth_channel
        collection = mongo.db[self.__CHANNEL_COLLECTION]
        document = {
            self.__BULLETIN_CHANNEL_KEY: self.bulletin_category.id,
            self.__WAITING_CHANNEL_KEY: self.waiting_channel.id,
            self.__QUEUE_CHANNEL_KEY: self.queue_channel.id,
            self.__AUTH_CHANNEL_KEY: self.auth_channel.id,
        }
        if self.lab_category:
            document[self.__LAB_CATEGORY_CHANNEL] = self.lab_category.id

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

    async def start_lab(self, message: Message) -> None:
        guild: Guild = message.guild
        ra: RoleAuthority = RoleAuthority(guild)
        # Make the category channel and make it inaccessible to unauthed nerds
        self.lab_category: CategoryChannel = await guild.create_category("Lab", overwrites={
            ra.un_authenticated: PermissionOverwrite(read_messages=False)
        })

        await self.lab_category.create_text_channel("General")
        await self.lab_category.create_voice_channel("Main Lecture")
        for i in range(1, 7):
            await self.lab_category.create_voice_channel("Small Group Chat " + str(i))

        self.update_channel(self.__LAB_CATEGORY_CHANNEL, self.lab_category)

    def lab_running(self) -> bool:
        return self.lab_category is not None

    async def end_lab(self, message):
        for channel in self.lab_category.channels:
            await channel.delete()
        await self.lab_category.delete()
        self.lab_category = None

        self.remove_channel(self.__LAB_CATEGORY_CHANNEL)

    def add_oh_session(self, session: OHSession):
        collection = mongo.db[self.__CHANNEL_COLLECTION]
        document = collection.find_one()
        if self.__OH_SESSION_KEY not in document:
            document[self.__OH_SESSION_KEY] = {}
        document[self.__OH_SESSION_KEY][str(session.room.id)] = session.to_dict()
        collection.replace_one({"_id": document["_id"]}, document)

    async def get_oh_sessions(self):
        collection = mongo.db[self.__CHANNEL_COLLECTION]
        document = collection.find_one()
        sessions = []
        for room_id, values in document[self.__OH_SESSION_KEY].items():
            session_dict = dict(values)
            session_dict["room"] = room_id
            from_dict = await OHSession.from_dict(values, self.guild)
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

