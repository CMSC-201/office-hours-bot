import logging

from discord import Message, Client, Member, User, Attachment

import csv
import os

import mongo
import command
from channels import ChannelAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class CheckRosterForDrops(command.Command):
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'
    __DROPPED = 'dropped'
    __MONGO_ID = '_id'

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)

        roster_path = os.path.join('csv_dump', 'drop_roster.csv')
        if self.message.attachments:
            attachment: Attachment = self.message.attachments[0]
            await attachment.save(roster_path)
        else:
            await self.message.channel.send('Did you attach a csv/txt file with the usernames?')
            return

        student_list = {}
        with open(roster_path, encoding="utf8") as new_users_file:
            student_list = {student_id.strip().lower(): True for student_id in new_users_file}

            if ra.is_admin(self.message.author) and ca.is_maintenance_channel(self.message.channel):
                students_collection = mongo.db[self.__STUDENTS_GROUP]
                for student in students_collection.find():
                    if student[self.__USERNAME] not in student_list:
                        students_collection.update_one({self.__MONGO_ID: student[self.__MONGO_ID]}, {'$set': {self.__DROPPED: True}})
                    elif self.__DROPPED not in student:
                        students_collection.update_one({self.__MONGO_ID: student[self.__MONGO_ID]}, {'$set': {self.__DROPPED: False}})

                await self.message.channel.send('Dropped students updated from course list.')
            else:
                await self.message.channel.send('This command must be run by an admin in the maintenance channel.')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!check roster for drops"):
            return True

        return False
