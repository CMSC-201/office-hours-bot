import logging

from discord import Message, Client

import regex
import command
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class SearchUsers(command.Command):
    async def handle(self):

        ra: RoleAuthority = RoleAuthority(self.message.guild)
        if ra.admin:
            match = regex.match(r'!search\s+user\s+(?P<user_identifier>\w+)', self.message.content)
            first_name_list = [first_name_user for first_name_user in self.user_collection.find({'First-Name': match.group('user_identifier')})]
            print(first_name_list)
            last_name_list = [first_name_user for first_name_user in self.user_collection.find({'Last-Name': match.group('user_identifier')})]
            print(last_name_list)
            umbc_id_list = [user for user in self.user_collection.find({'UMBC-Name-Id': match.group('user_identifier')})]
            print(umbc_id_list)

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!search user"):
            return True

        return False
