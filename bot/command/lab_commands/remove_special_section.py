import logging
import command
from channels import ChannelAuthority
import re
from discord import Message, Client

logger = logging.getLogger(__name__)


@command.command_class
class RemoveSpecialSection(command.Command):
    """
        This command should remove the lab roles for the sections, destroy the section categories and the subordinate rooms.

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

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self, previous_message=None):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        re_match = re.match(r'!remove\s+special\s+section\s+(?P<section_name>(\w|-)+)', self.message.content)
        await ca.remove_special_section(re_match.group('section_name'))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!lab create special'):
            return True

        return False
