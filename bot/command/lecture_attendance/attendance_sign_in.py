from discord import Message, Client
import command
import mongo
import re
from datetime import datetime, timedelta
from asyncio.locks import Lock


@command.command_class
class StudentSignIn(command.Command):
    sign_in_lock = Lock()

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

    __COMMAND_REGEX = r'!sign(\s+|-)in\s+(?P<auth_code>\w+)'
    __MONGO_ID = '_id'
    __DISCORD_ID = 'discord'

    __SIGNED_IN = 'Signed-In'
    __TIMESTAMP = 'Sign-In-Timestamp'
    __TIME_CODE = "%Y%m%d-%X"
    __STUDENT_LIST = 'student-list'
    __USERNAME = 'UMBC-Name-Id'

    __STUDENTS_GROUP = 'student'

    permissions = {'student': True, 'ta': True, 'admin': True}

    async def sign_in_database_update(self, the_database, the_student, session_key, lecture_name, the_session):
        the_session[self.STUDENT_LIST][the_student[self.__USERNAME]][self.__SIGNED_IN] = True
        the_session[self.STUDENT_LIST][the_student[self.__USERNAME]][self.__TIMESTAMP] = datetime.now().strftime(self.__TIME_CODE)
        # perhaps use a mutex to prevent multiple updates from colliding
        await self.sign_in_lock.acquire()
        the_database.update_one({self.__KEY_TYPE: self.__DAY_LIST, self.__LECTURE_NAME: lecture_name},
                                                  {'$set': {f"{self.__SESSIONS}.{session_key}.{self.__STUDENT_LIST}.{the_student[self.__USERNAME]}":
                                                                the_session[self.__STUDENT_LIST][the_student[self.__USERNAME]]}})
        self.sign_in_lock.release()

    @command.Command.authenticate
    async def handle(self, new_message=None):
        regex_match = re.match(self.__COMMAND_REGEX, self.message.content)
        if not regex_match:
            await self.safe_send(self.message.channel, 'Unable to create the new lecture attendance section.  Invalid command format. \nShould be !attendance register lecture [lec_name] sections = 11, 12, 13, 14, 15, 16')
            return False

        lecture_attendance_sections_db = mongo.db[self.__LECTURE_ATTENDANCE_SECTIONS]
        lecture_attendance_db = mongo.db[self.__LECTURE_ATTENDANCE]

        sections = lecture_attendance_sections_db.find_one({self.__KEY_TYPE: self.__SECTION_LIST})

        if not sections:
            await self.message.author.send('There are not currently any sections. ')

        authentication_code = regex_match.group('auth_code')

        found_one = False
        checked_in_messages = []
        late_messages = []

        students_group = mongo.db[self.__STUDENTS_GROUP]
        the_student = students_group.find_one({self.__DISCORD_ID: self.message.author.id})

        if not the_student:
            student_member = await self.guild.fetch_member(self.message.author.id)
            await student_member.send('You are not a recognized student.  If you are a student, then contact your Professor to tell them that you were not found in the student database. ')
            return False

        for lecture_name in sections:
            if lecture_name in [self.__KEY_TYPE, self.__MONGO_ID]:
                continue
            lecture_attendance_sessions = lecture_attendance_sections_db.find_one({self.__KEY_TYPE: self.__DAY_LIST, self.__LECTURE_NAME: lecture_name})
            if not lecture_attendance_sessions:
                continue

            for session_key in lecture_attendance_sessions[self.__SESSIONS]:
                the_session = lecture_attendance_sessions[self.__SESSIONS][session_key]
                if authentication_code == the_session[self.__REGULAR_CODE]:
                    attendance_session = lecture_attendance_db.find_one({self.__SESSION_KEY: session_key})
                    if attendance_session:
                        found_one = True
                        session_start_time = datetime.strptime(attendance_session[self.__START_TIME], self.__TIME_CODE)
                        session_duration = timedelta(seconds=int(attendance_session[self.__DURATION]))
                        if session_start_time + session_duration > datetime.now():
                            checked_in_messages.append(f'You have checked into {lecture_name}. ')
                            # update the database with the check-in
                            await self.sign_in_database_update(lecture_attendance_sections_db, the_student, session_key, lecture_name, the_session)
                        else:
                            late_messages.append(f'You have entered the correct code for the {session_key} but the attendance period is closed. ')
                if authentication_code == lecture_attendance_sessions[self.__SESSIONS][session_key][self.__OVERRIDE_CODE]:
                    attendance_session = lecture_attendance_db.find_one({self.__SESSION_KEY: session_key})
                    if attendance_session:
                        found_one = True
                        await self.message.author.send(f'You have entered the correct override code for the {session_key} and are now signed in.  ')
                        await self.sign_in_database_update(lecture_attendance_sections_db, the_student, session_key, lecture_name, the_session)
        if found_one:
            for check_in_message in checked_in_messages:
                await self.message.channel.send(check_in_message)
            if not checked_in_messages:
                for late_message in late_messages:
                    await self.message.channel.send(late_message)
        else:
            await self.message.channel.send(f'Unable to find any session with the code {authentication_code}')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        __COMMAND_REGEX = r'!sign(\s+|-)in\s+(?P<auth_code>\w+)'
        if re.match(__COMMAND_REGEX, message.content):
            return True
        return False

    @classmethod
    def get_help(self):
        return 'This command will register a set of sections as a lecture for the purposes of attendance. '
