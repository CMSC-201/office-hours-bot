import logging

from pymongo.results import DeleteResult, UpdateResult

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
class RemoveUser(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'
    __DISCORD_ID = 'discord'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        ma: MemberAuthority = MemberAuthority(self.message.guild)

        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        for group in [students_group, ta_group, admin_group]:
            match = re.match(r'!remove\s+user\s+(?P<user_identifier>\w+)(\s+(?P<reset>--reset))?', self.message.content)
            uid = match.group('user_identifier')
            umbc_id_list = [user for user in group.find({'UMBC-Name-Id': uid})]

            if umbc_id_list:
                member_document = umbc_id_list[0]
                member = await self.message.guild.fetch_member(member_document[self.__DISCORD_ID])

                if member:
                    await self.message.channel.send('Deauthenticating User %s' % member.nick)
                    await ma.deauthenticate_member(member)

                if match.group('reset'):
                    await self.message.channel.send('Resetting User Database Entry...')
                    result: UpdateResult = group.update_one({self.__UID_FIELD: uid}, {'$set': {self.__DISCORD_ID: ''}})
                    if result.modified_count:
                        await self.message.channel.send('User deauthenticated and discord id reset.')
                    else:
                        await self.message.channel.send('User deauthenticated but database entry not found/modified.')
                else:
                    await self.message.channel.send('Removing User from Database...')
                    result: DeleteResult = group.delete_one({self.__UID_FIELD: uid})
                    if result.deleted_count:
                        await self.message.channel.send('User removal complete.')
                    else:
                        await self.message.channel.send('User deauthenticated but not removed from database.')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!remove user"):
            return True

        return False
