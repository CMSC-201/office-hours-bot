import logging

from discord import Message, Client

import re
import command
import mongo
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority
from member import MemberAuthority
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


@command.command_class
class SearchUsers(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.message.guild)
        ca: ChannelAuthority = ChannelAuthority(self.message.guild)
        if ra.is_admin(self.message.author) and ca.is_maintenance_channel(self.message.channel):
            students_group = mongo.db[self.__STUDENTS_GROUP]
            ta_group = mongo.db[self.__TA_GROUP]
            admin_group = mongo.db[self.__ADMIN_GROUP]

            first_name_list = []
            last_name_list = []
            umbc_id_list = []

            for group in [students_group, ta_group, admin_group]:
                match = re.match(r'!search\s+user\s+(?P<user_identifier>\w+)', self.message.content)
                first_name_list.extend([first_name_user for first_name_user in group.find({'First-Name': match.group('user_identifier')})])
                last_name_list.extend([first_name_user for first_name_user in group.find({'Last-Name': match.group('user_identifier')})])
                umbc_id_list.extend([user for user in group.find({'UMBC-Name-Id': match.group('user_identifier')})])

            combined_list = first_name_list + last_name_list + umbc_id_list
            message = '\n'.join([str(record) for record in combined_list])
            if message:
                await self.message.channel.send(message)
            else:
                await self.message.channel.send('No results were found')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!search user"):
            return True

        return False
