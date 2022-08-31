import logging

from discord import Message, Client, Attachment

import command
import mongo
import hashlib
import random
import string
import csv
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class UpdateUsers(command.Command):

    __COLUMN_NAMES = ['UMBC-Name-Id', 'First-Name', 'Last-Name', 'Role', 'UID', 'Section']
    __ALT_COLUMN_NAMES = ['StudentLastName', 'StudentFirstName', 'StudentCampusID', 'StudentMyUMBCId', 'ClassNumberClassSectionSourceKey']
    __COLUMN_NAME_MAP = {'StudentLastName': 'Last-Name', 'StudentFirstName': 'First-Name',
                         'StudentCampusID': 'UID', 'StudentMyUMBCId': 'UMBC-Name-Id',
                         'ClassNumberClassSectionSourceKey': 'Section'}

    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __DISCORD_FIELD = 'discord'
    __UID_FIELD = 'UMBC-Name-Id'
    __ROLE = 'Role'
    __EMAIL_SENT = 'email-sent'
    __KEY = 'key'
    __SECTION = 'Section'

    permissions = {'student': False, 'ta': False, 'admin': True}

    async def get_dict_reader(self, file_name):
        """
        :param file_name: the file name to the csv
        :return: a DictReader
        """
        comma_csv = True
        default_col_names = False

        with open(file_name) as csv_file:
            first_line = next(csv.DictReader(csv_file))
            try:
                for name in self.__COLUMN_NAMES:
                    first_line[name]
                comma_csv = True
                default_col_names = True
                return True, True
            except KeyError:
                pass

            try:
                for name in self.__ALT_COLUMN_NAMES:
                    first_line[name]
                comma_csv = True
                default_col_names = False
                return True, default_col_names
            except KeyError:
                pass


        with open(file_name) as csv_file:
            first_line = next(csv.DictReader(csv_file, delimiter='\t'))
            try:
                for name in self.__COLUMN_NAMES:
                    first_line[name]
                comma_csv = False
                default_col_names = True
                return comma_csv, default_col_names
            except KeyError:
                pass

            try:
                for name in self.__ALT_COLUMN_NAMES:
                    first_line[name]
                comma_csv = False
                default_col_names = False
                return comma_csv, default_col_names
            except KeyError:
                    pass

        raise ValueError("Did not detect column headers with tabs or commas.  ")


    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        if self.message.attachments:
            attachment: Attachment = self.message.attachments[0]
            await attachment.save('update_users.csv')
        else:
            await self.message.channel.send('Did you attach a csv with the new users?')
            return
        try:
            csv_file_name = 'update_users.csv'
            try:
                comma_csv, default_col_names = await self.get_dict_reader(csv_file_name)
            except ValueError as ve:
                await self.message.channel.send(ve)
                return

            await self.message.channel.send(f'Update Users: \n\tDetected Comma Delimiter: {comma_csv}\n\tDetected REX Type: {not default_col_names}')
            with open(csv_file_name) as csv_file:
                users_reader = csv.DictReader(csv_file, delimiter="," if comma_csv else '\t')
                ignore_duplicates = False if '--show-duplicates' in self.message.content else True

                if default_col_names:
                    await self.message.channel.send('Update Users: Starting User-Add from Default CSV')
                    await self.load_default_data(users_reader, ignore_duplicates)
                else:
                    await self.message.channel.send('Update Users: Starting User-Add from REX-formatted CSV')
                    await self.load_rex_data(users_reader, ignore_duplicates)
                await self.message.channel.send('Update Users: Process Complete')

        except OSError:
            logger.info('Unable to open file user_database.csv')

    async def load_rex_data(self, users_reader, ignore_duplicates):
        """
        Loading rex data is specifically student data, so we don't need to worry about the ta or admin groups.

        By default we should skip sections with divisible by 10 numbers

        :param users_reader: the DictReader for the file
        """
        students_group = mongo.db[self.__STUDENTS_GROUP]

        for line in users_reader:
            try:
                current_student = {self.__COLUMN_NAME_MAP[key]: line[key].strip() for key in self.__ALT_COLUMN_NAMES}
            except KeyError as key_error:
                await self.message.channel.send(f'Key Error while Parsing Rex File: {key_error}.')
                return
            # if they're being loaded from rex, they're students
            current_student[self.__ROLE] = self.__STUDENTS_GROUP
            # add any new data elements to the current student's record before inserting
            current_student[self.__EMAIL_SENT] = 0
            current_student[self.__DISCORD_FIELD] = ''
            for column_name in self.__ALT_COLUMN_NAMES:
                current_student[self.__COLUMN_NAME_MAP[column_name]] = line[column_name].strip()
            current_student[self.__KEY] = self.generate_user_code(current_student)

            name_id = current_student[self.__UID_FIELD]

            if current_student[self.__ROLE] == self.__STUDENTS_GROUP:
                if int(current_student[self.__SECTION]) % 10 != 0:
                    if students_group.find_one({self.__UID_FIELD: current_student[self.__UID_FIELD]}):
                        if not ignore_duplicates:
                            await self.message.channel.send('Duplicate Student found: %s' % name_id)
                    else:
                        students_group.insert_one(current_student)
                        await self.message.channel.send('Added student: %s' % name_id)

    async def load_default_data(self, users_reader, ignore_duplicates):
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        for line in users_reader:
            if all(col_name in line for col_name in self.__COLUMN_NAMES) and line[self.__ROLE].strip().lower() in ['student', 'ta', 'admin']:

                current_student = {key: line[key].strip() for key in dict(line)}
                current_student[self.__ROLE] = line[self.__ROLE].strip().lower()
                name_id = current_student[self.__UID_FIELD]

                # add any new data elements to the current student's record before inserting
                current_student[self.__KEY] = self.generate_user_code(current_student)
                current_student[self.__EMAIL_SENT] = 0
                current_student[self.__DISCORD_FIELD] = ''

                if current_student[self.__ROLE] == self.__STUDENTS_GROUP:
                    if students_group.find_one({self.__UID_FIELD: current_student[self.__UID_FIELD]}):
                        await self.message.channel.send('Duplicate Student found: %s' % name_id)
                    else:
                        await self.message.channel.send('Added student: %s' % name_id)
                    students_group.insert_one(current_student)
                elif current_student[self.__ROLE] == self.__TA_GROUP:
                    if ta_group.find_one({self.__UID_FIELD: current_student[self.__UID_FIELD]}):
                        await self.message.channel.send('Duplicate TA found: %s' % name_id)
                    else:
                        await self.message.channel.send('Added TA: %s' % name_id)
                    ta_group.insert_one(current_student)
                elif current_student[self.__ROLE] == self.__ADMIN_GROUP:
                    if admin_group.find_one({self.__UID_FIELD: current_student[self.__UID_FIELD]}):
                        await self.message.channel.send('Duplicate Admin Found: %s' % name_id)
                    else:
                        await self.message.channel.send('Added admin: %s' % name_id)
                        admin_group.insert_one(current_student)
                else:
                    await self.message.channel.send('Bad Role %s' % current_student[self.__ROLE])
            else:
                if line[self.__ROLE].strip().lower() not in ['student', 'ta', 'admin']:
                    await self.message.channel.send('Role must be student, ta, admin.')
                else:
                    bad_columns = []
                    for col_name in self.__COLUMN_NAMES:
                        if col_name.strip() not in line:
                            bad_columns.append(col_name)
                    await self.message.channel.send('Column Names Not Found: ' + ', '.join(bad_columns))
                await self.message.channel.send('Bad line: ' + str(line))


    def generate_user_code(self, user):
        new_hash = hashlib.sha256()
        random_string = ''.join([random.choice(string.ascii_lowercase) for _ in range(20)])
        name_id = ' '.join([user['First-Name'].strip(), user['Last-Name'].strip(), user[self.__UID_FIELD].strip(), random_string])
        new_hash.update(name_id.encode('utf-8'))
        return new_hash.hexdigest()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!update users"):
            return True

        return False
