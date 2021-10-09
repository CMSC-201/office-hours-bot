import logging
import re
import os

import csv
from datetime import datetime

from discord import Message, Client, File

import mongo
import command
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class Where(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __DISCORD_ID = 'discord'
    __SECTION = 'Section'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'

    __LECTURE_LINKS = 'lecture-links'

    async def handle(self):

        lecture_collect = mongo.db[self.__LECTURE_LINKS]

        match = re.match(r'!where\s+(are|is)\s+the\s+lecture[s]?(\s+(today))', self.message.content)

        found_lecture = lecture_collect.find_one({'date': datetime.today().strftime('%m%d%Y')})

        if match and found_lecture:
            await self.message.author.send('The link to today\'s lecture can be found: {}'.format(found_lecture['link']))
        else:
            await self.message.author.send('The link hasn\'t been posted yet, or there isn\'t a lecture today.')

        if self.message.guild:
            await self.message.delete(delay=5)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!where"):
            return True

        return False


@command.command_class
class SetLectureLink(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __DISCORD_ID = 'discord'
    __SECTION = 'Section'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'

    __LECTURE_LINKS = 'lecture-links'

    async def handle(self):

        ra: RoleAuthority = RoleAuthority(self.guild)
        lecture_collect = mongo.db[self.__LECTURE_LINKS]

        match = re.match(r'!set\s+lecture\s+link\s+(?P<date>\d{8})\s+(?P<link>.*)', self.message.content)
        if ra.is_admin(self.message.author) and match:
            lecture_collect.insert_one({'date': match.group('date'), 'link': match.group('link')})

        if self.message.guild:
            await self.message.delete(delay=5)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!set lecture"):
            return True

        return False