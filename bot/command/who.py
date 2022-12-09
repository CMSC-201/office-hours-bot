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

    __QUEUE_COLLECTION = 'queues'
    __AVAILABLE_TAS = 'available_tas'
    __OFFICE_HOURS_OPEN = 'open'

    async def who_is_my_ta(self):
        ta_collection = mongo.db[self.__TA_GROUP]
        admin_collection = mongo.db[self.__ADMIN_GROUP]

        match = re.match(r'!who\s+is\s+the\s+ta\s+for\s+section\s+(?P<section_num>\d+)', self.message.content)
        section_num = match.group('section_num')

        found_section_leaders = []
        for ta in ta_collection.find():
            for section in ta.get('Section', "").split(','):
                if section.strip() == section_num:
                    found_section_leaders.append(ta)

        for admin in admin_collection.find():
            for section in admin.get('Section', "").split(','):
                if section.strip() == section_num:
                    found_section_leaders.append(admin)

        if found_section_leaders:
            if len(found_section_leaders) == 1:
                the_ta = found_section_leaders[0]
                ta_name = ' '.join([the_ta[self.__FIRST_NAME], the_ta[self.__LAST_NAME]])
                await self.message.channel.send(f'The TA for section {section_num} is {ta_name}')
            else:
                the_names = ', '.join([' '.join([the_ta[self.__FIRST_NAME], the_ta[self.__LAST_NAME]]) for the_ta in found_section_leaders])
                await self.message.channel.send(f'The TAs for section {section_num} are {the_names}')
        else:
            await self.message.channel.send(f'Unable to find ta for section {section_num}')

    async def handle(self):

        ra: RoleAuthority = RoleAuthority(self.guild)

        student_col = mongo.db[self.__STUDENTS_GROUP]
        ta_collection = mongo.db[self.__TA_GROUP]
        admin_collection = mongo.db[self.__ADMIN_GROUP]

        match_ta = re.match(r'!who\s+is\s+my\s+(?P<person>\w+)', self.message.content)
        if match_ta:
            if match_ta.group('person').lower() == 'ta':
                the_student = student_col.find_one({self.__DISCORD_ID: self.message.author.id})
                if not the_student:
                    await self.message.author.send('Unable to find you in the student database.')
                    return
                my_ta = ta_collection.find_one({self.__SECTION: the_student[self.__SECTION]})
                if not my_ta:
                    await self.message.author.send('Unable to find your TA.')
                else:
                    await self.message.author.send('Your TA is: {} {}'.format(my_ta[self.__FIRST_NAME], my_ta[self.__LAST_NAME]))
            elif match_ta.group('person').lower() == 'professor':
                pass
            elif match_ta.group('person').lower() == 'mommy':
                pass
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
        elif self.message.content.startswith('!who is on duty'):
            office_hour_queue = mongo.db[self.__QUEUE_COLLECTION]
            queue_doc = office_hour_queue.find_one()
            on_duty_tas = [await self.guild.fetch_member(ta_id) for ta_id in queue_doc[self.__AVAILABLE_TAS]]
            if on_duty_tas:
                await self.message.channel.send('The TAs on duty are:\n' + '\n'.join([x.name for x in on_duty_tas]))
            elif not queue_doc[self.__OFFICE_HOURS_OPEN]:
                await self.message.channel.send('Office hours are closed now, no TAs are on duty. ')
            else:
                await self.message.channel.send('No TAs are on duty.  ')
        elif self.message.content.startswith('!who is the ta for section') and ra.ta_or_higher(self.message.author):
            await self.who_is_my_ta()


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!who"):
            return True
        return False

