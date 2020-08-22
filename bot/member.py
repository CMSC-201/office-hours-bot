import logging

from discord import Guild, Member

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

        for group, role in zip([students_group, ta_group, admin_group], [ra.student, ra.ta, ra.admin]):
            person = group.find_one({'key': key})
            if person:
                found_person = person
                found_role = role
                found_group = students_group

        if found_person:
            if found_person.get(self.__DISCORD_ID_FIELD) not in [member.id, '']:
                logger.error("Human tried to auth with a new account.  New ID: {}, Old ID: {}".format(
                    member.id,
                    found_person[self.__DISCORD_ID_FIELD]
                ))
                return False

            name = ' '.join([found_person[first_or_last] for first_or_last in self.__NAME_FIELDS])
            await member.edit(nick=name)
            await member.add_roles(found_role)
            await member.remove_roles(ra.un_authenticated)

            found_group.update_one({self.__UID_FIELD: found_person[self.__UID_FIELD]}, {'$set': {self.__DISCORD_ID_FIELD: member.id}})

            return True

        return False

