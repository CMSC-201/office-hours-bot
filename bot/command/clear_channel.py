import logging

from discord import Message, Client, Member, User

import command
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class ClearChannel(command.Command):

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    async def handle(self):
        if self.message.content.strip().lower() == '!clear all':
            await self.message.channel.purge(limit=None)
        elif self.message.content.strip().lower() == '!clear all but pinned':
            await self.message.channel.purge(limit=None, check=lambda x: not x.pinned)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!clear"):
            return True

        return False
