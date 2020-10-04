from threading import Thread
import paramiko
from paramiko.ssh_exception import AuthenticationException
from discord import User
from discord.errors import Forbidden
import asyncio
import os
import csv
import json
import time
from datetime import datetime, timedelta

from command.submit_interface import add_student, configure_assignment, get_student, grant_extension, setup_interface, remove_assignment, close_assignment
import mongo
from channels import ChannelAuthority


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
    __BASE_SUBMIT_DIR = '/afs/umbc.edu/users/e/r/eric8/pub/cmsc201/fall20'
    __ADMIN__CLOSE_ASSIGNMENT = '/admin/close_assignment.py {} {} {}'
    __ADMIN_CLOSE_EXTENSION = '/admin/close_extension.py {} {} {}'

    def __init__(self, client):
        super().__init__(daemon=True)
        self.submit_admins = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
        self.assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]

        self.updated = False
        self.client = client
        self.ssh_client = None
        self.event_loop = asyncio.get_event_loop()

    def connect_ssh(self):

        if self.ssh_client:
            try:
                self.ssh_client.exec_command('ls')
            except ConnectionError:
                self.ssh_client = None

        if not self.ssh_client:
            self.ssh_client = paramiko.client.SSHClient()
            self.ssh_client.load_system_host_keys()
            admin = self.submit_admins.find_one()
            try:
                self.ssh_client.connect('gl.umbc.edu', username=admin['username'], password=admin['password'])
                print('logged into ssh...')
            except AuthenticationException:
                print('not able to authenticate.')

        return self.ssh_client

    def write_roster(self):
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        with open(os.path.join('csv_dump', self.__ROSTER_NAME), 'w', newline='') as csv_file:
            roster = csv.writer(csv_file)
            roster_list = [[student[self.__USERNAME], student[self.__SECTION]] for student in students_group.find()]
            roster_list.extend([[ta[self.__USERNAME], ta[self.__SECTION]] for ta in ta_group.find()])
            roster_list.extend([[admin[self.__USERNAME], 0] for admin in admin_group.find()])
            roster.writerows(roster_list)

    def close_extension(self, assignment):
        ca: ChannelAuthority = self.client.channel_authority
        self.connect_ssh()
        self.assignments.find_one({'name': assignment['name']})

        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]


        if 'section' in assignment:
            print('closing extension for section', assignment['section'], assignment['name'])
            self.ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN_CLOSE_EXTENSION.format(assignment['name'], assignment['section'], self.__ROSTER_NAME))

            if isinstance(assignment['name'], dict):
                update_open = 'section-extensions.{}.open'.format(assignment['section'])
                self.assignments.update_one({'name': assignment['name']}, {'$set': {update_open: False}})
            else:
                update_open = 'section-extensions.{}'.format(assignment['section'])
                section_id = assignment['section']
                due_date = assignment['due-date']
                self.assignments.update_one({'name': assignment['name']}, {'$set': {update_open: {'section': section_id, 'due-date': due_date, 'name': assignment['name'], 'open': False}}})
            print('{} extension closed for section {}'.format(assignment['name'], assignment['section']))
            # asyncio.run(ca.get_maintenance_channel().send('{} extension closed for section {}'.format(assignment['name'], assignment['section'])))

            for ta in ta_group.find({self.__SECTION: assignment['section']}):
                ta_discord_user: User = self.client.get_user(ta[self.__DISCORD_ID])
                message = "Your section's extension for assignment {} is closed.  You should recopy the files and begin grading.".format(assignment['name'])
                try:
                    asyncio.run_coroutine_threadsafe(ta_discord_user.send(message), self.event_loop)
                except Forbidden:
                    asyncio.run_coroutine_threadsafe(ca.get_maintenance_channel().send('Unable to message the TA.'), self.event_loop)

        elif 'student' in assignment:
            print('closing extension for student', assignment['student'], assignment['name'])
            self.ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN_CLOSE_EXTENSION.format(assignment['name'], assignment['student'], ''))

            if isinstance(assignment['name'], dict):
                update_open = 'student-extensions.{}.open'.format(assignment['student'])
                self.assignments.update_one({'name': assignment['name']}, {'$set': {update_open: False}})
            else:
                update_open = 'student-extensions.{}'.format(assignment['student'])
                student_id = assignment['student']
                due_date = assignment['due-date']
                self.assignments.update_one({'name': assignment['name']}, {'$set': {update_open: {'student': student_id, 'due-date': due_date, 'name': assignment['name'], 'open': False}}})
            print('{} extension closed for {}'.format(assignment['name'], assignment['student']))
            # asyncio.run(ca.get_maintenance_channel().send('{} extension closed for {}'.format(assignment['name'], assignment['student'])))

            the_student = students_group.find_one({self.__UID_FIELD: assignment['student']})
            the_student_name = ' '.join([the_student[self.__FIRST_NAME], the_student[self.__LAST_NAME]])
            for ta in ta_group.find({self.__SECTION: the_student[self.__SECTION]}):
                ta_discord_user: User = self.client.get_user(ta[self.__DISCORD_ID])
                message = '{} ({})\'s extension for assignment {} is now closed.  You should recopy the files and begin grading. '.format(the_student_name, the_student[self.__UID_FIELD], assignment['name'])
                try:
                    asyncio.run_coroutine_threadsafe(ta_discord_user.send(message), self.event_loop)
                except Forbidden:
                    asyncio.run_coroutine_threadsafe(ca.get_maintenance_channel().send('Unable to message the TA.'), self.event_loop)

    def close_assignment(self, assignment_name):
        assignment = self.assignments.find_one({'name': assignment_name})

        if not assignment:
            # await self.client.channel_authority.maintenance_channel.send('Assignment {} was not found. '.format(assignment_name))
            print('Assignment {} was not found. '.format(assignment_name))
            return

        ssh_client = self.connect_ssh()
        ftp_client = ssh_client.open_sftp()
        print('running close assignment script')

        self.write_roster()

        extensions_json = {}
        with open(os.path.join('csv_dump', self.__EXTENSIONS_NAME), 'w') as json_extensions_file:
            for assignment in self.assignments.find():
                extensions_json[assignment['name']] = {'section-extensions': {},
                                                       'student-extensions': {}}

                for student in assignment['student-extensions']:
                    due_date = assignment['student-extensions'][student].strftime('%Y.%m.%d.%H.%M.%S')
                    if assignment['student-extensions'][student] > datetime.now():
                        extensions_json[assignment['name']]['student-extensions'][student] = due_date
                for section in assignment['section-extensions']:
                    due_date = assignment['section-extensions'][section].strftime('%Y.%m.%d.%H.%M.%S')
                    extensions_json[assignment['name']]['section-extensions'][section] = due_date

            json_extensions_file.write(json.dumps(extensions_json, indent='\t'))

        ftp_client.put(os.path.join('csv_dump', self.__ROSTER_NAME), self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME)
        ftp_client.put(os.path.join('csv_dump', self.__EXTENSIONS_NAME), self.__BASE_SUBMIT_DIR + '/admin/' + self.__EXTENSIONS_NAME)
        ftp_client.close()

        roster_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME
        extensions_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__EXTENSIONS_NAME
        print('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN__CLOSE_ASSIGNMENT.format(assignment_name, roster_path, extensions_path))
        self.ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN__CLOSE_ASSIGNMENT.format(assignment_name, roster_path, extensions_path))
        self.assignments.update_one({'name': assignment_name}, {'$set': {'open': False}})

    def get_assignment_queue(self):
        assignment_queue = []
        for assignment in self.assignments.find():
            if assignment['open']:
                assignment_queue.append(assignment)
            if 'student-extensions' in assignment:
                for student in assignment['student-extensions']:
                    if isinstance(assignment['student-extensions'][student], dict):
                        if assignment['student-extensions'][student]['open']:
                            assignment_queue.append(assignment['student-extensions'][student])
                    else:
                        assignment_queue.append({'name': assignment['name'], 'student': student, 'open': True, 'due-date': assignment['student-extensions'][student]})
            if 'section-extensions' in assignment:
                for section in assignment['section-extensions']:
                    if isinstance(assignment['section-extensions'][section], dict):
                        if assignment['section-extensions'][section]['open']:
                            assignment_queue.append(assignment['section-extensions'][section])
                    else:
                        assignment_queue.append({'name': assignment['name'], 'section': section, 'open': True, 'due-date': assignment['section-extensions'][section]})

        assignment_queue.sort(key=lambda x: x['due-date'])

        return assignment_queue

    def print_assignment_queue(self):
        assignment_queue = self.get_assignment_queue()
        print('\n'.join(str(i) + ": " + str(a) for i, a in enumerate(assignment_queue)))

    def run(self):
        assignment_queue = self.get_assignment_queue()
        while True:
            try:
                if assignment_queue:
                    for assignment in assignment_queue:
                        if assignment['due-date'] <= datetime.now():
                            if 'student' in assignment:
                                self.close_extension(assignment)
                            elif 'section' in assignment:
                                self.close_extension(assignment)
                            else:
                                self.close_assignment(assignment['name'])

                if assignment_queue and assignment_queue[0]['due-date'] - timedelta(seconds=60) < datetime.now():
                    time.sleep(1)
                else:
                    time.sleep(30)

                assignment_queue = self.get_assignment_queue()

            except Exception as e:
                # this may be overkill but basically any exception should be printed, then the loop should start again.
                # assignment closing should never be killed by an exception
                print('Exception in the assignment queue')
                print(type(e), e)
