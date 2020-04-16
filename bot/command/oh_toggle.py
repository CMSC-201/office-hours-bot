import logging

from discord import Message, Client

import command
from channels import ChannelAuthority
from queues import QueueAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)


async def is_oh_command(client, message, types):
    ca: ChannelAuthority = ChannelAuthority(message.guild)
    has_command = False
    for type in types:
        if type in message.content.lower():
            has_command = True
    if command.is_bot_mentioned(message, client) and "oh" in message.content.lower() and has_command:
        if message.channel == ca.queue_channel:
            ra: RoleAuthority = RoleAuthority(message.guild)
            if ra.ta_or_higher(message.author):
                return True
            else:
                await message.channel.send("You can't do this, " + message.author.mention)
                return False
        else:
            await message.channel.send("You have to be in " +
                                       ca.queue_channel.mention + " to {} office hours.".format(types))
            return False
    return False


@command.command_class
class StartOfficeHours(command.Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        # Add TA to list of available TAs. Return True if fresh opening, True if newly added TA
        fresh_open, is_new_ta = qa.open_office_hours(self.message.author.id)
        if fresh_open:
            await ca.queue_channel.send("Office hours are live!")
            await ca.waiting_channel.send(
                "Office hours are live.  Get in line with !request")
            logger.info("Office hours opened by {}".format(
                command.name(self.message.author)
            ))
        if is_new_ta:
            await ca.queue_channel.send(command.name(self.message.author) + " has checked into office hours!")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return await is_oh_command(client, message, ["start", "open"])



@command.command_class
class EndOfficeHours(command.Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        # Remove TA from list of available TAs.

        if "force" in self.message.content:
            qa.force_close_office_hours()
            await ca.queue_channel.send(command.name(self.message.author) + " has forced OH to close.")
            await ca.waiting_channel.send(
                "Ok, y'all.  Office hours have ended for now.  An announcement will appear here when they have reopened.")
            return

        is_open, was_removed, ta_count = qa.close_office_hours(self.message.author.id)
        if ta_count > 0 and is_open and was_removed:
            await ca.queue_channel.send(command.name(self.message.author) + " has checked out of office hours.")
        # Last TA was removed, or TA queue was empty when called
        elif ta_count <= 0 and is_open:
            await qa.remove_all()
            await ca.queue_channel.send(command.name(self.message.author) + " has closed office hours!")
            await ca.waiting_channel.send(
                "Ok, y'all.  Office hours have ended for now.  An announcement will appear here when they have reopened.")
            logger.info("Office hours closed by {}".format(
                command.name(self.message.author)
            ))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return await is_oh_command(client, message, ["end", "close"])
