"""
    This is intended an one time use office-hour creator only.  It doesn't create the roles, we must assign them manually.

"""

import logging

from discord import Message, Client, Member, TextChannel, CategoryChannel
from typing import Optional

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class SetupCommand(command.Command):
    __CHANNEL_COLLECTION = "channels"

    async def handle(self):
        author: Member = self.message.author
        if not author.guild_permissions.administrator:
            await self.message.channel.send("You must have administrator permissions in the server to run this command.")
            return

        admin_category = "Administration"
        staff_category = "Instruction"
        student_category = "Course Rooms"
        waiting_room_name = "waiting-room"
        queue_room_name = "student-requests"
        maintenance_channel_name = 'maintenance'
        channel_structure = {
            admin_category: {
                "text": ['maintenance'],
                "voice": []
            },
            staff_category: {
                "text": [queue_room_name],
                "voice": [],
            },
            student_category: {
                "text": [waiting_room_name],
                "voice": [],
            }
        }

        categories = {}
        all_channels = {}  # Replicates channel_structure, but with Channel objects
        waiting_room: Optional[TextChannel] = None
        queue_room: Optional[TextChannel] = None
        maintenance_channel: Optional[TextChannel] = None
        for category, channels in channel_structure.items():
            text, voice = (channels["text"], channels["voice"])
            category_channel: CategoryChannel = await self.guild.create_category(category)

            categories[category] = category_channel
            all_channels[category] = {"text": {}, "voice": {}}

            for name in text:
                channel = await category_channel.create_text_channel(name)
                if name == maintenance_channel_name:
                    maintenance_channel = channel
                elif name == queue_room_name:
                    queue_room = channel
                elif name == waiting_room_name:
                    waiting_room = channel

                all_channels[category]["text"][name] = channel
                logger.info("Created text channel {} in category {}".format(name, category))

            for name in voice:
                await category_channel.create_voice_channel(name)
                all_channels[category]["voice"][name] = channel
                logger.info("Created voice channel {} in category {}".format(name, category))

        collection = mongo.db[self.__CHANNEL_COLLECTION]
        channel_entry = {
            self.__BULLETIN_CHANNEL_KEY: 0,
            self.__WAITING_CHANNEL_KEY: waiting_room,
            self.__QUEUE_CHANNEL_KEY: queue_room,
            self.__AUTH_CHANNEL_KEY: 0,
            self.__MAINT_CHANNEL_KEY: maintenance_channel.id,
        }
        collection.delete_many({})
        collection.insert_one(channel_entry)

        await maintenance_channel.send("Righto! You're good to go, boss!")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        ca: ChannelAuthority = ChannelAuthority(message.guild)
        if command.is_bot_mentioned(message, client) and ("office hours only startup" in message.content):
            if ca.waiting_channel is None:
                return True

            await message.channel.send("You can't run setup, " + message.author.mention)
            return False

        return False
