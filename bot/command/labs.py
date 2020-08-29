import logging

from discord import Message, Client, Attachment, Guild, PermissionOverwrite, TextChannel, CategoryChannel
from datetime import datetime, timedelta
import csv
import re

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority, PermissionAuthority

logger = logging.getLogger(__name__)


@command.command_class
class ConfigureLabs(command.Command):
    """
        This command should create the lab roles for the sections, create the section categories and each with a voice and text chat.

    """
    __LAB_SECTION_FILE_NAME = 'lab_sections.csv'
    __SECTION_STRING = 'Lab {}'
    __SECTION = 'Section'
    __SECTION_DATA = 'section-data'
    __DISCORD_ID = 'discord'

    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'

    async def handle(self):
        """
        Must upload a csv file which will contain the following columns (capitalization matters):
            Section: Section name or number (however it will be identified)
            Nickname: Nickname for the section.
            Name: TA Contents: TA umbc username assigned to the section
        """
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        ra: RoleAuthority = RoleAuthority(self.guild)
        if ca.is_maintenance_channel(self.message.channel) and ra.admin in self.message.author.roles:
            pa: PermissionAuthority = PermissionAuthority()

            section_data: Attachment = self.message.attachments[0]
            the_guild: Guild = self.message.guild
            try:
                students_group = mongo.db[self.__STUDENTS_GROUP]
                ta_group = mongo.db[self.__TA_GROUP]
                section_collection = mongo.db[self.__SECTION_DATA]

                await section_data.save(self.__LAB_SECTION_FILE_NAME)
                with open(self.__LAB_SECTION_FILE_NAME) as lab_sections:
                    section_reader = csv.DictReader(lab_sections)

                    # eliminating all lab channels
                    for channel_name in ca.lab_sections:
                        for channel in ca.lab_sections[channel_name].channels:
                            await channel.delete()
                        await ca.lab_sections[channel_name].delete()
                    ca.lab_sections = {}
                    section_collection.delete_many({})

                    for line in section_reader:
                        lab_section_name = self.__SECTION_STRING.format(line[self.__SECTION])
                        ca.lab_sections[line[self.__SECTION]] = await the_guild.create_category(lab_section_name, overwrites={
                            ra.ta: PermissionOverwrite(read_messages=False),
                            ra.student: PermissionOverwrite(read_messages=False),
                            ra.un_authenticated: PermissionOverwrite(read_messages=False)
                        })
                        text_channel = await ca.lab_sections[lab_section_name].create_text_channel('Section Text')
                        voice_channel = await ca.lab_sections[lab_section_name].create_voice_channel('Section Voice')
                        line.update({
                            'Section Name': lab_section_name,
                            'Section Category': ca.lab_sections[lab_section_name].id,
                            'Text Channel': text_channel.id,
                            'Voice Channel': voice_channel.id
                        })

                        section_collection.insert_one(line)

                        for ta in ta_group.find({self.__SECTION: line[self.__SECTION]}):
                            the_ta = the_guild.get_member(ta[self.__DISCORD_ID])
                            await ca.lab_sections[line[self.__SECTION]].set_permissions(the_ta, overwrite=pa.ta_overwrite)

                        for student in students_group.find({self.__SECTION: line[self.__SECTION]}):
                            the_student = the_guild.get_member(student[self.__DISCORD_ID])
                            await ca.lab_sections[line[self.__SECTION]].set_permissions(the_student, overwrite=pa.student_overwrite)

            except Exception as e:
                print(e)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!lab configure') and message.attachments:
            return True

        return False


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
            self.message.channel.send('The format for the command is !lab add user [username] [section number]')
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
                student = self.message.guild.get_member(found_student[self.__DISCORD_ID])
                await ca.lab_sections[self.__SECTION_STRING.format(section_number)].set_permissions(student, overwrite=pa.student_overwrite)
            elif found_ta:
                ta = self.message.guild.get_member(found_ta[self.__DISCORD_ID])
                await ca.lab_sections[self.__SECTION_STRING.format(section_number)].set_permissions(ta, overwrite=pa.ta_overwrite)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!lab add user'):
            return True
        return False


@command.command_class
class RemoveFromLabSection(command.Command):
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
            self.message.channel.send('The format for the command is !lab add user [username] [section number]')
            return
        if ca.is_maintenance_channel(self.message.channel) and ra.is_admin(self.message.author):

            username = self.message.content.split()[3]
            section_number = split_message[4]
            await self.message.channel.send('Removing {} from section {}'.format(username, section_number))

            students_group = mongo.db[self.__STUDENTS_GROUP]
            ta_group = mongo.db[self.__TA_GROUP]
            found_student = students_group.find_one({self.__USERNAME: username})
            found_ta = ta_group.find_one({self.__USERNAME: username})
            pa: PermissionAuthority = PermissionAuthority()

            if found_student:
                student = self.message.guild.get_member(found_student[self.__DISCORD_ID])
                await ca.lab_sections[self.__SECTION_STRING.format(section_number)].set_permissions(student, overwrite=pa.forbid_overwrite)
            elif found_ta:
                ta = self.message.guild.get_member(found_ta[self.__DISCORD_ID])
                await ca.lab_sections[self.__SECTION_STRING.format(section_number)].set_permissions(ta, overwrite=pa.forbid_overwrite)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!lab remove user'):
            return True
        return False


@command.command_class
class LabCheckIn(command.Command):
    __SECTION = 'Section'
    __SECTION_DATA = 'section-data'
    __DISCORD_ID = 'discord'
    __SECTION_STRING = 'Lab {}'

    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'
    __WEEKDAY_MAP = {0: 'M', 1: 'Tu', 2: 'W', 3: 'Th', 4: 'F', 5: 'Sa', 6: 'Su'}

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        # if the student is in the text chat of their lab session and the time is at the start then do the first authentication
        # if the student is in the text chat of their lab session and the time is after the second login and the TA has started the second check in process.

        current_lab_channel = None
        the_category: CategoryChannel = self.message.channel.category
        for lab_name in ca.lab_sections:
            if the_category == ca.lab_sections[lab_name]:
                current_lab_channel = ca.lab_sections[lab_name]

        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        section_collection = mongo.db[self.__SECTION_DATA]

        student_record = students_group.find_one({self.__DISCORD_ID: self.message.author.id})

        if student_record and current_lab_channel:
            section_name = self.__SECTION_STRING.format(student_record[self.__SECTION])

            # we're in the right section, now we need to check that it's the right time
            if current_lab_channel.name == section_name:
                section_data = section_collection.find_one({'Section Name': section_name})
                """ {'_id': ObjectId('5f480a36a6bca0f612b90999'), 'Section': '61', 'Days': 'M', 'Time': '11:00 am - 11:50 am', 'TA': '', 'Nickname': '', 'Section Name': 'Lab 61', 
                    'Section Category': 748625915226882068, 'Text Channel': 748625915839512646, 'Voice Channel': 748625916711665714}
                    2020-08-29 13:46:54.248772
                """
                if section_data:
                    margin = timedelta(seconds=30)

                    split_times = section_data['Time'].split('-')
                    matched_group = re.match(r'(?P<hour>\d+):(?P<minute>\d+)\s+(?P<am_pm>(am|pm))', split_times[0].strip())
                    today = datetime.today()
                    # test day for section 61
                    # today = datetime(year=2020, month=8, day=31, hour=11, minute=3, second=0)

                    the_hour = int(matched_group.group('hour'))
                    the_minute = int(matched_group.group('minute'))

                    if matched_group.group('am_pm') == 'pm':
                        the_hour += 12
                    # combines the current day with the starting time
                    start_time = datetime(year=today.year, month=today.month, day=today.day,
                                          hour=the_hour, minute=the_minute, second=0)

                    if start_time - margin <= today <= start_time + timedelta(minutes=15) + margin and \
                            self.__WEEKDAY_MAP[today.weekday()] in section_data['Days']:
                        await self.message.author.send('You are checked in to your office hours!')
                    else:
                        await self.message.author.send('This is not the correct check in time.')

                    print(section_data, start_time)
        elif not student_record:
            await self.message.author.send("We were unable to find you. Talk to you TAs or Professors. ")
        elif not current_lab_channel:
            await self.message.author.send("We couldn't find this section.  Did you send this in your lab channel?")

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!check in'):
            return True
        return False
