from typing import Optional

from discord import Permissions, Guild, Role, Member, PermissionOverwrite, User
import mongo


class RoleAuthority:
    __ADMIN_NAME = "Admin"
    __STUDENT_NAME = "Student"
    __UNAUTHED_NAME = "Unauthed"
    __TA_NAME = "TA"
    __EVERYONE_NAME = "@everyone"
    __ROLE_LIST = [__ADMIN_NAME, __STUDENT_NAME, __UNAUTHED_NAME, __TA_NAME, __EVERYONE_NAME]
    __LAB_CHANNEL = 'lab'

    __ROLE_COLLECTION = 'role-collection'

    def __init__(self, guild: Guild):
        self.guild = guild

        self.role_db = mongo.db[self.__ROLE_COLLECTION]

        self.role_map = {}

        for role_name in self.__ROLE_LIST:
            role_data = self.role_db.find_one({'role-name': role_name})
            if role_data:
                self.role_map[role_name] = guild.get_role(role_data['role-id'])
            else:
                for role in guild.roles:
                    if role.name == role_name:
                        self.role_map[role.name] = role
                        self.role_db.insert_one({'role-name': role_name,
                                                 'role-id': role.id})
                        break

    async def add_role(self, member: Member, role_name: str):
        """
        :param member: a discord.Member object of the server
        :param role_name: a string which will be matched to the role name, must be exact
        :return: success of adding roles.
        """
        if role_name in self.role_map:
            await member.add_roles(self.role_map[role_name])

        return self.role_map[role_name] in member.roles

    async def remove_role(self, member: Member, role_name: str):
        if role_name in self.role_map:
            await member.remove_roles(self.role_map[role_name])

        return self.role_map[role_name] in member.roles

    def is_student(self, member: Member) -> bool:
        return self.role_map[self.__STUDENT_NAME] in member.roles

    def is_ta(self, member: Member) -> bool:
        return self.role_map[self.__TA_NAME] in member.roles

    def is_admin(self, member: Member) -> bool:
        return self.role_map[self.__ADMIN_NAME] in member.roles

    def get_ta_role(self) -> Role:
        return self.role_map[self.__TA_NAME]

    def get_student_role(self) -> Role:
        return self.role_map[self.__STUDENT_NAME]

    def get_admin_role(self) -> Role:
        return self.role_map[self.__ADMIN_NAME]

    def get_unauthenticated_role(self) -> Role:
        return self.role_map[self.__UNAUTHED_NAME]

    def get_everyone_role(self) -> Role:
        return self.role_map[self.__EVERYONE_NAME]

    def ta_or_higher(self, member: Member) -> bool:
        """
        True if the member is a TA or higher privilege, false otherwise
        :param member: a Member object
        :return:
        """
        return self.role_map[self.__ADMIN_NAME] in member.roles or self.role_map[self.__TA_NAME] in member.roles

    async def has_permission(self, author: Member, permission_object):
        """
            has_permission should determine if the caller of the command has permission to execute it.

            If the 'all': True permission is set, then anyone can call this regardless of whether they are authenticated.

        :param author: the user who messaged the bot.
        :param permission_object: a dictionary with the roles and booleans as values.
        :return: boolean, True if permission is granted, False if denied
        """
        permission = False

        if 'all' in permission_object and permission_object['all']:
            return True

        # in the case of a DM, instead of being given a Member, the author is in fact a User (who doesn't have roles since they aren't
        #       associated with a guild at the time.  fetch the member by their id, and determine if they have permission to execute
        #       the command within the guild
        if isinstance(author, User):
            author = await self.guild.fetch_member(author.id)

        for role, method in zip(['student', 'ta', 'admin'], [self.is_student, self.is_ta, self.is_admin]):
            if role in permission_object and permission_object[role]:
                permission = permission or method(author)

        return permission


#TODO: remove permission authorities, use only the role authority, have it manage permissions as well since permissions are linked to roles.
class PermissionAuthority:
    def __init__(self):
        # role permissions
        self.student_permissions: Permissions = Permissions.none()
        self.student_permissions.update(add_reactions=True,
                                        stream=True,
                                        read_message_history=True,
                                        read_messages=True,
                                        send_messages=True,
                                        connect=True,
                                        speak=True,
                                        use_voice_activation=True)
        self.admin_permissions: Permissions = Permissions.all()
        self.un_authed_perms: Permissions = Permissions.none()
        self.un_authed_perms.update(read_message_history=True,
                                    read_messages=True,
                                    send_messages=True)
        self.ta_permissions: Permissions = Permissions.all()
        self.ta_permissions.update(administrator=False,
                                   admin_permissions=False,
                                   manage_channels=False,
                                   manage_guild=False,
                                   manage_roles=False,
                                   manage_permissions=False,
                                   manage_webhooks=False, )

        self.ta_overwrite = PermissionOverwrite(administrator=True,
                                                manage_channels=True,
                                                manage_guild=False,
                                                manage_roles=False,
                                                manage_permissions=False,
                                                manage_webhooks=False,
                                                add_reactions=True,
                                                stream=True,
                                                read_message_history=True,
                                                read_messages=True,
                                                send_messages=True,
                                                connect=True,
                                                speak=True,
                                                use_voice_activation=True)
        self.student_overwrite = PermissionOverwrite(add_reactions=True,
                                                     stream=True,
                                                     read_message_history=True,
                                                     read_messages=True,
                                                     send_messages=True,
                                                     connect=True,
                                                     speak=True,
                                                     use_voice_activation=True)

        self.forbid_overwrite = PermissionOverwrite(
            read_messages=False,
            send_messages=False,
            connect=False,
        )
