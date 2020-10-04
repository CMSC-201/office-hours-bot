import logging

from discord import Message, Client, Attachment, Guild, PermissionOverwrite, TextChannel, CategoryChannel, Member, File
from discord.errors import Forbidden
from datetime import datetime, timedelta
import csv
import os
import re

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority, PermissionAuthority

logger = logging.getLogger(__name__)


@command.command_class
class GetAttendance(command.Command):
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
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)

        lab_channel: CategoryChannel = ca.find_lab_channel(self.message.channel.category)

        check_in_collection = mongo.db[self.__CHECK_IN_DATA]

        match = re.match(r'!lab\s+((?P<section>\d{2})\s+)?get\s+attendance\s+(?P<date_code>\d{8})', self.message.content)

        if not ra.ta_or_higher(self.message.author):
            await self.message.author.send('You do not have permission to run the command.')
        elif match:
            section_name = self.__SECTION_STRING.format(match.group('section'))
            date_code = int(match.group('date_code'))
            check_in_record = check_in_collection.find_one({'Section Name': section_name, 'Date': date_code})
            if check_in_record:
                try:
                    file_name = 'attendance_{}_{}.csv'.format(section_name, date_code)
                    with open(os.path.join('csv_dump', file_name), 'w', newline='') as csv_file:
                        roster_writer = csv.DictWriter(csv_file, fieldnames=['Student', self.__FIRST_CHECK_IN, self.__SECOND_CHECK_IN, 'Attendance'])
                        roster_writer.writeheader()

                        for student in check_in_record:
                            if student not in ['Section Name', 'Date', self.__ALLOW_FIRST_CHECKIN, self.__ALLOW_SECOND_CHECKIN, '_id']:
                                try:
                                    roster_writer.writerow({'Student': student,
                                                            self.__FIRST_CHECK_IN: check_in_record[student][self.__FIRST_CHECK_IN],
                                                            self.__SECOND_CHECK_IN: check_in_record[student][self.__SECOND_CHECK_IN],
                                                            'Attendance': check_in_record[student][self.__FIRST_CHECK_IN] + check_in_record[student][self.__SECOND_CHECK_IN]})
                                except TypeError:
                                    roster_writer.writerow({'Student': student, 'Attendance': check_in_record[student]})

                    f = File(os.path.join('csv_dump', file_name))
                    await self.message.author.send('Your attendance record is here:', files=[f])

                except OSError:
                    await self.message.author.send('Some kind of file error occurred, retry.')
                except Forbidden:
                    await self.message.channel.send('Attendance Request: Unable to send you a DM, try again or enable DMs.  ')
                print(check_in_record)
            else:
                print('Couldn\'t find the check in record for that date')
        else:
            await self.safe_send(self.message.author, 'The format of the command is wrong.', backup=self.message.channel)

        await self.message.delete(delay=2)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        match = re.match(r'!lab\s+((?P<section>\d{2})\s+)?get\s+attendance\s+(?P<date_code>\d{8})', message.content)
        if match:
            return True
        return False
