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
    except:
        print("ERROR when deleting message, but bot may proceed normally.")


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
    # Clear all message objects from room
    await room_chan.purge(limit=1000)
    # Take the role from teachers and students
    teacher, student = None, None
    while len(room["teachers"]) > 0:
        teacher = room["teachers"].pop()
        await msg.guild.get_member(teacher).remove_roles(room_role)
    while len(room["students"]) > 0:
        student = room["students"].pop()
        await msg.guild.get_member(student).remove_roles(room_role)
    # Mark room as vacant
    queue["open_rooms"].append(room)

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
        text = msg.author.mention + " Please provide " + \
                "your code in this format: `!auth (key)`"
        response = await msg.channel.send(text)
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
        text = msg.author.mention + " You have been " + \
                "authenticated! Please go to <#getting-started>"
        response = await msg.channel.send(text)
        await safe_delete(response, delay=15)
        author = msg.author.id
        role = msg.guild.get_role(uuids["StudentRole"])
        # Assign student and name
        await msg.guild.get_member(author).add_roles(role)
        await msg.guild.get_member(author).edit(nick=name)
    # Student does not exist, perhaps an incorrect code
    else:
        text = msg.author.mention + " You have not given a valid code, " + \
                "or the code has already been used.\n" + \
                "Please contact a professor or Min."
        response = await msg.channel.send(text)
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

    if not read_json('../offices.json')["is_open"]:
        text = msg.author.mention + " Office hours are currently closed!"
        response = await msg.channel.send(text)
        await safe_delete(response, delay=5)
        await safe_delete(msg)
        return msg.author.nick + " requested during closed hours."

    student = msg.author.id
    queue = read_json('../student_queue.json')
    # Student already made a request
    if student_waiting(queue, student):
        text = msg.author.mention + " You have already made a request!"
        response = await msg.channel.send(text)
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
    text = msg.author.mention + " Your request will be processed!"
    response = await msg.channel.send(text)
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

    if not office_queue["is_open"]:
        text = msg.author.mention + " Office hours was toggled off! Please issue the `!toggle` command!"
        response = await msg.channel.send(text)
        await safe_delete(response, delay=5)
        await safe_delete(msg)
        return msg.author.nick + " accepted during closed hours."

    if len(student_queue) < 1:
        text = msg.author.mention + " There are currently no students needing help!"
        response = await msg.channel.send(text)
        await safe_delete(response, delay=10)
        await safe_delete(msg)
        return msg.author.nick + " tried to help, but nobody was there."

    if len(office_queue["open_rooms"]) < 1:
        text = msg.author.mention + " There are currently no available office hour rooms!"
        response = await msg.channel.send(text)
        await safe_delete(response, delay=10)
        await safe_delete(msg)
        return msg.author.nick + " tried to help, but there was nowhere to go."

    # Get resources
    office = office_queue["open_rooms"][0]
    role = msg.guild.get_role(office["key"])
    # Move room to occupied
    office_queue["open_rooms"].remove(office)
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
    text = "<@" + str(t_id) + "> and <@" + str(s_id) + ">"
    await msg.guild.get_channel(office["room"]).send(text)
    text = "Here is your room! You may close this room with `!close`."
    await msg.guild.get_channel(office["room"]).send(text)
    # Remove command from channel immediately
    await safe_delete(msg)
    # Save state
    write_json('../student_queue.json', student_queue)
    write_json('../offices.json', office_queue)
    # Return log message
    return teacher.name + " has accepted " + \
        student.name + "'s request and are in " + \
        msg.guild.get_channel(office["room"]).name


async def toggle_office(msg, args, uuids):
    # Wrong Channel
    if msg.channel.id != uuids["RequestsRoom"]:
        await safe_delete(msg)
        return "Executed in wrong channel."

    office_queue = read_json('../offices.json')
    return_msg = ""
    # Delete the old indicator message if existing
    if(office_queue["open_indicator"] > 0):
        indicator_channel = msg.guild.get_channel(uuids["WaitingRoom"])
        old_msg = await indicator_channel.fetch_message(office_queue["open_indicator"])
        await safe_delete(old_msg)
    # Toggle the office hours, send the messages
    if(office_queue["is_open"]):
        message = "Office hours are now ""CLOSED**!"
        waiting = await msg.guild.get_channel(uuids["WaitingRoom"]).send(message)
        request = await msg.guild.get_channel(uuids["RequestsRoom"]).send(message)
        office_queue["open_indicator"] = waiting.id
        office_queue["is_open"] = False
        return_msg = "Successfully closed office hours."
    else:
        message = "Office hours are now **OPEN**!"
        waiting = await msg.guild.get_channel(uuids["WaitingRoom"]).send(message)
        request = await msg.guild.get_channel(uuids["RequestsRoom"]).send(message)
        office_queue["open_indicator"] = waiting.id
        office_queue["is_open"] = True
        return_msg = "Successfully opened office hours."

    # Remove all queues. This works in both cases:
    #   Opening: Clear all old requests before opening
    #   Closing: Clear all current requests because of closing
    student_queue = read_json('../student_queue.json')
    while len(student_queue) > 0:
        s_info = student_queue.pop()
        # Delete the request
        requestmsg = await msg.channel.fetch_message(s_info["requestID"])
        await safe_delete(requestmsg)
        
    # Save state
    write_json('../student_queue.json', student_queue)
    write_json('../offices.json', office_queue)
    # Return log message
    return return_msg


def read_json(path):
    with open(path, "r") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w+") as f:
        f.write(json.dumps(data))


commands = {"close":office_close,
            "auth":student_authenticate,
            "request":request_create,
            "accept":request_accept,
            "toggle":toggle_office}


async def execute_command(msg, args, uuids):
    cmd = args[0]
    if cmd in commands:
        return await commands[cmd](msg, args, uuids)
    command_only = [uuids["RequestsRoom"],uuids["WaitingRoom"]]
    if msg.channel.id in command_only and not msg.author.bot:
        await safe_delete(msg)
        return "Not a command, in a command only channel."
    await safe_delete(msg)
    return "Command did not exist."