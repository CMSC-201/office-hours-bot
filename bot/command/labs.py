import logging

from discord import Message, Client, Attachment, Guild, PermissionOverwrite
import csv

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

        """
            for now delete all old lab sections
            create all new sections
            scan TAs and set permissions for TAs assigned to sections
            scan students and set permissions for students assigned to sections            
        """

        ra: RoleAuthority = RoleAuthority(self.message.guild)
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
