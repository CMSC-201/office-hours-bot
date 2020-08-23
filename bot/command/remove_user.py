import logging

from discord import Message, Client, Member, User

import re
import command
import mongo
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority
from member import MemberAuthority


logger = logging.getLogger(__name__)


@command.command_class
class RemoveUser(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'
    __DISCORD_ID = 'discord'

    async def handle(self):
        ra: RoleAuthority = RoleAuthority(self.message.guild)
        ma: MemberAuthority = MemberAuthority(self.message.guild)
        if ra.admin:
            students_group = mongo.db[self.__STUDENTS_GROUP]
            ta_group = mongo.db[self.__TA_GROUP]
            admin_group = mongo.db[self.__ADMIN_GROUP]

            for group in [students_group, ta_group, admin_group]:
                match = re.match(r'!remove\s+user\s+(?P<user_identifier>\w+)', self.message.content)
                uid = match.group('user_identifier')
                umbc_id_list = [user for user in group.find({'UMBC-Name-Id': uid})]

                if umbc_id_list:
                    member_document = umbc_id_list[0]
                    print(member_document[self.__DISCORD_ID])
                    member = self.message.guild.get_member(member_document[self.__DISCORD_ID])
                    if member:
                        await self.message.channel.send('Deauthenticating User %s' % member.nick)
                        await ma.deauthenticate_user(member)
                    await self.message.channel.send('Removing User from Database...')
                    group.delete_one({self.__UID_FIELD: uid})
                    await self.message.channel.send('User removal complete.')

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!remove user"):
            return True

        return False
