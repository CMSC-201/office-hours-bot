import logging

from discord import Message, Client, Attachment, Guild, PermissionOverwrite, TextChannel, CategoryChannel, Member, File
from datetime import datetime, timedelta
import csv
import os
import re
from pymongo.results import UpdateResult, DeleteResult

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority, PermissionAuthority

logger = logging.getLogger(__name__)

@command.command_class
class AllowCheckIn(command.Command):
    __SECTION = 'Section'
    __SECTION_DATA = 'section-data'
    __CHECK_IN_DATA = 'check-in-data'
    __DISCORD_ID = 'discord'
    __SECTION_STRING = 'Lab {}'

    __ALLOW_SECOND_CHECKIN = 'allow-second-checkin'
    __FIRST_CHECK_IN = 1
    __SECOND_CHECK_IN = 2
    __TA_GROUP = 'ta'
    __ADMIN_GROUP = 'admin'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'
    __WEEKDAY_MAP = {0: 'M', 1: 'Tu', 2: 'W', 3: 'Th', 4: 'F', 5: 'Sa', 6: 'Su'}

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)

        current_lab_channel = None
        section_name = ''
        the_category: CategoryChannel = self.message.channel.category
        for lab_name in ca.lab_sections:
            if the_category == ca.lab_sections[lab_name]:
                current_lab_channel = ca.lab_sections[lab_name]
                section_name = lab_name

        students_group = mongo.db[self.__STUDENTS_GROUP]
        # ta_group = mongo.db[self.__TA_GROUP]
        # admin_group = mongo.db[self.__ADMIN_GROUP]
        section_collection = mongo.db[self.__SECTION_DATA]
        check_in_collection = mongo.db[self.__CHECK_IN_DATA]

        today = datetime.today()

        match = re.match(r'!lab\s+remove\s+session\s+(?P<date_code>\d+)', self.message.content)
        if ra.ta_or_higher(self.message.author) and current_lab_channel and match:
            date_code = int(match.group('date_code'))
            print(date_code)
            # we're in the right section, now we need to check that it's the right time
            dr: DeleteResult = check_in_collection.delete_one({'Section Name': section_name, 'Date': date_code})
            if dr.deleted_count:
                await self.message.author.send("Erased the discussion section for {}".format(date_code))
            else:
                for session in check_in_collection.find({'Section Name': section_name}):
                    print(session)

        elif not ra.ta_or_higher(self.message.author):
            await self.message.author.send("We were unable to find you. You are either not a TA, or otherwise unable to run this command.  ")
        elif not current_lab_channel:
            await self.message.author.send("We couldn't find this section.  Did you send this in your lab channel?")

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!lab remove session'):
            return True
        return False