import logging
import re
import datetime as dt

from discord import Guild, Message, Client, Member, User, Embed, Colour, TextChannel, VoiceChannel, CategoryChannel

import command
import mongo
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


@command.command_class
class DetectChannels(command.Command):
    __CHANNEL_COLLECTION = "channels"

    # these are the names of the channels to the user
    __BULLETIN_NAME = 'bulletin'
    __MAINTENANCE_NAME = 'maintenance'
    __WAITING_ROOM_NAME = 'waiting-room'
    __STUDENT_REQUESTS = 'student-requests'

    # these are the keys used in the database
    __WAITING_CHANNEL_KEY = "waiting"
    __QUEUE_CHANNEL_KEY = "queue"
    __BULLETIN_CHANNEL_KEY = "bulletin"
    __MAINT_CHANNEL_KEY = 'maint'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    async def handle(self):
        the_match = re.match(r'!set\s+channel\s+name=(?P<channel_name>(\w|-)+)\s+id=(?P<channel_id>\d+)', self.message.content)

        if the_match:
            collection = mongo.db[self.__CHANNEL_COLLECTION]
            channel_ids = collection.find_one()

            if not channel_ids:
                await self.message.channel.send('Unable to find database entry for primary channels, creating... ')
                collection.insert_one({
                    self.__BULLETIN_CHANNEL_KEY: 0,
                    self.__WAITING_CHANNEL_KEY: 0,
                    self.__QUEUE_CHANNEL_KEY: 0,
                    self.__MAINT_CHANNEL_KEY: 0,
                })
                channel_ids = collection.find_one()

            channel_id = the_match.group('channel_id')
            if the_match.group('channel_name') == self.__BULLETIN_NAME:
                collection.update_one({'_id': channel_ids['_id']}, {'$set': {self.__BULLETIN_CHANNEL_KEY: channel_id}})
            elif the_match.group('channel_name') == self.__MAINTENANCE_NAME:
                collection.update_one({'_id': channel_ids['_id']}, {'$set': {self.__MAINT_CHANNEL_KEY: channel_id}})
            elif the_match.group('channel_name') == self.__STUDENT_REQUESTS:
                collection.update_one({'_id': channel_ids['_id']}, {'$set': {self.__QUEUE_CHANNEL_KEY: channel_id}})
            elif the_match.group('channel_name') == self.__WAITING_ROOM_NAME:
                collection.update_one({'_id': channel_ids['_id']}, {'$set': {self.__WAITING_CHANNEL_KEY: channel_id}})
            else:
                await self.message.channel.send('Room name not recognized, options are: bulletin, maintenance, waiting-room, or student-request. ')
        else:
            await self.message.channel.send('Unable to match command.  Usage: \n !set channel name = [channel name] id = [channel id]\n\t where name = bulletin, maintenance, waiting-room, or student-requests')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!set channel"):
            return True

        return False
