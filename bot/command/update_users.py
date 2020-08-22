import logging

from discord import Message, Client, Attachment

import command
import mongo
import hashlib
import csv
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority
from member import MemberAuthority

logger = logging.getLogger(__name__)


@command.command_class
class UpdateUsers(command.Command):

    __COLUMN_NAMES = ['UMBC-Name-Id', 'First-Name', 'Last-Name', 'Role']
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __DISCORD_FIELD = 'discord'

    async def handle(self):
        attachment: Attachment = self.message.attachments[0]
        await attachment.save('update_users.csv')

        ra: RoleAuthority = RoleAuthority(self.message.guild)
        if ra.admin:
            try:
                students_group = mongo.db[self.__STUDENTS_GROUP]
                ta_group = mongo.db[self.__TA_GROUP]
                admin_group = mongo.db[self.__ADMIN_GROUP]

                with open('update_users.csv', encoding="utf8") as new_users_file:
                    users_reader = csv.DictReader(new_users_file)
                    for line in users_reader:
                        if all(line[col_name].strip() for col_name in self.__COLUMN_NAMES) and line['Role'].strip().lower() in ['student', 'ta', 'admin']:

                            current_student = dict(line)
                            current_student['Role'] = line['Role'].strip().lower()

                            new_hash = hashlib.sha256()
                            name_id = ' '.join([line['First-Name'], line['Last-Name'], line['UMBC-Name-Id']])
                            new_hash.update(name_id.encode('utf-8'))

                            # add any new data elements to the current student's record before inserting
                            current_student['key'] = new_hash.hexdigest()
                            current_student['email-sent'] = 0
                            current_student[self.__DISCORD_FIELD] = ''

                            if current_student['Role'] == self.__STUDENTS_GROUP:
                                if students_group.find_one({'UMBC-Name-Id': current_student['UMBC-Name-Id']}):
                                    await self.message.channel.send('Duplicate Student found: %s' % name_id)
                                else:
                                    await self.message.channel.send('Added student: %s' % name_id)
                                students_group.insert_one(current_student)
                            elif current_student['Role'] == self.__TA_GROUP:
                                if ta_group.find_one({'UMBC-Name-Id': current_student['UMBC-Name-Id']}):
                                    await self.message.channel.send('Duplicate TA found: %s' % name_id)
                                else:
                                    await self.message.channel.send('Added TA: %s' % name_id)
                                ta_group.insert_one(current_student)
                            elif current_student['Role'] == self.__ADMIN_GROUP:
                                if admin_group.find_one({'UMBC-Name-Id': current_student['UMBC-Name-Id']}):
                                    await self.message.channel.send('Duplicate Admin Found: %s' % name_id)
                                else:
                                    await self.message.channel.send('Added admin: %s' % name_id)
                                    admin_group.insert_one(current_student)
                            else:
                                await self.message.channel.send('Bad Role %s' % current_student['Role'])
                        else:
                            self.message.channel.send('Bad line: ' + str(line))
                await self.message.delete()
            except OSError:
                self.log.info('Unable to open file user_database.csv')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!update users"):
            return True

        return False
