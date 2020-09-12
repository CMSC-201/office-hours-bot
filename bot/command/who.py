import logging
import re
import os

import csv

from discord import Message, Client, File

import mongo
import command
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class Who(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __DISCORD_ID = 'discord'
    __SECTION = 'Section'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'

    async def handle(self):

        ra: RoleAuthority = RoleAuthority(self.guild)

        student_col = mongo.db[self.__STUDENTS_GROUP]
        ta_collection = mongo.db[self.__TA_GROUP]

        if self.message.content.startswith('!who is my ta'):

            the_student = student_col.find_one({self.__DISCORD_ID: self.message.author.id})
            if not the_student:
                await self.message.author.send('Unable to find you in the student database.')
                return
            my_ta = ta_collection.find_one({self.__SECTION: the_student[self.__SECTION]})
            if not my_ta:
                await self.message.author.send('Unable to find your TA.')
            else:
                await self.message.author.send('Your TA is: {} {}'.format(my_ta[self.__FIRST_NAME], my_ta[self.__LAST_NAME]))
        elif self.message.content.startswith('!who is in section') and ra.ta_or_higher(self.message.author):
            match = re.match(r'!who\s+is\s+in\s+section\s+(?P<section_num>\d+)', self.message.content)
            if match:
                section_num = match.group('section_num')
                list_of_students = [s for s in student_col.find({self.__SECTION: match.group('section_num')})]
                if list_of_students:
                    try:
                        with open(os.path.join('csv_dump', 'section{}.csv'.format(section_num)), 'w', newline='') as csv_file:
                            roster_writer = csv.DictWriter(csv_file, fieldnames=list(list_of_students[0].keys()))
                            roster_writer.writeheader()
                            for s in list_of_students:
                                roster_writer.writerow(s)
                        f = File(os.path.join('csv_dump', 'section{}.csv'.format(section_num)))
                        await self.message.author.send('Your roster is here:', files=[f])

                    except OSError:
                        await self.message.author.send('Some kind of file error occurred, retry.')
                else:
                    await self.message.author.send('Section {} appears to be empty.'.format(section_num))

        if self.message.guild:
            await self.message.delete(delay=5)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!who"):
            return True

        return False
