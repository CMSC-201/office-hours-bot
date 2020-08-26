import logging

from discord import Message, Client, Member, User

import command
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class ClearChannel(command.Command):

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.message.guild)

        def not_pinned(msg: Message):
            return not msg.pinned

        if ra.is_admin(self.message.author):
            if self.message.content.strip().lower() == '!clear all':
                await self.message.channel.purge()
            elif self.message.content.strip().lower() == '!clear all but pinned':
                await self.message.channel.purge(check=not_pinned)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!clear"):
            return True

        return False
