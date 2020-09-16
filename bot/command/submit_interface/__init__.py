from command.submit_interface import add_student, configure_assignment, get_student, grant_extension, setup_interface
from threading import Thread
import paramiko

import time
from datetime import datetime, timedelta
import mongo


class SubmitDaemon(Thread):

    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    def __init__(self, client):
        super().__init__(daemon=True)
        self.submit_admins = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
        self.assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]
        self.updated = False
        self.client = client

    def get_earliest_time(self):
        earliest_time = datetime.now() + timedelta(weeks=100)

        if self.assignments.find_one({}):
            earliest_time = min(assignment['due-date'] for assignment in self.assignments.find())

        return earliest_time

    def run(self):

        nearest_time = self.get_earliest_time()
        while True:
            # sleep for a minute until an update comes in or until we're close enough to a due date deadline.
            while not self.updated and nearest_time + timedelta(seconds=60) > datetime.now():
                time.sleep(60)
            print('hello')
            self.updated = False
            nearest_time = self.get_earliest_time()


