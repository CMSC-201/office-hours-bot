from discord import Message, Client
import command
import mongo
import re
from datetime import datetime, timedelta
from asyncio.locks import Lock


@command.command_class
class ModifyAttendanceRecord(command.Command):
    __LECTURE_ATTENDANCE = 'lecture-attendance'
    __LECTURE_ATTENDANCE_SECTIONS = 'lecture-attendance-sections'
    __SESSIONS = 'sessions'
    __LECTURE_NAME = 'lecture-name'
    __SESSION_KEY = 'session-key'

    __KEY_TYPE = 'key-type'
    __SECTION_LIST = 'section-list'
    __DAY_LIST = 'day-list'

    __REGULAR_CODE = 'regular-code'
    __OVERRIDE_CODE = 'override-code'

    __COMMAND_REGEX = r'!attendance\s+modify\s+record\s+lecture=(?P<lecture_name>[\w_-]+)\s+(?P<session_code>[\w_:-]+)\s+(?P<student_id>\w+)\s+(?P<in_or_out>\w+)'
    __MONGO_ID = '_id'
    __DISCORD_ID = 'discord'

    __SIGNED_IN = 'Signed-In'
    __TIMESTAMP = 'Sign-In-Timestamp'
    __TIME_CODE = "%Y%m%d-%X"
    __STUDENT_LIST = 'student-list'
    __USERNAME = 'UMBC-Name-Id'

    __STUDENTS_GROUP = 'student'

    permissions = {'student': True, 'ta': True, 'admin': True}

    async def sign_in_database_update(self, the_database, the_student, session_key, lecture_name, the_session, set_val):
        the_session[self.__STUDENT_LIST][the_student[self.__USERNAME]][self.__SIGNED_IN] = set_val
        the_session[self.__STUDENT_LIST][the_student[self.__USERNAME]][self.__TIMESTAMP] = datetime.now().strftime(self.__TIME_CODE)
        # perhaps use a mutex to prevent multiple updates from colliding
        return the_database.update_one({self.__SESSION_KEY: session_key}, {'$set': {f"{self.__STUDENT_LIST}.{the_student[self.__USERNAME]}": the_session[self.__STUDENT_LIST][the_student[self.__USERNAME]]}})

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self, new_message=None):
        regex_match = re.match(self.__COMMAND_REGEX, self.message.content)
        if not regex_match:
            await self.safe_send(self.message.channel, 'Unable to begin modifying the record since the expression does not match the command. ')
            return False

        lecture_attendance_sections_db = mongo.db[self.__LECTURE_ATTENDANCE_SECTIONS]
        lecture_attendance_db = mongo.db[self.__LECTURE_ATTENDANCE]

        sections = lecture_attendance_sections_db.find_one({self.__KEY_TYPE: self.__SECTION_LIST})

        if not sections:
            await self.message.author.send('There are not currently any sections. ')

        lecture_name = regex_match.group('lecture_name')
        the_student_id = regex_match.group('student_id')
        session_code = regex_match.group('session_code')
        in_or_out = regex_match.group('in_or_out')

        students_group = mongo.db[self.__STUDENTS_GROUP]
        the_student = students_group.find_one({self.__USERNAME: the_student_id})

        if not the_student:
            await self.message.channel.send(f'Unable to find the student {the_student_id}')
            return False

        if lecture_name in sections:
            lecture_attendance_sessions = lecture_attendance_sections_db.find_one({self.__KEY_TYPE: self.__DAY_LIST, self.__LECTURE_NAME: lecture_name})
            if not lecture_attendance_sessions:
                await self.message.channel.send(f'Unable to find any lecture sessions for {lecture_name}.')
                return False
            if not session_code in lecture_attendance_sessions[self.__SESSIONS]:
                await self.message.channel.send(f'Unable to find the session by the code {session_code} for {lecture_name}.')
                return False

            lecture_attendance_session = lecture_attendance_db.find_one({self.__SESSION_KEY: session_code})

            if in_or_out.lower().strip() in ['in', 'sign-in', 'check-in', 'true']:
                if await self.sign_in_database_update(lecture_attendance_db, the_student, session_code, lecture_name, lecture_attendance_session, True):
                    await self.message.channel.send(f'{the_student[self.__USERNAME]} attendance record for session code {session_code} has been modified to True')
                else:
                    await self.message.channel.send(f'{the_student[self.__USERNAME]} attendance record for session code {session_code} has been not been modified.')
            elif in_or_out.lower().strip() in ['out', 'sign-out', 'check-out', 'false']:
                if await self.sign_in_database_update(lecture_attendance_db, the_student, session_code, lecture_name, lecture_attendance_session, False):
                    await self.message.channel.send(f'{the_student[self.__USERNAME]} attendance record for session code {session_code} has been modified to False')
                else:
                    await self.message.channel.send(f'{the_student[self.__USERNAME]} attendance record for session code {session_code} has been not been modified.')
    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        __COMMAND_REGEX = r'!attendance\s+modify\s+record\s+lecture=(?P<lecture_name>[\w_-]+)\s+(?P<session_code>[\w_:-]+)\s+(?P<student_id>\w+)\s+(?P<in_or_out>\w+)'
        if re.match(__COMMAND_REGEX, message.content):
            return True
        return False

    @classmethod
    def get_help(self):
        return 'This command will register a set of sections as a lecture for the purposes of attendance. '
