import logging

from discord import Message, Client

import command
from channels import ChannelAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)


async def is_lab_command(message: Message, client: Client, keyword: str):
    ca: ChannelAuthority = ChannelAuthority(message.guild)
    if command.is_bot_mentioned(message, client) and \
            ("{} lab".format(keyword) in message.content or "lab {}".format(keyword) in message.content):
        if ca.lab_running() and keyword == "start":
            await message.channel.send("A lab is already running, " + message.author.mention + \
                                       ", please wait for it to conclude or join in.")
            return False
        if message.channel == ca.queue_channel:
            ra: RoleAuthority = RoleAuthority(message.guild)
            if ra.ta_or_higher(message.author):
                return True
            else:
                await message.channel.send("You can't do this, " + message.author.mention)
                return False
        else:
            await message.channel.send("You have to be in " + ca.queue_channel.mention + " to request a lab start.")
            return False
    return False


@command.command_class
class StartLab(command.Command):
    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        await ca.start_lab(self.message)
        logger.info("Lab started by {}".format(
            command.name(self.message.author)
        ))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return await is_lab_command(message, client, "start")


@command.command_class
class EndLab(command.Command):
    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        await ca.end_lab(self.message)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return await is_lab_command(message, client, "end")
