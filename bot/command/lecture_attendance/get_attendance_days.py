from discord import Message, Client, Color, Member, Embed
import command
import mongo
import re
from datetime import timedelta, datetime


@command.command_class
class StartAttendance(command.Command):
    __LECTURE_ATTENDANCE = 'lecture-attendance'
    __LECTURE_ATTENDANCE_SECTIONS = 'lecture-attendance-sections'
    __SESSIONS = 'sessions'
    __LECTURE_NAME = 'lecture-name'
    __SESSION_KEY = 'session-key'

    __STUDENTS_GROUP = 'student'

    __STUDENT_SECTION = 'Section'

    __START_TIME = 'start-time'
    __DURATION = 'duration'
    __STUDENT_LIST = 'student-list'

    __KEY_TYPE = 'key-type'
    __SECTION_LIST = 'section-list'
    __DAY_LIST = 'day-list'

    __REGULAR_CODE = 'regular-code'
    __OVERRIDE_CODE = 'override-code'

    __COMMAND_REGEX = r'!attendance\s+list\s+sessions\s+lecture\s*=\s*(?P<lecture_name>[\w_-]+)'

    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'
    __USERNAME = 'UMBC-Name-Id'

    __SIGNED_IN = 'Signed-In'
    __TIMESTAMP = 'Sign-In-Timestamp'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @staticmethod
    def get_attendance_instance_key(lecture_name, amount_of_time: timedelta):
        """
        lecture_name:YYYYMMDD:HHMMSS:{number of seconds}

        :param amount_of_time:
        :param start_time:
        :param lecture_name:

        :return: a string with the lecture code
        """
        start_time = datetime.now().strftime("%Y%M%D:%X")
        return f'{lecture_name}:{start_time}:{amount_of_time.seconds}', start_time

    def reduced_student_record(self, student):
        new_student_record = {self.__SIGNED_IN: False, self.__TIMESTAMP: ''}
        for x in [self.__FIRST_NAME, self.__LAST_NAME, self.__USERNAME, self.__STUDENT_SECTION]:
            new_student_record[x] = student[x]

        return new_student_record

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self, new_message=None):
        regex_match = re.match(self.__COMMAND_REGEX, self.message.content)
        if not regex_match:
            await self.safe_send(self.message.channel, 'Correct command syntax is: !attendance start lecture = [lecture-name] end=[HH:MM:SS]')
            return False

        lecture_attendance_sections_db = mongo.db[self.__LECTURE_ATTENDANCE_SECTIONS]
        sections = lecture_attendance_sections_db.find_one({self.__KEY_TYPE: self.__SECTION_LIST})
        lecture_name = regex_match.group('lecture_name')

        if lecture_name not in sections:
            await self.safe_send(self.message.channel, 'This was not a valid lecture name.  ')
            return False

        lecture_attendance_sessions = lecture_attendance_sections_db.find_one({self.__KEY_TYPE: self.__SECTION_LIST, self.__LECTURE_NAME: lecture_name})
        if not lecture_attendance_sessions:
            self.message.channel.send(f'There are no lectures with the name {lecture_name}')
            return False

        color = Color.purple()
        embedded_message = Embed(description=f'Sessions for Lecture {lecture_name}', timestamp=datetime.now() + timedelta(hours=5), colour=color)
        for session_key in lecture_attendance_sessions[self.__SESSIONS]:
            session = lecture_attendance_sessions[self.__SESSIONS][session_key]
            embedded_message.add_field(name=session_key, value=f'Start Time: {session[self.__START_TIME]}\tDuration:{session[self.__DURATION]}\tRegular Code:{session[self.__REGULAR_CODE]}\tOverride Code:{session[self.__OVERRIDE_CODE]}')

        await self.message.channel.send(embed=embedded_message)


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        __COMMAND_REGEX = r'!attendance\s+list\s+sessions\s+lecture\s*=\s*(?P<lecture_name>[\w_-]+)'
        if re.match(__COMMAND_REGEX, message.content):
            return True
        return False

    @classmethod
    def get_help(self):
        return 'This command starts a new attendance session.  '
