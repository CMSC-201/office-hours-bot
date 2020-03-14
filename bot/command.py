import json
import discord
from datetime import datetime as dt

def parse_arguments(msg, prefix):
    args = []
    if msg.content.startswith(prefix):
        params = msg.content[1:].split()
        for param in params:
            args.append(param)
    return args


def student_waiting(queue, id):
    for i in range(len(queue)):
        if queue[i]["userID"] == id:
            return True
    return False


async def safe_delete(msg, delay=None):
    try:
        await msg.delete(delay=delay)
    except RuntimeError as e:
        print(e, "\nBot may proceed normally.")

async def office_close(msg, args, uuids):
    # Room is room object which contains room id, role (key) id
    # and list of teachers and students
    room, room_name = None, None
    queue = read_json('../offices.json')
    for office in queue["occupied"]:
        if office["room"] == msg.channel.id:
            room = office
            queue["occupied"].remove(room)
    # Not a valid room
    if not room:
        await safe_delete(msg)
        return "Cannot close non-office room!"
    # Begin closing room
    room_chan = msg.guild.get_channel(room["room"])
    room_role = msg.guild.get_role(room["key"])
    room_name = room_chan.name
    # Take the role from teachers and students
    teacher, student = None, None
    while len(room["teachers"]) > 0:
        teacher = room["teachers"].pop()
        await msg.guild.get_member(teacher).remove_roles(room_role)
    while len(room["students"]) > 0:
        student = room["students"].pop()
        await msg.guild.get_member(student).remove_roles(room_role)
    # Clear all message objects from room
    await room_chan.purge(limit=1000)
    # Mark room as vacant
    queue["openRooms"].append(room)

    # Save state
    write_json('../offices.json', queue)
    # Return log message
    return room_name + " has been closed!"


async def student_authenticate(msg, args, uuids):
    # Wrong Channel
    if msg.channel.id != uuids["AuthRoom"]:
        await safe_delete(msg)
        return "Executed in wrong channel."
    # No key in command
    if len(args) < 2:
        response = await msg.channel.send("Please provide your code in this format: " + \
                                          "`!auth (key)`")
        await safe_delete(response, delay=15)
        await safe_delete(msg)
        return "Did not have an argument for key."

    students = read_json('../student_hash.json')
    name = None
    key = args[1]
    # Find student's hash key
    for student in students["unauthed"]:
        if key == student["id"]:
            name = student["name"]
            students["authed"].append(student)
            students["unauthed"].remove(student)
    # Student exists, begin authentication process
    if name:
        response = await msg.channel.send("You have been authenticated! Please go to <#>")
        await safe_delete(response, delay=15)
        author = msg.author.id
        role = msg.guild.get_role(uuids["StudentRole"])
        # Assign student and name
        await msg.guild.get_member(author).add_roles(role)
        await msg.guild.get_member(author).edit(nick=name)
    # Student does not exist, perhaps an incorrect code
    else:
        response = await msg.channel.send("You have not given a valid code, or the " + \
                                    "code has already been used.\n" + \
                                    "Please contact a professor or Min.")
        await safe_delete(response, delay=15)
        await safe_delete(msg)
        return "Authentication for " + msg.author.name + " has failed."

    # Remove command from channel immediately
    await safe_delete(msg)
    # Save state
    write_json('../student_hash.json', students)
    # Return log message
    return name + " has been authenticated!"


async def request_create(msg, args, uuids):
    # Wrong Channel
    if msg.channel.id != uuids["WaitingRoom"]:
        await safe_delete(msg)
        return "Executed in wrong channel."

    student = msg.author.id
    queue = read_json('../student_queue.json')
    # Student already made a request
    if student_waiting(queue, student):
        response = await msg.channel.send("You have already made a request!")
        await safe_delete(response, delay=5)
        await safe_delete(msg)
        return msg.author.nick + " had already created a request."

    # Description minus the command
    description = msg.content[len(args[0])+1:]
    # Build embedded message
    color = discord.Colour(0).blue()
    embeddedMsg = discord.Embed(description = description,
                                timestamp = dt.now(),
                                colour = color)
    embeddedMsg.set_author(name = msg.author.name)
    embeddedMsg.add_field(name = "Accept request by typing",
                          value = "!accept")
    # Send embedded message
    request = await msg.guild.get_channel(uuids["RequestsRoom"]).send(embed=embeddedMsg)
    
    # Save new student to queue
    entry = {"userID": student,
             "requestID": request.id}
    queue.append(entry)

    # Command finished
    response = await msg.channel.send("Your request will be processed!")
    await safe_delete(response, delay=15)

    # Remove command from channel immediately
    await safe_delete(msg)
    # Save state
    write_json('../student_queue.json', queue)
    # Return log message
    return msg.author.name + " has been added to the queue."


async def request_accept(msg, args, uuids):
    # Wrong Channel
    if msg.channel.id != uuids["RequestsRoom"]:
        await safe_delete(msg)
        return "Executed in wrong channel."
    
    student_queue = read_json('../student_queue.json')
    office_queue = read_json('../offices.json')
    if len(student_queue) < 1:
        response = await msg.channel.send("There are currently no students needing help!")
        await safe_delete(response, delay=10)
        await safe_delete(msg)
        return msg.author.nick + " tried to help, but nobody was there."

    if len(office_queue["openRooms"]) < 1:
        response = await msg.channel.send("There are currently no available office hour rooms!")
        await safe_delete(response, delay=10)
        await safe_delete(msg)
        return msg.author.nick + " tried to help, but there was nowhere to go."

    # Get resources
    office = office_queue["openRooms"][0]
    role = msg.guild.get_role(office["key"])
    # Move room to occupied
    office_queue["openRooms"].remove(office)
    office_queue["occupied"].append(office)
    # Get member ids
    t_id = msg.author.id
    s_info = student_queue[0]
    s_id = s_info["userID"]
    # Remove student from queue
    student_queue.remove(s_info)
    # Get member objects
    teacher = msg.guild.get_member(t_id)
    student = msg.guild.get_member(s_id)
    # Delete the request
    requestmsg = await msg.channel.fetch_message(s_info["requestID"])
    await safe_delete(requestmsg)
    # Add occupants
    office["teachers"].append(t_id)
    office["students"].append(s_id)
    # Give teacher and student room role
    await teacher.add_roles(role)
    await student.add_roles(role)
    message = "<@" + str(t_id) + "> and <@" + str(s_id) + ">"
    await msg.guild.get_channel(office["room"]).send(message)
    message = "Here is your room! You may close this room with `!close`."
    await msg.guild.get_channel(office["room"]).send(message)
    # Remove command from channel immediately
    await safe_delete(msg)
    # Save state
    write_json('../student_queue.json', student_queue)
    write_json('../offices.json', office_queue)
    # Return log message
    return teacher.name + " has accepted " + \
        student.name + "'s request and are in " + \
        msg.guild.get_channel(office["room"]).name


def read_json(path):
    with open(path, "r") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w+") as f:
        f.write(json.dumps(data))


commands = {"close":office_close,
            "auth":student_authenticate,
            "request":request_create,
            "accept":request_accept}


async def execute_command(msg, args, uuids):
    cmd = args[0]
    if cmd in commands:
        return await commands[cmd](msg, args, uuids)
    await safe_delete(msg)
    return "Command did not exist."