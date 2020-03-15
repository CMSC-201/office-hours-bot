from discord import Permissions, Guild, Role, Member


class RoleAuthority:
    __ADMIN_NAME = "Admin"
    __STUDENT_NAME = "Student"
    __UNAUTHED_NAME = "Unauthed"
    __TA_NAME = "TA"

    def __init__(self, guild: Guild):
        self.admin = None
        self.student = None
        self.un_authenticated = None
        self.ta = None

        role: Role = None  # The things I do for type hints...
        for role in guild.roles:
            if role.name == self.__ADMIN_NAME:
                self.admin = role
            elif role.name == self.__STUDENT_NAME:
                self.student = role
            elif role.name == self.__UNAUTHED_NAME:
                self.un_authenticated = role
            elif role.name == self.__TA_NAME:
                self.ta = role

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
