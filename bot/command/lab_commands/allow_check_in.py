import logging

from discord import Message, Client, Attachment, Guild, PermissionOverwrite, TextChannel, CategoryChannel, Member, File
from discord.errors import Forbidden
from datetime import datetime, timedelta
import csv
import os
import re
from pymongo.results import UpdateResult

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

    __ALLOW_FIRST_CHECKIN = 'allow-first-checkin'
    __ALLOW_SECOND_CHECKIN = 'allow-second-checkin'

    __FIRST_CHECK_IN = 'First-Check-In'
    __SECOND_CHECK_IN = 'Second-Check-In'
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
        section_collection = mongo.db[self.__SECTION_DATA]
        check_in_collection = mongo.db[self.__CHECK_IN_DATA]

        today = datetime.today()

        if ra.ta_or_higher(self.message.author) and current_lab_channel:
            # we're in the right section, now we need to check that it's the right time
            section_data = section_collection.find_one({'Section Name': section_name})
            section_number = section_data[self.__SECTION]
            date_code = int(today.strftime('%Y%m%d'))
            check_in_data = check_in_collection.find_one({'Section Name': section_name, 'Date': date_code})
            logger.info(str(check_in_data))
            if section_data:
                if not check_in_data:
                    await self.safe_send(self.message.author, 'Creating discussion for the date {}'.format(date_code), backup=self.message.channel)

                    todays_record = {'Section Name': section_name, 'Date': date_code, self.__ALLOW_FIRST_CHECKIN: True, self.__ALLOW_SECOND_CHECKIN: False}
                    for student in students_group.find({self.__SECTION: section_number}):
                        todays_record[student[self.__USERNAME]] = {self.__FIRST_CHECK_IN: 0, self.__SECOND_CHECK_IN: 0}
                    check_in_collection.insert_one(todays_record)
                    await self.safe_send(self.message.author, 'Created discussion for the date {}'.format(date_code), backup=self.message.channel)
                    await self.safe_send(self.message.channel, 'Started discussion attendance for the date {}, you may "!check in" now'.format(date_code))

                elif not check_in_data[self.__ALLOW_SECOND_CHECKIN]:
                    ur: UpdateResult = check_in_collection.update_one({'Section Name': section_name, 'Date': date_code}, {'$set': {self.__ALLOW_SECOND_CHECKIN: True}})
                    if not ur.matched_count:
                        await self.message.author.send('Unable to find discussion at the current time.  ')
                    elif not ur.modified_count:
                        await self.message.author.send('Unable to modify the discussion.  ')
                    else:
                        await self.message.channel.send('Second Checkin is now Allowed')
            else:
                await self.message.author.send('Unable to find section data.')

        elif not ra.ta_or_higher(self.message.author):
            await self.message.author.send("We were unable to find you. You are either not a TA, or otherwise unable to run this command.  ")
        elif not current_lab_channel:
            await self.message.author.send("We couldn't find this section.  Did you send this in your lab channel?")

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!lab allow check in'):
            return True
        elif message.content.startswith('!lab allow check in conf'):
            return True
        return False

    @classmethod
    def get_help(cls):
        return "This command allows a TA to create a new lab section, students can use the !check in command in a lab section. \n Command Format: !lab allow check in"