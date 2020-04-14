import logging
from datetime import datetime as dt

import discord
from discord import Message, Client, Member

import command
from channels import ChannelAuthority
from queues import QueueAuthority

logger = logging.getLogger(__name__)


@command.command_class
class EnterQueue(command.Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        request = "[Student did not supply text]"
        if " " in self.message.content:
            # remove the !request from the front of the message
            request = " ".join(self.message.content.split()[1:])

        ca: ChannelAuthority = ChannelAuthority(self.guild)

        # Build embedded message
        color = discord.Colour(0).blue()
        embeddedMsg = discord.Embed(description=request,
                                    timestamp=dt.now(),
                                    colour=color)

        author: Member = self.message.author
        embeddedMsg.set_author(name=command.name(author))
        embeddedMsg.add_field(name="Accept request by typing",
                              value="!accept")
        embeddedMsg.add_field(name="Reject request by typing",
                              value="!reject {} [text to be sent to student]".format(author.id))
        # Send embedded message
        announcement = await ca.queue_channel.send(embed=embeddedMsg)
        qa.add_to_queue(author, request, announcement)
        await self.message.delete()
        logger.info("{} added to queue with request text: {}".format(
            command.name(author),
            request
        ))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        ca: ChannelAuthority = ChannelAuthority(message.guild)
        if message.content.startswith("!request"):
            qa: QueueAuthority = QueueAuthority(message.guild)
            if not qa.is_office_hours_open():
                warning = await message.channel.send(
                    "Office hours are closed.  Please try again after they have opened.".format(
                        message.author.mention,
                        ca.waiting_channel.mention))
                await warning.delete(delay=7)
                await message.delete()
                return False
            if qa.is_member_in_queue(message.author):
                warning = await message.channel.send(
                    "{} you are already in the queue.  Please continue waiting.".format(
                        message.author.mention,
                        ca.waiting_channel.mention))
                await warning.delete(delay=7)
                await message.delete()
                return False
            if message.channel == ca.waiting_channel:
                return True
            else:
                warning = await message.channel.send("{} you must be in {} to request a place in the queue.".format(
                    message.author.mention,
                    ca.waiting_channel.mention))
                await warning.delete(delay=7)
                await message.delete()
                return False
        return False
