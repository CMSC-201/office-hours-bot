import logging

from discord import Message, Client, Attachment, Guild, PermissionOverwrite, TextChannel, CategoryChannel, Member, File
from discord.errors import NotFound
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
    __USERNAME = 'UMBC-Name-Id'

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
                        logger.info(str(line))
                        lab_section_name = self.__SECTION_STRING.format(line[self.__SECTION])
                        logger.info('Creating Section Category Channel')
                        ca.lab_sections[lab_section_name] = await the_guild.create_category(lab_section_name, overwrites={
                            ra.ta: PermissionOverwrite(read_messages=False),
                            ra.student: PermissionOverwrite(read_messages=False),
                            ra.un_authenticated: PermissionOverwrite(read_messages=False)
                        })
                        logger.info('Creating Section Text')
                        text_channel = await ca.lab_sections[lab_section_name].create_text_channel('Section Text')
                        logger.info('Creating Section Voice')
                        voice_channel = await ca.lab_sections[lab_section_name].create_voice_channel('Section Voice')
                        line.update({
                            'Section Name': lab_section_name,
                            'Section Category': ca.lab_sections[lab_section_name].id,
                            'Text Channel': text_channel.id,
                            'Voice Channel': voice_channel.id
                        })
                        logger.info('Inserting lab into section db')
                        section_collection.insert_one(line)

                        if line[self.__TA_GROUP]:
                            section_ta = ta_group.find_one({self.__USERNAME: line[self.__TA_GROUP].strip().lower()})
                            the_ta = await self.get_member(section_ta[self.__DISCORD_ID])
                            await ca.lab_sections[lab_section_name].set_permissions(the_ta, overwrite=pa.ta_overwrite)
                            section_ta[self.__SECTION] = line[self.__SECTION]
                            ta_group.update_one({self.__USERNAME: line[self.__TA_GROUP].strip().lower()}, {'$set': {self.__SECTION: section_ta[self.__SECTION]}})

                        logger.info('Finding TA')
                        for ta in ta_group.find({self.__SECTION: line[self.__SECTION]}):
                            the_ta = await self.get_member(ta[self.__DISCORD_ID])
                            try:
                                await ca.lab_sections[lab_section_name].set_permissions(the_ta, overwrite=pa.ta_overwrite)
                            except NotFound:
                                logger.info('Unable to find the ta, continuing')

                        logger.info('Finding Students')
                        for student in students_group.find({self.__SECTION: line[self.__SECTION]}):
                            try:
                                the_student = await the_guild.fetch_member(student[self.__DISCORD_ID])
                                await ca.lab_sections[lab_section_name].set_permissions(the_student, overwrite=pa.student_overwrite)
                            except NotFound:
                                logger.info('Unable to find the student, continuing')
            except Exception as e:
                logger.warning(str(e), str(type(e)))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!lab configure') and message.attachments:
            return True

        return False

    @classmethod
    def get_help(cls):
        import textwrap
        return textwrap.dedent(
            """This command allows the course administrators to create the lab sections and sets the permissions.  
            Command Format: !lab configure
            Attachment required: a csv containing the data for the labs with column headings and an example line below
            
            Section,Days,Time,TA,Nickname
            11,M,2:30 pm - 3:20 pm,,""")
