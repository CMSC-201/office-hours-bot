import logging

from discord import Guild, Member, Role, User

import mongo
from roles import RoleAuthority

logger = logging.getLogger(__name__)


class MemberAuthority:
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'

    __NAME_FIELDS = ["First-Name", "Last-Name"]
    __KEY_FIELD = "key"
    __DISCORD_ID_FIELD = "discord"
    __UID_FIELD = 'UMBC-Name-Id'

    def __init__(self, guild: Guild):
        self.guild = guild

    async def authenticate_member(self, member: Member, key: str) -> bool:
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        ra: RoleAuthority = RoleAuthority(self.guild)

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
                return False
            elif not found_person.get(self.__DISCORD_ID_FIELD):

                name = ' '.join([found_person[first_or_last] for first_or_last in self.__NAME_FIELDS])
                await member.edit(nick=name)
                await member.add_roles(found_role)
                await member.remove_roles(ra.un_authenticated)

                result = found_group.update_one({self.__UID_FIELD: found_person[self.__UID_FIELD]}, {'$set': {self.__DISCORD_ID_FIELD: member.id}})

                # should be one, if non-zero it indicates that the update occurred.
                # result.matched_count, result.modified_count
                return result.modified_count > 0
            else:
                return True

        return False

    async def deauthenticate_member(self, member: Member) -> bool:
        ra: RoleAuthority = RoleAuthority(self.guild)
        for role in member.roles:
            if not role.is_default():
                await member.remove_roles(role)
            await member.add_roles(ra.un_authenticated)
        return True
