from typing import Optional

from discord import Permissions, Guild, Role, Member

# TODO: store the role ids in mongo so we can rename them
class RoleAuthority:
    __ADMIN_NAME = "Admin"
    __STUDENT_NAME = "Student"
    __UNAUTHED_NAME = "Unauthed"
    __TA_NAME = "TA"
    __EVERYONE_NAME = "@everyone"
    __LAB_CHANNEL = 'lab'

    def __init__(self, guild: Guild):
        self.admin: Optional[Role] = None
        self.student: Optional[Role] = None
        self.un_authenticated: Optional[Role] = None
        self.ta: Optional[Role] = None
        self.everyone: Optional[Role] = None

        self.role_map = {}

        for role in guild.roles:
            self.role_map[role.name] = role
            if role.name == self.__ADMIN_NAME:
                self.admin = role
            elif role.name == self.__STUDENT_NAME:
                self.student = role
            elif role.name == self.__UNAUTHED_NAME:
                self.un_authenticated = role
            elif role.name == self.__TA_NAME:
                self.ta = role
            elif role.name == self.__EVERYONE_NAME:
                self.everyone = role
            elif self.__LAB_CHANNEL in role.name:
                pass

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

    def is_admin(self, member: Member) -> bool:
        return self.admin in member.roles

    def ta_or_higher(self, member: Member) -> bool:
        """
        True if the member is a TA or higher privilege, false otherwise
        :param member:
        :return:
        """
        return self.admin in member.roles or self.ta in member.roles


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
