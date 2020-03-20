import logging

from discord import Guild, Member

import mongo
from roles import RoleAuthority

logger = logging.getLogger(__name__)


class MemberAuthority:
    __MEMBER_COLLECTION = "members"
    __AUTHENTICATION_FIELD = "authentication"

    __NAME_FIELD = "name"
    __KEY_FIELD = "key"
    __DISCORD_ID_FIELD = "discord"

    def __init__(self, guild: Guild):
        self.guild = guild

    async def authenticate_member(self, member: Member, key: str) -> bool:
        collection = mongo.db[self.__MEMBER_COLLECTION]
        document = collection.find_one()

        if not document:
            document = {
                self.__AUTHENTICATION_FIELD: []
            }
            collection.insert(document)
        found = False
        for auth_data in document[self.__AUTHENTICATION_FIELD]:
            if auth_data[self.__KEY_FIELD] == key:
                name = auth_data[self.__NAME_FIELD]
                ra: RoleAuthority = RoleAuthority(self.guild)
                # try:
                await member.edit(nick=name)
                await member.add_roles(ra.student)
                await member.remove_roles(ra.un_authenticated)
                # except:
                #     logger.error("Error authenticating user {}".format(member.id))

                auth_data[self.__DISCORD_ID_FIELD] = member.id

                found = True
                break

        collection.replace_one({"_id": document["_id"]}, document)
        return found
