import logging

from discord import Message, Client, Attachment, Guild, PermissionOverwrite, TextChannel, CategoryChannel, Member, File
from datetime import datetime, timedelta
import csv
import os

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority, PermissionAuthority

logger = logging.getLogger(__name__)


@command.command_class
class GetLabZeroAttendance(command.Command):
    __SECTION = 'Section'
    __SECTION_DATA = 'section-data'
    __CHECK_IN_DATA = 'check-in-data'
    __DISCORD_ID = 'discord'
    __SECTION_STRING = 'Lab {}'

    __ALLOW_SECOND_CHECKIN = 'allow-second-checkin'
    __FIRST_CHECK_IN = 1
    __SECOND_CHECK_IN = 2
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)

        lab_channel: CategoryChannel = ca.find_lab_channel(self.message.channel.category)

        recognized_authors = {}

        students_group = mongo.db[self.__STUDENTS_GROUP]

        if ra.ta_or_higher(self.message.author) and lab_channel:
            for channel in lab_channel.text_channels:
                channel: TextChannel
                channel_history_list = await channel.history(limit=None).flatten()
                for message in channel_history_list:
                    if message.author.id not in recognized_authors:
                        student = students_group.find_one({self.__DISCORD_ID: message.author.id})
                        recognized_authors[message.author.id] = student

            discord_lab_file: File = None
            field_names = {'First-Name', 'Last-Name', self.__USERNAME}
            if recognized_authors:
                section = lab_channel.name
                lab_attendance_file_name = os.path.join('csv_dump',
                                                        'lab_attendance_{}_{}.csv'.format(section, datetime.today().strftime('%m.%d.%H.%M.%S')))
                with open(lab_attendance_file_name, 'w', newline='') as lab_attendance_file:
                    writer = csv.DictWriter(lab_attendance_file, fieldnames=field_names)
                    writer.writeheader()
                    for student_id in recognized_authors:
                        if recognized_authors[student_id]:
                            new_line = {col_id: recognized_authors[student_id][col_id] for col_id in field_names}
                            writer.writerow(new_line)
                discord_lab_file = File(open(lab_attendance_file_name, 'rb'))
                await self.message.author.send('Getting Lab 0 Attendance Score', files=[discord_lab_file])
            else:
                await self.message.author.send('No one has checked in yet.')
        else:
            await self.message.author.send('You do not have permission to run the command.')

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!lab get lab0 grades'):
            return True
        return False
