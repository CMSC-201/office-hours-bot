import logging

from pymongo.results import DeleteResult, UpdateResult

from discord import Message, Client, Member, User
from discord.errors import NotFound

import re
import command
import mongo
from roles import RoleAuthority
from member import MemberAuthority
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


@command.command_class
class RecheckRoles(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'TA'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'
    __DISCORD_ID = 'discord'
    __ROLE = 'Role'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'

    permissions = {'student': False, 'ta': False, 'admin': True}

    async def add_member_to_group(self, role_authority: RoleAuthority, discord_id, discord_group_name, group_name):
        """
            :param role_authority:
            :param member: the member to check
            :param group_name: the discord name for the group
            :param group_string: the internal name of the group
            :return: 1 if done, 0 if not
        """
        member: Member = await self.guild.fetch_member(discord_id)
        if not any(role.name == discord_group_name for role in member.roles):
            await role_authority.add_role(member, group_name)
            await self.message.channel.send(f'{discord_group_name} was not in {member.display_name}\'s list of roles, added.')
            return 1
        return 0


    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        role_authority: RoleAuthority = RoleAuthority(self.guild)

        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        __ADMIN_NAME = "Admin"
        __STUDENT_NAME = "Student"
        __TA_NAME = "TA"

        num_modified = 0

        for group in [students_group, ta_group, admin_group]:
            for person in group.find():
                try:
                    if person[self.__DISCORD_ID]:
                        if person[self.__ROLE] == self.__ADMIN_GROUP:
                            num_modified += await self.add_member_to_group(role_authority, person[self.__DISCORD_ID], __ADMIN_NAME, self.__ADMIN_GROUP)
                        elif person[self.__ROLE] == self.__TA_GROUP:
                            num_modified += await self.add_member_to_group(role_authority, person[self.__DISCORD_ID], __TA_NAME, self.__TA_GROUP)
                        elif person[self.__ROLE] == self.__STUDENTS_GROUP:
                            num_modified += await self.add_member_to_group(role_authority, person[self.__DISCORD_ID], __STUDENT_NAME, self.__STUDENTS_GROUP)
                except NotFound:
                    await self.message.channel.send(f"{person[self.__FIRST_NAME]} {person[self.__LAST_NAME]} {person[self.__UID_FIELD]} was not found, possibly is not in the server anymore.")
        await self.message.channel.send(f'{num_modified} roles were added')


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!recheck roles"):
            return True

        return False
