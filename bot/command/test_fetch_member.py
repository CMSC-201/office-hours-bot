import logging

from discord import Message, Client, Colour, Embed

import re
import command
import mongo
from datetime import datetime as dt
from datetime import timedelta
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority
from member import MemberAuthority
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


@command.command_class
class TestFetchMember(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __DISCORD_ID = 'discord'
    __DROPPED = 'dropped'
    __UID_FIELD = 'UMBC-Name-Id'

    permissions = {'student': False, 'ta': False, 'admin': True}

    def search_database(self, criteria):
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        found_list = []

        for group in [students_group, ta_group, admin_group]:
            found_list.extend([first_name_user for first_name_user in group.find(criteria)])
        return found_list

    @command.Command.require_maintenance
    async def handle(self):
        general_match = re.match(r'!test\s+fetch\s+member\s+(?P<user_identifier>(.*))', self.message.content)

        if not general_match:
            await self.message.channel.send("Format is !test fetch member [member username]")
            return

        found_list = self.search_database({self.__UID_FIELD: general_match.group('user_identifier')})
        print(found_list)
        for db_member in found_list:
            member = await self.message.guild.fetch_member(db_member[self.__DISCORD_ID])
            if member:
                await self.message.channel.send(str(member))
            else:
                await self.message.channel.send(db_member[self.__UID_FIELD])

        if not found_list:
            print('No members were found in the database, no test was run.')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!test fetch member"):
            return True

        return False

