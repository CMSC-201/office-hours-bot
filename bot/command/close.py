import logging

from discord import Message, Client, CategoryChannel

import command
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


@command.command_class
class EndOHSession(command.Command):
    async def handle(self):
        await self.message.channel.send("Closing")
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        category_channel: CategoryChannel = None

        # find the correct session
        this_session = None
        for session in await ca.get_oh_sessions():
            if self.message.channel in session.room.channels:
                this_session = session
                category_channel = session.room

        # delete the role
        await this_session.role.delete()

        # delete the channels
        for room in category_channel.channels:
            await room.delete()
        await category_channel.delete()

        # remove the session from mongo
        ca.remove_oh_session(category_channel.id)
        logger.info("OH session in room {} closed by {}".format(
            category_channel.id,
            command.name(self.message.author)))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!close"):
            ca: ChannelAuthority = ChannelAuthority(message.guild)
            for session in await ca.get_oh_sessions():
                if message.channel in session.room.channels:
                    return True
        return False
