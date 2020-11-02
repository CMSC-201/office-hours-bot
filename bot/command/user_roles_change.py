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
class AddUserRole(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __DISCORD_ID = 'discord'
    __UMBC_ID = 'UMBC-Name-Id'

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.message.guild)
        ca: ChannelAuthority = ChannelAuthority(self.message.guild)
        if ra.admin and ca.is_maintenance_channel(self.message.channel):
            students_group = mongo.db[self.__STUDENTS_GROUP]
            ta_group = mongo.db[self.__TA_GROUP]
            admin_group = mongo.db[self.__ADMIN_GROUP]

            split_message = self.message.content.split()
            role_name = split_message[3]
            user_name = split_message[4]
            group_names = [self.__ADMIN_GROUP, self.__TA_GROUP, self.__STUDENTS_GROUP]
            if role_name not in ra.role_map:
                await self.message.channel.send("The group %s name wasn't found." % role_name)
                return

            found_student = students_group.find_one({self.__UMBC_ID: user_name})
            found_ta = ta_group.find_one({self.__UMBC_ID: user_name})
            found_admin = admin_group.find_one({self.__UMBC_ID: user_name})

            if found_student:
                member = self.message.guild.get_member(found_student[self.__DISCORD_ID])
                await ra.add_role(member, role_name)
                await self.message.channel.send('Updated user %s with role %s' % (user_name, role_name))
            elif found_ta:
                member = self.message.guild.get_member(found_ta[self.__DISCORD_ID])
                await ra.add_role(member, role_name)
                await self.message.channel.send('Updated user %s with role %s' % (user_name, role_name))
            elif found_admin:
                member = self.message.guild.get_member(found_admin[self.__DISCORD_ID])
                await ra.add_role(member, role_name)
                await self.message.channel.send('Updated user %s with role %s' % (user_name, role_name))
            else:
                await self.message.channel.send('Unable to find user %s' % user_name)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!user role add") and len(message.content.split()) == 5:
            return True

        return False


@command.command_class
class RemoveUserRole(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __DISCORD_ID = 'discord'
    __UMBC_ID = 'UMBC-Name-Id'

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.message.guild)
        ca: ChannelAuthority = ChannelAuthority(self.message.guild)
        if ra.admin and ca.is_maintenance_channel(self.message.channel):
            students_group = mongo.db[self.__STUDENTS_GROUP]
            ta_group = mongo.db[self.__TA_GROUP]
            admin_group = mongo.db[self.__ADMIN_GROUP]

            split_message = self.message.content.split()
            role_name = split_message[3]
            user_name = split_message[4]
            if role_name not in ra.role_map:
                await self.message.channel.send("The group %s name wasn't found." % role_name)
                return

            found_student = students_group.find_one({self.__UMBC_ID: user_name})
            found_ta = ta_group.find_one({self.__UMBC_ID: user_name})
            found_admin = admin_group.find_one({self.__UMBC_ID: user_name})

            if found_student:
                member = self.message.guild.get_member(found_student[self.__DISCORD_ID])
                await ra.remove_role(member, role_name)
                await self.message.channel.send('Updated user %s by removing role %s' % (user_name, role_name))
            elif found_ta:
                member = self.message.guild.get_member(found_ta[self.__DISCORD_ID])
                await ra.remove_role(member, role_name)
                await self.message.channel.send('Updated user %s by removing role %s' % (user_name, role_name))
            elif found_admin:
                member = self.message.guild.get_member(found_admin[self.__DISCORD_ID])
                await ra.remove_role(member, role_name)
                await self.message.channel.send('Updated user %s by removing role %s' % (user_name, role_name))
            else:
                await self.message.channel.send('Unable to find user %s' % user_name)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client) -> bool:
        if message.content.startswith("!user role remove") and len(message.content.split()) == 5:
            return True

        return False
