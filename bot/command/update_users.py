import logging

from discord import Message, Client

import command
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class UpdateUsers(command.Command):
    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.message.guild)
        if ra.admin:
            pass

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!update users"):
            return True

        return False
