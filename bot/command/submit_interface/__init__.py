import locale
from threading import Thread, Lock
from typing import Optional
import paramiko
from paramiko.ssh_exception import AuthenticationException, SSHException
from discord import User
from discord.errors import Forbidden
import logging
import asyncio
import os
import csv
import json
import time
from datetime import datetime, timedelta
import globals
import mongo
from channels import ChannelAuthority
from submit_interface.close_extension import StudentExtensionClosureThread

from submit_exceptions import AlreadyClosingException


class SubmitDaemon(Thread):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'
    __SECTION = 'Section'
    __DISCORD_ID = 'discord'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'
    __UID_FIELD = 'UMBC-Name-Id'

    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'

    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'
    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']
    __ADMIN__CLOSE_ASSIGNMENT = '/admin/close_assignment.py {} {} {}'
    __CLOSE_STUDENT_EXTENSION = '/admin/close_extension.py {} student={}'
    __CLOSE_SECTION_EXTENSION = '/admin/close_extension.py {} section={} {}'

    __COPY_STUDENT_EXTENSION = '/admin/'

    def __init__(self, client):
        super().__init__(daemon=True)
        self.submit_admins = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
        self.assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]

        self.updated = False
        self.client = client
        self.ssh_client: Optional[paramiko.client.SSHClient] = None
        self.event_loop = asyncio.get_event_loop()

        self.lock = Lock()

    def connect_ssh(self):

        if self.ssh_client and (not self.ssh_client.get_transport() or not self.ssh_client.get_transport().is_active()):
            self.ssh_client = None

        if not self.ssh_client:
            self.ssh_client = paramiko.client.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            admin = self.submit_admins.find_one()
            try:
                self.ssh_client.connect('gl.umbc.edu', username=admin['username'], password=admin['password'], timeout=10)
                logging.info('Logged into ssh on the GL server.')
            except AuthenticationException:
                logging.info('GL server not able to authenticate.')

        return self.ssh_client

    def write_roster(self):
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        if not os.path.exists('csv_dump'):
            os.makedirs('csv_dump')

        with open(os.path.join('csv_dump', self.__ROSTER_NAME), 'w', newline='') as csv_file:
            roster = csv.writer(csv_file)
            roster_list = [[student[self.__USERNAME], student[self.__SECTION]] for student in students_group.find()]
            roster_list.extend([[ta[self.__USERNAME], ta[self.__SECTION]] for ta in ta_group.find()])
            roster_list.extend([[admin[self.__USERNAME], 0] for admin in admin_group.find()])
            roster.writerows(roster_list)

    async def send_extension_closure_messages(self, ca: ChannelAuthority, search_group, message: str):
        """
        Sends an extension closure message to the admins and tas associated with a particular section

        :param ca: a ChannelAuthority object
        :param search_group: the mongo find iterator
        :param message: the string message
        """
        for user in search_group:
            discord_user: User = await self.client.fetch_user(user[self.__DISCORD_ID])
            try:
                asyncio.run_coroutine_threadsafe(discord_user.send(message), self.event_loop)
            except Forbidden:
                asyncio.run_coroutine_threadsafe(ca.get_maintenance_channel().send('Unable to message the TA.'), self.event_loop)

    async def close_extension(self, assignment):
        try:

            logging.info('Starting Close Extension Function')
            ca: ChannelAuthority = ChannelAuthority(self.client.guilds[0])

            the_assignment = self.assignments.find_one({'name': assignment['name']})

            students_group = mongo.db[self.__STUDENTS_GROUP]
            ta_group = mongo.db[self.__TA_GROUP]
            admin_group = mongo.db[self.__ADMIN_GROUP]

            if 'section' in assignment:
                if not the_assignment['section-extensions'][assignment['section']]['open']:
                    raise AlreadyClosingException(f'This extension has already started it\'s close function: {assignment["name"]}: {assignment["section"]}', assignment)

                self.connect_ssh()

                update_open = f'section-extensions.{assignment["section"]}'
                section_id = assignment['section']
                due_date = assignment['due-date']
                logging.info(f'closing {assignment["name"]} extension for section {assignment["section"]}')
                print('python3 ' + self.__BASE_SUBMIT_DIR + self.__CLOSE_SECTION_EXTENSION.format(assignment['name'], assignment['section'], self.__ROSTER_NAME))
                _, std_output, _ = self.ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + self.__CLOSE_SECTION_EXTENSION.format(assignment['name'], assignment['section'], self.__ROSTER_NAME))
                for line in std_output.readlines():
                    print(line)

                update_open = 'section-extensions.{}'.format(assignment['section'])
                section_id = assignment['section']
                due_date = assignment['due-date']
                self.assignments.update_one({'name': assignment['name']}, {'$set': {update_open: {'section': section_id, 'due-date': due_date, 'name': assignment['name'], 'open': False}}})

                maintenance_message = 'Section {}\'s extension for assignment {} is now closed.'.format(section_id, assignment['name'])
                await ca.get_maintenance_channel().send(maintenance_message)

                logging.info('{} extension closed for section {}'.format(assignment['name'], assignment['section']))

                message = "Your section's extension for assignment {} is closed.  You should recopy the files and begin grading.".format(assignment['name'])
                await self.send_extension_closure_messages(ca, ta_group.find({self.__SECTION: assignment['section']}), message)
                await self.send_extension_closure_messages(ca, admin_group.find({self.__SECTION: assignment['section']}), message)
        except AlreadyClosingException as ace:
            logging.info('Preventing Multiple Runs: ' + ace.message)
        except Exception as e:
            logging.info('An exception has occured during an extension closure.')
            logging.error(str(type(e)) + " : " + str(e))

    async def close_assignment(self, assignment_name):
        ca: ChannelAuthority = ChannelAuthority(self.client.guilds[0])
        maintenance_channel = ca.get_maintenance_channel()

        assignment = self.assignments.find_one({'name': assignment_name})

        if not assignment:
            await maintenance_channel.send('Assignment {} was not found. '.format(assignment_name))
            logging.info('Assignment {} was not found. '.format(assignment_name))
            return

        logging.info('Running close assignment script for assignment {}'.format(assignment_name))

        self.write_roster()

        extensions_json = {}
        with open(os.path.join('csv_dump', self.__EXTENSIONS_NAME), 'w') as json_extensions_file:
            for assignment in self.assignments.find():
                extensions_json[assignment['name']] = {'section-extensions': {},
                                                       'student-extensions': {}}

                for student in assignment['student-extensions']:
                    due_date = assignment['student-extensions'][student]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                    if assignment['student-extensions'][student]['due-date'] > datetime.now():
                        extensions_json[assignment['name']]['student-extensions'][student] = due_date
                for section in assignment['section-extensions']:
                    due_date = assignment['section-extensions'][section]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                    extensions_json[assignment['name']]['section-extensions'][section] = due_date

            json_extensions_file.write(json.dumps(extensions_json, indent='\t'))

        ssh_client = self.connect_ssh()
        ftp_client = ssh_client.open_sftp()
        ftp_client.put(os.path.join('csv_dump', self.__ROSTER_NAME), self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME)
        ftp_client.put(os.path.join('csv_dump', self.__EXTENSIONS_NAME), self.__BASE_SUBMIT_DIR + '/admin/' + self.__EXTENSIONS_NAME)
        ftp_client.close()
        await maintenance_channel.send('New roster and extension files written to GL server by FTP. ')
        roster_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME
        extensions_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__EXTENSIONS_NAME
        print('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN__CLOSE_ASSIGNMENT.format(assignment_name, roster_path, extensions_path))
        self.ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN__CLOSE_ASSIGNMENT.format(assignment_name, roster_path, extensions_path))
        await maintenance_channel.send('Sending ssh command to close assignment {} on the GL server. '.format(assignment_name))
        self.assignments.update_one({'name': assignment_name}, {'$set': {'open': False}})
        await maintenance_channel.send('Updating Database with assignment {} closure. '.format(assignment_name))

    def get_assignment_queue(self):
        assignment_queue = []
        for assignment in self.assignments.find():
            if assignment['open']:
                assignment_queue.append(assignment)
            if 'student-extensions' in assignment:
                for student in assignment['student-extensions']:
                    if assignment['student-extensions'][student]['open']:
                        assignment_queue.append(assignment['student-extensions'][student])
            if 'section-extensions' in assignment:
                for section in assignment['section-extensions']:
                    if assignment['section-extensions'][section]['open']:
                        assignment_queue.append({'name': assignment['name'], 'section': section, 'open': True, 'due-date': assignment['section-extensions'][section]['due-date']})

        assignment_queue.sort(key=lambda x: x['due-date'])

        return assignment_queue

    def print_assignment_queue(self):
        assignment_queue = self.get_assignment_queue()
        print('\n'.join(str(i) + ": " + str(a) for i, a in enumerate(assignment_queue)))

    def close_student_extension(self, assignment_data):
        admin = self.submit_admins.find_one()
        ca: ChannelAuthority = ChannelAuthority(self.client.guilds[0])
        report_name = self.get_report_name(assignment_data)
        status_report = {'assignment': assignment_data, 'closed': False, 'sent': False, 'thread': None}
        closure_thread = StudentExtensionClosureThread(assignment_data['name'], assignment_data['student'], assignment_data['due-date'], admin, self.lock, self.event_loop, status_report, ca.get_maintenance_channel())
        status_report['thread'] = closure_thread
        logging.info('Created Thread for {} extension closure for {} .'.format(assignment_data['name'], assignment_data['student']))
        closure_thread.start()
        logging.info('Started Thread for {} extension closure for {} .'.format(assignment_data['name'], assignment_data['student']))
        return report_name, status_report

    def check_reports(self, current_reports):
        ca: ChannelAuthority = ChannelAuthority(self.client.guilds[0])
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        sent_report_names = []
        for report_name in current_reports:
            report = current_reports[report_name]
            if report['closed'] and not report['sent']:
                asyncio.run_coroutine_threadsafe(self.send_extension_closure_messages(ca, ta_group.find({self.__SECTION: report['student-section']}), report["ta-message"]), self.event_loop)
                asyncio.run_coroutine_threadsafe(self.send_extension_closure_messages(ca, admin_group.find({self.__SECTION: report['student-section']}), report["ta-message"]), self.event_loop)
                report['sent'] = True
                sent_report_names.append(report_name)
            elif report['sent']:
                sent_report_names.append(report_name)

            if 'failed' in report and report['failed']:
                sent_report_names.append(report)

        for name in sent_report_names:
            del current_reports[name]

    @staticmethod
    def get_report_name(assignment):
        report_name = ''
        if 'student' in assignment:
            report_name = f'{assignment["name"]}.{assignment["student"]}.{assignment["due-date"].strftime("%Y.%m.%d.%H.%M.%S")}'

        return report_name

    def run(self):
        current_reports = {}
        while True:
            assignment_queue = self.get_assignment_queue()
            try:
                for assignment in assignment_queue:
                    if assignment['due-date'] <= datetime.now():
                        if 'student' in assignment and self.get_report_name(assignment) not in current_reports:
                            logging.info('Detected new assignment {} extension for {} to close.'.format(assignment['name'], assignment['student']))
                            report_name, report = self.close_student_extension(assignment)
                            current_reports[report_name] = report
                        elif 'section' in assignment:
                            logging.info('Closing {} extension for section {} in the thread.'.format(assignment['name'], assignment['section']))
                            asyncio.run_coroutine_threadsafe(self.close_extension(assignment), self.event_loop)
                        else:
                            logging.info('Closing the assignment: {}'.format(assignment['name']))
                            asyncio.run_coroutine_threadsafe(self.close_assignment(assignment['name']), self.event_loop)

                self.check_reports(current_reports)

            except Exception as e:
                # this may be overkill but basically any exception should be printed, then the loop should start again.
                # assignment closing should never be killed by an exception
                logging.error('Exception in the assignment queue')
                logging.error(str(type(e)) + " : " + str(e))

            # keep this to prevent any exception from looping through very quickly causing multiple closures.
            time.sleep(5)
