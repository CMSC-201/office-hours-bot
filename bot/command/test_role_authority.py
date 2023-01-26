import logging

from discord import Message, Client, Colour, Embed

import re
import command
import mongo
from roles import RoleAuthority

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
        role_authority: RoleAuthority = RoleAuthority(self.message.guild)

        if not role_authority.get_unauthenticated_role():
            await self.message.channel.send("Unauthenticated Role is None")
        else:
            await self.message.channel.send(str(role_authority.get_unauthenticated_role().id))
            await self.message.channel.send("Unauthenticated Role Exists")
            await self.message.channel.send(', '.join([str(r.id) for r in self.message.guild.roles]))

        if not role_authority.get_student_role():
            await self.message.channel.send("Student Role is None")
        else:
            await self.message.channel.send("Student Role Exists")

        if not role_authority.get_ta_role():
            await self.message.channel.send("TA Role is None")
        else:
            await self.message.channel.send("TA Role Exists")
        if not role_authority.get_admin_role():
            await self.message.channel.send("Admin Role is None")
        else:
            await self.message.channel.send("Admin Role Exists")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!test role authority"):
            return True

        return False

