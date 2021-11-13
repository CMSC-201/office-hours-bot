from discord import Message, Client
import command
import mongo
import re
from datetime import timedelta, datetime
import random


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

    __COMMAND_REGEX = r'!attendance\s+start\s+session\s*=\s*(?P<lecture_name>[\w_-]+)\s+(time\s*=\s*(?P<timer>\d{2}:\d{2}:\d{2}))?'

    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'
    __USERNAME = 'UMBC-Name-Id'
    __TIME_CODE = "%Y%m%d-%X"

    __SIGNED_IN = 'Signed-In'
    __TIMESTAMP = 'Sign-In-Timestamp'

    permissions = {'student': False, 'ta': False, 'admin': True}

    def get_attendance_instance_key(self, lecture_name, amount_of_time: timedelta):
        """
        lecture_name:YYYYMMDD:HHMMSS:{number of seconds}

        :param amount_of_time:
        :param start_time:
        :param lecture_name:

        :return: a string with the lecture code
        """
        start_time = datetime.now().strftime(self.__TIME_CODE)
        return f'{lecture_name}-T{start_time}-D{amount_of_time.seconds}', start_time

    def reduced_student_record(self, student):
        new_student_record = {self.__SIGNED_IN: False, self.__TIMESTAMP: ''}
        for x in [self.__FIRST_NAME, self.__LAST_NAME, self.__USERNAME, self.__STUDENT_SECTION]:
            new_student_record[x] = student[x]

        return new_student_record

    @command.Command.authenticate
    async def handle(self, new_message=None):
        regex_match = re.match(self.__COMMAND_REGEX, self.message.content)
        if not regex_match:
            await self.safe_send(self.message.channel, 'Correct command syntax is: !attendance start lecture = [lecture-name] end=[HH:MM:SS]')
            return False

        lecture_attendance_sections_db = mongo.db[self.__LECTURE_ATTENDANCE_SECTIONS]
        lecture_attendance_db = mongo.db[self.__LECTURE_ATTENDANCE]

        sections = lecture_attendance_sections_db.find_one({self.__KEY_TYPE: self.__SECTION_LIST})
        lecture_name = regex_match.group('lecture_name')

        if lecture_name not in sections:
            await self.safe_send(self.message.channel, 'This was not a valid lecture name.  ')
            return False

        time_string = regex_match.group('timer')
        timer_numbers = [int(x) for x in time_string.split(':')]
        timer_amount = timedelta(hours=timer_numbers[0], minutes=timer_numbers[1], seconds=timer_numbers[2])

        lecture_attendance_sessions = lecture_attendance_sections_db.find_one({self.__KEY_TYPE: self.__SECTION_LIST, self.__LECTURE_NAME: lecture_name})
        if not lecture_attendance_sessions:
            lecture_attendance_sessions = {self.__KEY_TYPE: self.__SECTION_LIST, self.__LECTURE_NAME: lecture_name, self.__SESSIONS: {}}
            lecture_attendance_sections_db.insert_one(lecture_attendance_sessions)

        # check for a currently running attendance session for the lecture
        for session_key in lecture_attendance_sessions[self.__SESSIONS]:
            session_start_time = datetime.strptime(lecture_attendance_sessions[self.__SESSIONS][session_key][self.__START_TIME], self.__TIME_CODE)
            session_duration = timedelta(seconds=int(lecture_attendance_sessions[self.__SESSIONS][session_key][self.__DURATION]))
            if session_start_time + session_duration > datetime.now():
                await self.safe_send(self.message.channel, f'An attendance session is currently ongoing for the lecture section {lecture_name}.  ')
                return False

        # no attendance session is ongoing for the lecture section, start a new one
        students_group = mongo.db[self.__STUDENTS_GROUP]

        student_list = {}
        for section_num in sections[lecture_name]:
            student_list.update({student[self.__USERNAME]: self.reduced_student_record(student) for student in students_group.find({self.__STUDENT_SECTION: str(section_num)})})

        regular_code = str(random.randint(1, 9999)).zfill(4)
        override_code = str(random.randint(1, 99999)).zfill(5)

        new_session_key, start_time = self.get_attendance_instance_key(lecture_name, timer_amount)
        lecture_attendance_sessions[self.__SESSIONS][new_session_key] = {self.__START_TIME: start_time, self.__DURATION: timer_amount.seconds, self.__REGULAR_CODE: regular_code, self.__OVERRIDE_CODE: override_code}

        new_attendance_record = {self.__SESSION_KEY: new_session_key, self.__START_TIME: start_time, self.__DURATION: timer_amount.seconds,
                                 self.__REGULAR_CODE: regular_code, self.__OVERRIDE_CODE: override_code, self.__STUDENT_LIST: student_list}
        lecture_attendance_sections_db.update_one({self.__KEY_TYPE: self.__SECTION_LIST, self.__LECTURE_NAME: lecture_name}, {'$set': {f"{self.__SESSIONS}": lecture_attendance_sessions[self.__SESSIONS]}})
        lecture_attendance_db.insert_one(new_attendance_record)

        await self.message.channel.send(f'Starting a new attendance session for lecture {lecture_name} with a duration of {timer_amount.seconds} seconds, the code for the session is {regular_code}.')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        __COMMAND_REGEX = r'!attendance\s+start\s+session\s*=\s*(?P<lecture_name>[\w_-]+)\s+(time\s*=\s*(?P<timer>\d{2}:\d{2}:\d{2}))?'
        if re.match(__COMMAND_REGEX, message.content):
            return True
        return False

    @classmethod
    def get_help(self):
        return 'This command starts a new attendance session.  '
