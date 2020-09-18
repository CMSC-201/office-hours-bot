from threading import Thread
import paramiko
from paramiko.ssh_exception import AuthenticationException
import asyncio
import os
import csv
import json
import time
from datetime import datetime, timedelta

from command.submit_interface import add_student, configure_assignment, get_student, grant_extension, setup_interface
import mongo


class SubmitDaemon(Thread):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'
    __SECTION = 'Section'

    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'

    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'
    __BASE_SUBMIT_DIR = '/afs/umbc.edu/users/e/r/eric8/pub/cmsc201/fall20'
    __ADMIN__CLOSE_ASSIGNMENT = '/admin/close_assignment.py {} {} {}'

    def __init__(self, client):
        super().__init__(daemon=True)
        self.submit_admins = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
        self.assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]

        self.updated = False
        self.client = client
        self.ssh_client = None

    def get_earliest_time(self):
        earliest_assignment = None

        if self.assignments.find_one({'open': True}):
            earliest_assignment = min((assignment for assignment in self.assignments.find({'open': True})), key=lambda x: x['due-date'])

        return earliest_assignment

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

    async def close_assignment(self, assignment_name):
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        assignment = self.assignments.find_one({'name': assignment_name})

        if not assignment:
            await self.client.channel_authority.maintenance_channel.send('Assignment {} was not found. '.format(assignment_name))
            return

        ssh_client = self.connect_ssh()
        ftp_client = ssh_client.open_sftp()
        print('running close assignment script')

        with open(os.path.join('csv_dump', self.__ROSTER_NAME), 'w', newline='') as csv_file:
            roster = csv.writer(csv_file)
            roster_list = [[student[self.__USERNAME], student[self.__SECTION]] for student in students_group.find()]
            roster_list.extend([[ta[self.__USERNAME], ta[self.__SECTION]] for ta in ta_group.find()])
            roster_list.extend([[admin[self.__USERNAME], 0] for admin in admin_group.find()])
            roster.writerows(roster_list)

        extensions = {}
        with open(os.path.join('csv_dump', self.__EXTENSIONS_NAME), 'w') as json_extensions_file:
            for assignment in self.assignments.find():
                assignment_section_extensions = assignment.get('section-extensions', {})
                assignment_student_extensions = assignment.get('student-extensions', {})
                extensions[assignment['name']] = {'section-extensions': assignment_section_extensions,
                                                  'student-extensions': assignment_student_extensions}

            json_extensions_file.write(json.dumps(extensions, indent='\t'))

        ftp_client.put(os.path.join('csv_dump', self.__ROSTER_NAME), self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME)
        ftp_client.put(os.path.join('csv_dump', self.__EXTENSIONS_NAME), self.__BASE_SUBMIT_DIR + '/admin/' + self.__EXTENSIONS_NAME)
        ftp_client.close()

        roster_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME
        extensions_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__EXTENSIONS_NAME
        print('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN__CLOSE_ASSIGNMENT.format(assignment_name, roster_path, extensions_path))
        self.ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN__CLOSE_ASSIGNMENT.format(assignment_name, roster_path, extensions_path))
        self.assignments.update_one({'name': assignment_name}, {'$set': {'open': False}})

    def run(self):

        nearest_assignment = self.get_earliest_time()
        while True:
            # sleep for a minute until an update comes in or until we're close enough to a due date deadline.
            while not self.updated and nearest_assignment and nearest_assignment['due-date'] > datetime.now():
                time.sleep(60)

            while nearest_assignment and datetime.now() <= nearest_assignment['due-date']:
                time.sleep(0.25)

            if nearest_assignment:
                for assignment in self.assignments.find():
                    if assignment['due-date'] <= datetime.now() and assignment['open']:
                        asyncio.run(self.close_assignment(assignment['name']))

                    time.sleep(30)

            self.updated = False
            nearest_assignment = self.get_earliest_time()


