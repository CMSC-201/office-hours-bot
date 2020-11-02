import re
from discord import Message, Client

from pymongo.results import InsertOneResult, UpdateResult

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority


@command.command_class
class SetupInterface(command.Command):
    __COMMAND_REGEX = r"!submit\s+setup\s+(?P<username>\w+)\s+(?P<password>.*)"
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'

    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        ra: RoleAuthority = RoleAuthority(self.guild)
        if ra.is_admin(self.message.author) and ca.is_maintenance_channel(self.message.channel):
            match = re.match(self.__COMMAND_REGEX, self.message.content)
            submit_col = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
            admin_match = submit_col.find_one({'username': match.group('username')})
            if admin_match and match.group('password') == admin_match['password']:
                await self.message.channel.send('Duplicate admin found.')
            elif admin_match:
                await self.message.channel.send('New password, updating...')
                ur: UpdateResult = submit_col.update_one({'username': match.group('username')}, {'$set': {'password': match.group('password')}})
                if ur.modified_count:
                    await self.message.channel.send('Password Update Complete')
                else:
                    await self.message.channel.send('Unable to update password.')
            else:
                ir: InsertOneResult = submit_col.insert_one({'username': match.group('username'), 'password': match.group('password')})
                if ir.inserted_id:
                    await self.message.channel.send('Registered submit-admin {}.'.format(match.group('username')))
                else:
                    await self.message.channel.send('Unable to register submit-admin {}.'.format(match.group('username')))
            await self.message.delete(delay=1)


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+setup\s+(?P<username>\w+)\s+(?P<password>.*)", message.content):
            return True
        return False
