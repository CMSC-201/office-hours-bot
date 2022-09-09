import logging

from discord import Guild, TextChannel, Message, Client, CategoryChannel, PermissionOverwrite, Role
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
    __SPECIAL_SECTIONS = 'special-sections'

    __CHANNEL_NAME = 'section-name'
    __CHANNEL_ID = 'channel-id'
    __CHANNEL_STUDENT_ROLE_ID = 'student-role-id'
    __CHANNEL_LEADER_ROLE_ID = 'leader-role-id'

    def __init__(self, guild: Guild):
        self.waiting_channel: TextChannel = None
        self.queue_channel: TextChannel = None
        self.lab_sections = {}
        self.guild: Guild = guild
        self.oh_sessions = None
        self.lab_sections = {}
        self.special_sections = mongo.db[self.__SPECIAL_SECTIONS]
        self.maintenance_channel: TextChannel = None
        channels = mongo.db[self.__CHANNEL_COLLECTION].find_one()
        if not channels:
            logger.warning("Unable to load channel authority!  Run setup!")
            channels = {}

        try:
            waiting_uuid = channels[self.__WAITING_CHANNEL_KEY]
            queue_uuid = channels[self.__QUEUE_CHANNEL_KEY]
            self.bulletin_category = self.guild.get_channel(channels[self.__BULLETIN_CHANNEL_KEY])
            self.auth_channel: TextChannel = self.guild.get_channel(channels[self.__AUTH_CHANNEL_KEY])
            self.waiting_channel = self.guild.get_channel(waiting_uuid)
            self.queue_channel = self.guild.get_channel(queue_uuid)

            # currently we will simply record all of the lab sections, rather than keeping them in the database.
            for channel in guild.channels:
                if channels.get(self.__MAINT_CHANNEL_KEY, -1) == channel.id:
                    self.maintenance_channel = channel
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

    def add_special_section(self, category_channel: CategoryChannel, student_role: Role, leader_role: Role):
        channel_entry = {self.__CHANNEL_NAME: category_channel.name, self.__CHANNEL_ID: category_channel.id,
                         self.__CHANNEL_STUDENT_ROLE_ID: student_role.id, self.__CHANNEL_LEADER_ROLE_ID: leader_role.id}
        self.special_sections.insert_one(channel_entry)

    async def remove_special_section(self, section_name):
        the_section = self.special_sections.find_one({self.__CHANNEL_NAME: section_name})
        category_channel = self.guild.get_channel(the_section[self.__CHANNEL_ID])

        if the_section:
            await self.guild.get_role(the_section[self.__CHANNEL_STUDENT_ROLE_ID]).delete()
            await self.guild.get_role(the_section[self.__CHANNEL_LEADER_ROLE_ID]).delete()
            for sub_channel in category_channel.channels:
                await sub_channel.delete()
            await category_channel.delete()

        self.special_sections.delete_one({self.__CHANNEL_NAME: section_name})

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

    def find_lab_channel(self, the_category: CategoryChannel):
        current_lab_channel = None
        for lab_name in self.lab_sections:
            if the_category == self.lab_sections[lab_name]:
                current_lab_channel = self.lab_sections[lab_name]
        return current_lab_channel

    async def start_lab(self, lab_name) -> None:
        ra: RoleAuthority = RoleAuthority(self.guild)
        # Make the category channel and make it inaccessible to unauthed nerds
        self.lab_category: CategoryChannel = await self.guild.create_category(self.__LAB_CATEGORY_NAME + lab_name,
                                                                              overwrites={
                                                                                  ra.get_ta_role(): PermissionOverwrite(read_messages=False),
                                                                                  ra.get_student_role(): PermissionOverwrite(read_messages=False),
                                                                                  ra.get_unauthenticated_role(): PermissionOverwrite(read_messages=False)
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
        if channels.get(self.__MAINT_CHANNEL_KEY, -1) == -1:
            return True
        elif channel.id == channels.get(self.__MAINT_CHANNEL_KEY, -1):
            if not self.maintenance_channel:
                self.maintenance_channel = channel
            return True

        return False

    def get_maintenance_channel(self):
        # collection = mongo.db[self.__CHANNEL_COLLECTION]
        # channels = collection.find_one({})

        # collection = mongo.db[self.__CHANNEL_COLLECTION]
        # channels = collection.find_one()
        # print(channels)

        # this is a janky solution to fix this until we get the channel situation fixed.
        for channel in self.guild.text_channels:
            if channel.name == 'maintenance':
                return self.maintenance_channel

        return None
