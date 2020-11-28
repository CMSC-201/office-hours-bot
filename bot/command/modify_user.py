import logging

from discord import Message, Client, Member, User
from discord.errors import NotFound

import re
import command
import mongo
from roles import RoleAuthority
from member import MemberAuthority
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


@command.command_class
class ModifyUser(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'
    __DISCORD_ID = 'discord'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.message.guild)
        ma: MemberAuthority = MemberAuthority(self.message.guild)
        ca: ChannelAuthority = ChannelAuthority(self.message.guild)

        if ra.is_admin(self.message.author) and ca.is_maintenance_channel(self.message.channel):
            students_group = mongo.db[self.__STUDENTS_GROUP]
            ta_group = mongo.db[self.__TA_GROUP]
            admin_group = mongo.db[self.__ADMIN_GROUP]
            found = False

            match = re.match(r'!modify\s+user\s+(?P<user_identifier>\w+)\s+(?P<attribute>\S+)\s+(?P<new_value>\S+)(\s+(?P<force>--force))?', self.message.content)
            if match:
                uid = match.group('user_identifier')
                field_to_modify = match.group('attribute')
                new_value = match.group('new_value')

                for group in [students_group, ta_group, admin_group]:
                    found_user = group.find_one({self.__UID_FIELD: uid})
                    if found_user:
                        found = True
                        if field_to_modify in found_user:
                            if self.__UID_FIELD != field_to_modify and field_to_modify != '_id':
                                # get type to enforce the type of the field
                                t = type(found_user[field_to_modify])
                                try:
                                    new_value_cast = t(new_value)
                                    group.update_one({self.__UID_FIELD: found_user[self.__UID_FIELD]}, {'$set': {field_to_modify: new_value_cast}})
                                    await self.message.channel.send('Updated user {} attribute {} to {}'.format(uid, field_to_modify, new_value))
                                except ValueError:
                                    await self.message.channel.send('Cannot cast {} to the type {}'.format(new_value, t.__name__))
                            else:
                                await self.message.channel.send('Do not modify the UMBC-Name-Id field or _id field, that would probably be bad.')
                        else:
                            await self.message.channel.send('No attribute = {}'.format(field_to_modify))
                if not found:
                    await self.message.channel.send('Unable to find user with uid {}'.format(uid))
            else:
                await self.message.channel.send('Bad format of the command, should be:\n\t!modify user uid attribute new_value --force(optional)')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!modify user"):
            return True
        return False
