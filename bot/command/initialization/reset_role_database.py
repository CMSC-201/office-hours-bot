import logging

from discord import Message, Client, Colour, Embed

import re
import command
import mongo


logger = logging.getLogger(__name__)


@command.command_class
class ResetRoleDatabase(command.Command):
    __ADMIN_NAME = "Admin"
    __STUDENT_NAME = "Student"
    __UNAUTHED_NAME = "Unauthed"
    __TA_NAME = "TA"
    __EVERYONE_NAME = "@everyone"
    __ROLE_LIST = [__ADMIN_NAME, __STUDENT_NAME, __UNAUTHED_NAME, __TA_NAME, __EVERYONE_NAME]
    __ROLE_COLLECTION = 'role-collection'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.require_maintenance
    async def handle(self):
        role_db = mongo.db[self.__ROLE_COLLECTION]
        # empty this collection
        role_db.delete_many({})
        # rebuild the collection
        for role_name in self.__ROLE_LIST:
            await self.message.channel.send(f'Searching for {role_name} role.')
            for role in self.guild.roles:
                if role.name == role_name:
                    await self.message.channel.send(f'Found Matching role: {role.name}.')
                    role_db.insert_one({'role-name': role_name, 'role-id': role.id})
                    await self.message.channel.send(f'Inserted {role.name} into database with {role.id}.')
                    break


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!reset role database"):
            return True

        return False

