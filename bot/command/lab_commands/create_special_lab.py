import logging

from discord import Message, Client, Attachment, Guild, PermissionOverwrite, TextChannel, CategoryChannel, Member, File, Permissions
from discord.errors import NotFound
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
    __LAB_SECTION_FILE_NAME = 'special_section.csv'
    __SECTION_STRING = 'Lab {}'
    __SECTION = 'Section'
    __SECTION_DATA = 'section-data'
    __DISCORD_ID = 'discord'

    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'

    permissions = {'student': False, 'ta': False, 'admin': True}

    def create_permission_overwrites(self):
        lab_student_permissions = PermissionOverwrite(
            add_reactions=True,
            administrator=False,
            attach_files=False,
            ban_members=False,
            change_nickname=False,
            connect=True,
            create_instant_invite=False,
            deafen_members=False,
            embed_links=True,
            external_emojis=True,
            kick_members=False,
            manage_channels=False,
            manage_emojis=False,
            manage_guild=False,
            manage_messages=False,
            manage_nicknames=False,
            manage_permissions=False,
            manage_roles=False,
            manage_webhooks=False,
            mention_everyone=False,
            move_members=False,
            mute_members=False,
            priority_speaker=False,
            read_message_history=False,
            read_messages=True,
            send_messages=True,
            send_tts_messages=False,
            speak=True,
            stream=True,
            use_external_emojis=True,
            use_voice_activation=True,
            view_audit_log=False,
            view_channel=True,
            view_guild_insights=False,
        )

        lab_leader_permissions = PermissionOverwrite(
            add_reactions=True,
            administrator=False,
            attach_files=False,
            ban_members=True,
            change_nickname=False,
            connect=True,
            create_instant_invite=True,
            deafen_members=True,
            embed_links=True,
            external_emojis=True,
            kick_members=True,
            manage_channels=True,
            manage_emojis=True,
            manage_guild=False,
            manage_messages=True,
            manage_nicknames=False,
            manage_permissions=True,
            manage_roles=True,
            manage_webhooks=False,
            mention_everyone=True,
            move_members=True,
            mute_members=True,
            priority_speaker=True,
            read_message_history=True,
            read_messages=True,
            send_messages=True,
            send_tts_messages=True,
            speak=True,
            stream=True,
            use_external_emojis=True,
            use_voice_activation=True,
            view_audit_log=True,
            view_channel=True,
            view_guild_insights=False,
        )
        return lab_student_permissions, lab_leader_permissions

    async def lab_create_roles(self, lab_title):
        """
        :param lab_title: a string containing the name of the special lab section.
        """
        student_role = await self.guild.create_role(name=lab_title+'Student', permissions=Permissions.none(), mentionable=True)
        leader_role = await self.guild.create_role(name=lab_title+'Leader', permissions=Permissions.none(), mentionable=True)
        return student_role, leader_role

    def find_user_by_username(self, username):
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]
        student_found = students_group.find_one({self.__USERNAME: username})
        if student_found:
            return student_found
        ta_found = ta_group.find_one({self.__USERNAME: username})
        if ta_found:
            return ta_found
        admin_found = admin_group.find_one({self.__USERNAME: username})
        if admin_found:
            return admin_found

        return None

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self, previous_message=None):
        """
        Must upload a csv file which will contain a username on each line for the students in the special section.  The first line should be the name of the section.
        """
        pa: PermissionAuthority = PermissionAuthority()
        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)

        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        the_guild: Guild = self.message.guild

        match = re.match(r'!create\s+special\s+section\s+(?P<lab_name>(\w|-)+)\s+(--usernames\s*=\s*)(?P<usernames>(\w|\s)+)', self.message.content)
        if not match:
            await self.message.channel.send('Improper format, please give a name of the lab section followed by --usernames=[usernames space separated]')
            return

        lab_section_name = match.group('lab_name')

        try:
            section_collection = mongo.db[self.__SECTION_DATA]

            student_role, leader_role = await self.lab_create_roles(lab_section_name)
            student_overwrite, leader_overwrite = self.create_permission_overwrites()

            logger.info('Creating Section Category Channel: ')
            new_category = await the_guild.create_category(lab_section_name, overwrites={
                ra.ta: PermissionOverwrite(read_messages=False),
                ra.student: PermissionOverwrite(read_messages=False),
                ra.un_authenticated: PermissionOverwrite(read_messages=False),
                student_role: student_overwrite,
                leader_role: leader_overwrite,
            })
            logger.info('\tAdding new category channel to special section database. ')
            ca.add_special_section(new_category, student_role, leader_role)

            logger.info('Creating Section {} Text'.format(lab_section_name))
            await new_category.create_text_channel('Section Text')
            logger.info('Creating Section {} Voice'.format(lab_section_name))
            await new_category.create_voice_channel('Section Voice')

            usernames = match.group('usernames').lower().split()
            await self.message.channel.send('Adding the following users to the channels: ' + ', '.join(usernames))
            for user_name in usernames:
                try:
                    section_student = students_group.find_one({self.__USERNAME: user_name})
                    if section_student:
                        discord_student = await self.guild.fetch_member(section_student[self.__DISCORD_ID])
                        if discord_student:
                            await discord_student.add_roles(student_role)
                            await self.message.channel.send('\tAdding student {} to the section.'.format(section_student[self.__USERNAME]))
                    else:
                        section_ta = ta_group.find_one({self.__USERNAME: user_name})
                        admin_ta = admin_group.find_one({self.__USERNAME: user_name})
                        if admin_ta:
                            discord_admin = await self.guild.fetch_member(section_ta[self.__DISCORD_ID])
                            if discord_admin:
                                await discord_admin.add_roles(leader_role)
                                await self.message.channel.send('\tAdding admin {} to the section.'.format(discord_admin[self.__USERNAME]))
                            else:
                                await self.message.channel.send('\tUnable to find discord username for {}.'.format(discord_admin[self.__USERNAME]))
                        elif section_ta:
                            discord_ta = await self.guild.fetch_member(section_ta[self.__DISCORD_ID])
                            if discord_ta:
                                await discord_ta.add_roles(leader_role)
                                await self.message.channel.send('\tAdding ta {} to the section.'.format(section_ta[self.__USERNAME]))
                except NotFound:
                    await self.message.channel.send('Unable to find discord member for username {}.'.format(section_ta[self.__USERNAME]))
        except Exception as e:
            logger.warning(str(e), str(type(e)))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!create special section'):
            return True

        return False

    @classmethod
    def get_help(cls):
        import textwrap
        return textwrap.dedent(
            """This command allows the course administrators to create special lab sections and sets the roles.  
            Command Format: !lab create special name-of-lab-section
            Attachment required: a csv containing the student usernames you want to add to the group.""")
