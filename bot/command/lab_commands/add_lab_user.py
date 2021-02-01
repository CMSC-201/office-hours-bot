import logging

from discord import Message, Client, Attachment, Guild, PermissionOverwrite, TextChannel, CategoryChannel, Member, File
from datetime import datetime, timedelta
import csv
import re
import os

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority, PermissionAuthority

logger = logging.getLogger(__name__)


@command.command_class
class AddToLabSection(command.Command):
    __SECTION = 'Section'
    __SECTION_DATA = 'section-data'
    __DISCORD_ID = 'discord'
    __SECTION_STRING = 'Lab {}'

    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        split_message = self.message.content.split()
        if len(split_message) != 5:
            await self.message.channel.send('The format for the command is !lab add user [username] [section number]')
            return
        if ca.is_maintenance_channel(self.message.channel) and ra.is_admin(self.message.author):

            username = self.message.content.split()[3]
            section_number = split_message[4]
            await self.message.channel.send('Adding {} to section {}'.format(username, section_number))

            students_group = mongo.db[self.__STUDENTS_GROUP]
            ta_group = mongo.db[self.__TA_GROUP]
            found_student = students_group.find_one({self.__USERNAME: username})
            found_ta = ta_group.find_one({self.__USERNAME: username})
            pa: PermissionAuthority = PermissionAuthority()

            if found_student:
                student = await self.get_member(found_student[self.__DISCORD_ID])
                await ca.lab_sections[self.__SECTION_STRING.format(section_number)].set_permissions(student, overwrite=pa.student_overwrite)
            elif found_ta:
                ta = await self.get_member(found_ta[self.__DISCORD_ID])
                await ca.lab_sections[self.__SECTION_STRING.format(section_number)].set_permissions(ta, overwrite=pa.ta_overwrite)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!lab add user'):
            return True
        return False

    @classmethod
    def get_help(cls):
        return "This command adds a user to a lab section. \n Command Format: !lab add user <username> <section>"
