import logging
from datetime import datetime as dt

import discord
from discord import Message, Client, Member
from datetime import datetime, timedelta, tzinfo, timezone

import command
from channels import ChannelAuthority
from roles import RoleAuthority
from queues import QueueAuthority

logger = logging.getLogger(__name__)


@command.command_class
class EnterQueue(command.Command):

    async def notify_on_duty_tas(self):
        pass

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
                                    timestamp=dt.now() + timedelta(hours=5),
                                    colour=color)

        author: Member = self.message.author
        embeddedMsg.set_author(name=command.name(author))
        embeddedMsg.add_field(name="Accept request by typing",
                              value="!accept")
        embeddedMsg.add_field(name="Reject request by typing",
                              value="!reject {} [text to be sent to student]".format(author.id))

        announcement = await ca.queue_channel.send(embed=embeddedMsg)

        await self.safe_send(self.message.author, 'You are now entered in the queue.  A TA should be available to help you shortly.', backup=self.message.channel)
        request_id = 0

        qa.add_to_queue(author, request, announcement)
        # self.client.statistics.record_office_hour_request(request_id, self.message.author, request, dt.now())

        await self.safe_delete(self.message)
        logger.info("{} added to queue with request text: {}".format(
            command.name(author),
            request
        ))

        await self.notify_on_duty_tas()


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        ca: ChannelAuthority = ChannelAuthority(message.guild)

        if message.content.startswith("!request") and message.channel == ca.waiting_channel:
            qa: QueueAuthority = QueueAuthority(message.guild)
            if len(message.content.split()) == 1:
                warning = await message.channel.send("You must ask a question so we can know how to help you.  The format should be !request <your question here>")
                await warning.delete(delay=7)
                await message.delete()
                return False
            elif not qa.is_office_hours_open():
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
            return True
        elif message.channel == ca.waiting_channel and not message.content.startswith('!status'):
            ra: RoleAuthority = RoleAuthority(message.guild)
            if not ra.ta_or_higher(message.author):
                await message.author.send('You should reserve this channel for office hour requests only.  Ask your question in general, tech-support or request help using the office hour system.  ')
                await message.delete(delay=10)
        elif message.content.startswith("!request"):
            warning = await message.channel.send("{} you must be in {} to request a place in the queue.".format(
                message.author.mention,
                ca.waiting_channel.mention))
            await warning.delete(delay=7)
            await message.delete()
        return False
