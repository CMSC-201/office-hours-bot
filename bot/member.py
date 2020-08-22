import logging

from discord import Guild, Member

import mongo
from roles import RoleAuthority

logger = logging.getLogger(__name__)


class MemberAuthority:
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'admin'
    __STUDENTS_GROUP = 'students'
    __AUTHENTICATION_FIELD = "authentication"

    __NAME_FIELD = "name"
    __KEY_FIELD = "key"
    __DISCORD_ID_FIELD = "discord"

    def __init__(self, guild: Guild):
        self.guild = guild

    async def authenticate_member(self, member: Member, key: str) -> bool:
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        found_student = students_group.find_one({'key': key})
        found_ta = ta_group.find_one({'key': key})
        found_admin = admin_group.find_one({'key': key})

        ra: RoleAuthority = RoleAuthority(self.guild)

        found_person = None
        found_role = None

        for person, role in [(found_student, ra.student),
                             (found_ta, ra.ta),
                             (found_admin, ra.admin)]:
            if person:
                found_person = person
                found_role = role

        if found_person:
            if found_person.get(self.__DISCORD_ID_FIELD) != member.id:
                logger.error("Human tried to auth with a new account.  New ID: {}, Old ID: {}".format(
                    member.id,
                    found_person[self.__DISCORD_ID_FIELD]
                ))
                return False

            name = found_person[self.__NAME_FIELD]
            await member.edit(nick=name)
            await member.add_roles(found_role)
            await member.remove_roles(ra.un_authenticated)
            found_person[self.__DISCORD_ID_FIELD] = member.id
            return True

        return False

