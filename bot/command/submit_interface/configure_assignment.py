import re
from datetime import datetime, timedelta
from discord import Message, Client

from pymongo.results import InsertOneResult, UpdateResult

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority


@command.command_class
class ConfigureAssignment(command.Command):
    __COMMAND_REGEX = r"!submit\s+configure\s+(?P<assign_name>\w+)\s+(?P<due_date>\d{2}-\d{2}-\d{4})\s+(?P<due_time>\d{2}:\d{2}:\d{2})(\s+--admin=(?P<admin>\w+))?"
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        ra: RoleAuthority = RoleAuthority(self.guild)
        if ra.is_admin(self.message.author) and ca.is_maintenance_channel(self.message.channel):
            match = re.match(self.__COMMAND_REGEX, self.message.content)
            submit_col = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
            assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]

            # keep this for when we need to update on the server.
            if match.group('admin'):
                admin_match = submit_col.find_one({'username': match.group('admin')})
            else:
                admin_match = submit_col.find_one({})

            assignment_name = match.group('assign_name')
            due_date = datetime.strptime(' '.join([match.group('due_date'), match.group('due_time')]), '%m-%d-%Y %H:%M:%S')
            duplicate = assignments.find_one({'name': assignment_name})
            if duplicate:
                if duplicate['due-date'] == due_date:
                    await self.message.channel.send('There is a duplicate assignment')
                else:
                    await self.message.channel.send('Updating due date for {} to {}'.format(assignment_name, due_date.strftime('%m-%d-%Y %H:%M:%S')))
                    assignments.update_one({'name': assignment_name}, {'$set': {'due-date': due_date}})
                    self.client.submit_daemon.updated = True
            else:
                await self.message.channel.send('Configuring Assignment {}...'.format(assignment_name))
                ir = assignments.insert_one({'name': assignment_name, 'due-date': due_date})
                if ir.inserted_id:
                    await self.message.channel.send('Assignment {} added to database.'.format(assignment_name))
                    self.client.submit_daemon.updated = True
                else:
                    await self.message.channel.send('Error: Assignment {} not added to database.'.format(assignment_name))


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+configure\s+(?P<assign_name>\w+)\s+(?P<due_date>\d{2}-\d{2}-\d{4})\s+(?P<due_time>\d{2}:\d{2}:\d{2})(\s+(?P<admin>--admin=\w+))?", message.content):
            return True
        return False
