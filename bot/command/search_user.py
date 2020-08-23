import logging

from discord import Message, Client

import re
import command
import mongo
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority
from member import MemberAuthority


logger = logging.getLogger(__name__)


@command.command_class
class SearchUsers(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.message.guild)
        if ra.admin:
            students_group = mongo.db[self.__STUDENTS_GROUP]
            ta_group = mongo.db[self.__TA_GROUP]
            admin_group = mongo.db[self.__ADMIN_GROUP]

            for group in [students_group, ta_group, admin_group]:
                match = re.match(r'!search\s+user\s+(?P<user_identifier>\w+)', self.message.content)
                first_name_list = [first_name_user for first_name_user in group.find({'First-Name': match.group('user_identifier')})]
                last_name_list = [first_name_user for first_name_user in group.find({'Last-Name': match.group('user_identifier')})]
                umbc_id_list = [user for user in group.find({'UMBC-Name-Id': match.group('user_identifier')})]
                print(first_name_list + last_name_list + umbc_id_list)

        # gives a NotFound Exception??
        # await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!search user"):
            return True

        return False
