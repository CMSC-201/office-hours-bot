from discord import Message, Client
import command
import mongo
import re


@command.command_class
class RegisterLecture(command.Command):
    __LECTURE_ATTENDANCE = 'lecture-attendance'
    __LECTURE_ATTENDANCE_SECTIONS = 'lecture-attendance-sections'
    __KEY_TYPE = 'key-type'
    __SECTION_LIST = 'section-list'
    __DAY_LIST = 'day-list'

    __COMMAND_REGEX = r'!attendance\s+register\s+lecture\s+(?P<lecture_name>[\w_-]+)\s+sections\s*=\s*(?P<section_numbers>(\s*\d+\s*[,])*(\s*\d+\s*))'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self, new_message=None):
        regex_match = re.match(self.__COMMAND_REGEX, self.message.content)
        if not regex_match:
            await self.safe_send(self.message.channel, 'Unable to create the new lecture attendance section.  Invalid command format. \nShould be !attendance register lecture [lec_name] sections = 11, 12, 13, 14, 15, 16')
            return False

        lecture_attendance_sections_db = mongo.db[self.__LECTURE_ATTENDANCE_SECTIONS]
        sections = lecture_attendance_sections_db.find_one({self.__KEY_TYPE: self.__SECTION_LIST})

        create_new = False
        if not sections:
            create_new = True
            sections = {self.__KEY_TYPE: self.__SECTION_LIST}

        lecture_name = regex_match.group('lecture_name')
        section_numbers_string = regex_match.group('section_numbers')

        try:
            section_numbers = [int(x) for x in section_numbers_string.split(',')]
        except ValueError:
            await self.safe_send(self.message.channel, 'Unable to parse section numbers, they should be integers. ')
            return False

        if lecture_name not in sections:
            sections[lecture_name] = section_numbers
        else:
            await self.safe_send(self.message.channel, 'Updating Section Numbers...')
            sections[lecture_name] = section_numbers
        if create_new:
            lecture_attendance_sections_db.insert_one(sections)
        else:
            lecture_attendance_sections_db.replace_one({self.__KEY_TYPE: self.__SECTION_LIST}, sections)
        await self.safe_send(self.message.channel, f'Lecture Section {lecture_name} added for attendance purposes with sections {", ".join([str(x) for x in section_numbers])}.')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!attendance register lecture'):
            return True
        return False

    @classmethod
    def get_help(self):
        return 'This command will register a set of sections as a lecture for the purposes of attendance. '
