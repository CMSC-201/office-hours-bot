import logging
import datetime as dt

from discord import Message, Client, Member, User, Embed, Colour

import command
import mongo
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class RecheckRoles(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'TA'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'
    __DISCORD_ID = 'discord'
    __ROLE = 'Role'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'

    permissions = {'student': False, 'ta': False, 'admin': True}

    async def add_member_to_group(self, role_authority: RoleAuthority, discord_id, discord_group_name, group_name):
        """
            :param role_authority:
            :param member: the member to check
            :param group_name: the discord name for the group
            :param group_string: the internal name of the group
            :return: 1 if done, 0 if not
        """
        member: Member = await self.guild.fetch_member(discord_id)
        if not any(role.name == discord_group_name for role in member.roles):
            await role_authority.add_role(member, group_name)
            await self.message.channel.send(f'{discord_group_name} was not in {member.display_name}\'s list of roles, added.')
            return 1
        return 0


    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        role_authority: RoleAuthority = RoleAuthority(self.guild)

        admin_role = role_authority.get_admin_role()
        ta_role = role_authority.get_ta_role()
        student_role = role_authority.get_student_role()
        unauthenticated_role = role_authority.get_unauthenticated_role()

        color = Colour(0).dark_gold()
        for the_role in [admin_role, ta_role, student_role, unauthenticated_role]:
            message_text = f"{the_role.name}\n\tid = {the_role.id}\n\tguild = {the_role.guild}"
            embedded_message = Embed(title=f"{the_role.name}", description=message_text, timestamp=dt.datetime.now() + dt.timedelta(hours=4), colour=color)
            await self.message.channel.send(embed=embedded_message)


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!display roles"):
            return True

        return False
