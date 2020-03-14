import logging

from discord import Guild, TextChannel

import mongo

logger = logging.getLogger("channels")


class ChannelAuthority:
    __WAITING_CHANNEL_KEY = "waiting"
    __QUEUE_CHANNEL_KEY = "queue"
    __CHANNEL_COLLECTION = "channels"

    def __init__(self, guild: Guild,
                 waiting_channel: TextChannel = None,
                 queue_channel: TextChannel = None):
        self.waiting_channel = waiting_channel
        self.queue_channel = queue_channel
        self.guild = guild

    async def load_channels(self):
        channels = mongo.db[self.__CHANNEL_COLLECTION].find_one()
        if not channels:
            logger.warning("Unable to load channel authority!  Run setup!")
            return
        try:
            waiting_uuid = channels[self.__WAITING_CHANNEL_KEY]
            queue_uuid = channels[self.__QUEUE_CHANNEL_KEY]

            self.waiting_channel = self.guild.get_channel(waiting_uuid)
            self.queue_channel = self.guild.get_channel(queue_uuid)
        except KeyError:
            logger.warning("Unable to load channel authority!  Run setup!")

    def save_channels(self, waiting_channel, queue_channel):
        self.waiting_channel = waiting_channel
        self.queue_channel = queue_channel
        collection = mongo.db[self.__CHANNEL_COLLECTION]
        document = {
            self.__WAITING_CHANNEL_KEY: self.waiting_channel.id,
            self.__QUEUE_CHANNEL_KEY: self.queue_channel.id,
        }
        collection.delete_many({})
        collection.insert(document)
