import logging
import command

from discord import Message, Client, Member
from queues import QueueAuthority, OHSession

logger = logging.getLogger(__name__)


@command.command_class
class RetractRequest(command.Command):

    permissions = {'student': True, 'ta': True, 'admin': True}

    @command.Command.authenticate
    async def handle(self, new_message=None):
        qa: QueueAuthority = QueueAuthority(self.guild)
        if not qa.is_member_in_queue(self.message.author):
            await self.safe_send(self.message.author, "You are not in the queue.  If you want to be added, you should use the !request command. ")
            await self.safe_delete(self.message, delay=7)
            return
        elif new_message and new_message.content.strip().lower() in ['y', 'yes']:
            session: OHSession = await qa.find_and_remove_by_user_id(self.message.author)
            await self.safe_delete(session.announcement)
            await self.safe_send(self.message.author, "You have been removed from the office hour queue.  ")
            await self.safe_delete(self.message, delay=7)
            return False
        elif new_message and new_message.content.strip().lower() not in ['y', 'yes']:
            await self.safe_send(self.message.author, "You will not be removed from the queue.  ")
            return False
        else:
            await self.safe_send(self.message.channel, 'Are you sure you wish to remove yourself from the office hour queue? (y/yes) or (n/no)')
            return True

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!retract"):
            return True

        return False

    @staticmethod
    async def is_invoked_by_direct_message(message: Message, client: Client):
        if message.content.startswith("!retract"):
            return True

        return False
