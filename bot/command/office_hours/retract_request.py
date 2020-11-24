import logging
from datetime import datetime as dt

import discord
from discord import Message, Client, Member
from datetime import datetime, timedelta, tzinfo, timezone

import command
from channels import ChannelAuthority
from roles import RoleAuthority
from queues import QueueAuthority, OHSession

logger = logging.getLogger(__name__)


@command.command_class
class RetractRequest(command.Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.message.guild)

        if self.message.channel == ca.waiting_channel:
            if not qa.is_member_in_queue(self.message.author):
                await self.safe_send(self.message.author, "You are not in the queue.  If you want to be added, you should use the !request command. ")
                await self.safe_delete(self.message, delay=7)
                return

            else:
                session: OHSession = await qa.find_and_remove_by_user_id(self.message.author)
                await self.safe_delete(session.announcement)
                await self.safe_delete(self.message, delay=7)
                await self.safe_send(self.message.author, "You have been removed from the office hour queue.  ")
        else:
            await self.safe_send(self.message.author, "Your request-retract should be done in the waiting channel.  ")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!retract"):
            return True

        return False
