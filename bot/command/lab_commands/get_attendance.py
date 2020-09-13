import logging

from discord import Message, Client, Attachment, Guild, PermissionOverwrite, TextChannel, CategoryChannel, Member, File
from datetime import datetime, timedelta
import csv
import os
import re

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority, PermissionAuthority

logger = logging.getLogger(__name__)


@command.command_class
class GetAttendance(command.Command):
    __SECTION = 'Section'
    __SECTION_DATA = 'section-data'
    __CHECK_IN_DATA = 'check-in-data'
    __DISCORD_ID = 'discord'
    __SECTION_STRING = 'Lab {}'

    __ALLOW_SECOND_CHECKIN = 'allow-second-checkin'
    __FIRST_CHECK_IN = 1
    __SECOND_CHECK_IN = 2
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)

        lab_channel: CategoryChannel = ca.find_lab_channel(self.message.channel.category)

        check_in_collection = mongo.db[self.__CHECK_IN_DATA]

        match = re.match(r'!lab\s+((?P<section>\d{2})\s+)?get\s+attendance\s+(?P<date_code>\d{8})', self.message.content)

        if not ra.ta_or_higher(self.message.author):
            await self.message.author.send('You do not have permission to run the command.')
        elif match:
            print(lab_channel)
            section_name = self.__SECTION_STRING.format(match.group('section'))
            check_in_record = check_in_collection.find_one({'Section Name': section_name, 'Date': int(match.group('date_code'))})
            if check_in_record:
                print(check_in_record)
            else:
                print('Couldn\'t find the check in record for that date')
        else:
            await self.message.author.send('The format of the command is wrong.')

        await self.message.delete(delay=2)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        match = re.match(r'!lab\s+((?P<section>\d{2})\s+)?get\s+attendance\s+(?P<date_code>\d{8})', message.content)
        if match:
            return True
        return False
