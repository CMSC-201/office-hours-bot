import logging

from discord import Guild, Member, Role, User

import mongo
from roles import RoleAuthority, PermissionAuthority
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


class MemberAuthority:
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'

    __NAME_FIELDS = ["First-Name", "Last-Name"]
    __KEY_FIELD = "key"
    __DISCORD_ID_FIELD = "discord"
    __UID_FIELD = 'UMBC-Name-Id'
    __SECTION = 'Section'
    __LAB = 'Lab {}'

    BAD_AUTHENTICATION = 0
    AUTHENTICATED = 1
    DUPLICATE_ACCOUNT = 2

    def __init__(self, guild: Guild):
        self.guild = guild

    async def authenticate_member(self, member: Member, key: str) -> int:
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        ra: RoleAuthority = RoleAuthority(self.guild)
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        found_person = None
        found_role = None
        found_group = None
        print(member, member.id)

        for group, role in zip([students_group, ta_group, admin_group], [ra.student, ra.ta, ra.admin]):
            person = group.find_one({'key': key})
            if person:
                found_person = person
                found_role = role
                found_group = group
                break

        if found_person:
            if found_person.get(self.__DISCORD_ID_FIELD) and found_person.get(self.__DISCORD_ID_FIELD) != member.id:
                logger.error("Human tried to auth with a new account.  New ID: {}, Old ID: {}".format(
                    member.id,
                    found_person[self.__DISCORD_ID_FIELD]
                ))
                return self.DUPLICATE_ACCOUNT
            elif not found_person.get(self.__DISCORD_ID_FIELD):

                name = ' '.join([found_person[first_or_last] for first_or_last in self.__NAME_FIELDS])
                await member.edit(nick=name)
                await member.add_roles(found_role)
                await member.remove_roles(ra.un_authenticated)

                result = found_group.update_one({self.__UID_FIELD: found_person[self.__UID_FIELD]}, {'$set': {self.__DISCORD_ID_FIELD: member.id}})
                pa: PermissionAuthority = PermissionAuthority()
                # add lab authorization.
                if found_person[self.__SECTION].strip():
                    section_name = found_person[self.__SECTION].strip()
                    if self.__LAB.format(section_name) in ca.lab_sections:
                        if found_group == ta_group:
                            await ca.lab_sections[self.__LAB.format(section_name)].set_permissions(member, overwrite=pa.ta_overwrite)
                        elif found_group == students_group:
                            await ca.lab_sections[self.__LAB.format(section_name)].set_permissions(member, overwrite=pa.student_overwrite)

                # should be one, if non-zero it indicates that the update occurred.
                # result.matched_count, result.modified_count
                return result.modified_count > 0 and self.AUTHENTICATED
            else:
                return self.AUTHENTICATED

        return self.BAD_AUTHENTICATION

    async def deauthenticate_member(self, member: Member) -> bool:
        ra: RoleAuthority = RoleAuthority(self.guild)
        for role in member.roles:
            if not role.is_default():
                await member.remove_roles(role)
            await member.add_roles(ra.un_authenticated)
        return True
