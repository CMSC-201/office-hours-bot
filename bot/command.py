import json
import discord
from datetime import datetime as dt

def parse_arguments(msg, prefix):
    args = []
    if msg.content.startswith(prefix):
        params = msg.content[:1].split()
        for param in params:
            args.append(param)
    return args


def student_waiting(queue, id):
    for i in range(len(queue)):
        if queue[i].userID == id:
            return True
    return False
    

def office_close(msg, args, uuids):
    room, room_name = None, None
    queue = read_json('../offices.json')
    for office in queue["occupied"]:
        if office["room"] == msg.channel.id:
            room = office
            queue["occupied"].remove(room)
    # Begin closing the room if occupied
    if room:
        room_chan = msg.guild.get_channel(room)
        room_role = msg.guild.get_role(room)
        room_name = room_chan.name
        # Take the role from teachers and students
        teacher, student = None, None
        while len(room["teachers"]) > 0:
            teacher = room["teachers"].pop()
            msg.guild.get_member(teacher).remove_roles(room_role)
        while len(room["students"]) > 0:
            student = room["students"].pop()
            msg.guild.get_member(student).remove_roles(room_role)
        # Clear all message objects from room
        room_chan.purge(limit=1000)
        # Mark room as vacant
        queue["openRooms"].append(room)

    # Remove command from channel immediately
    msg.delete()
    # Save state
    write_json('../offices.json', queue)
    # Return log message
    return room_name + " has been closed!"


def student_authenticate(msg, args, uuids):
    # Wrong Channel
    if msg.channel.id != uuids["AuthRoom"]:
        msg.delete()
        return
    # No key in command
    if len(args) < 2:
        response = msg.channel.send("Please provide your code in this format:",
                                    "`!auth (key)`")
        response.delete(delay=15)
        msg.delete()
        return

    students = read_json('../studenthash.json')
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
        response = msg.channel.send("You have been authenticated! Please go to <#>")
        response.delete(delay=15)
        author = msg.author.id
        role = msg.guild.get_role(uuids["StudentRole"])
        # Assign student and name
        msg.guild.get_member(author).add_roles(role)
        msg.guild.get_member(author).edit(nick=name)
    # Student does not exist, perhaps an incorrect code
    else:
        response = msg.channel.send("You have not given a valid code, or the",
                                    "code has already been used.\n",
                                    "Please contact a professor or Min.")
        response.delete(delay=15)
        return "Authentication for " + msg.author.name + " has failed."

    # Remove command from channel immediately
    msg.delete()
    # Save state
    write_json('../studenthash.json', students)
    # Return log message
    return name + " has been authenticated!"


def request_create(msg, args, uuids):
    # Wrong Channel
    if msg.channel.id != uuids["WaitingRoom"]:
        msg.delete()
        return

    student = msg.author.id
    queue = read_json('../student_queue.json')
    # Student already made a request
    if student_waiting(queue, student):
        response = msg.channel.send("You have already made a request!")
        response.delete(delay=5)
        msg.delete()
        return msg.author.nick + " had already created a request."

    # Description minus the command
    description = msg.content[len(args[0])+1:]
    # Build embedded message
    color = discord.Colour().blue()
    embeddedMsg = discord.Embed(description = description,
                                timestamp = dt.now(),
                                colour = color)
    embeddedMsg.set_author(msg.author.name)
    embeddedMsg.add_field(name = "Accept request by typing",
                          value = "!accept")
    # Send embedded message
    request = msg.guild.get_channel(uuids["RequestsRoom"]).send(embed=embeddedMsg)
    
    # Save new student to queue
    entry = {"userID": student,
             "requestID": request.id}
    queue.append(entry)

    # Command finished
    response = msg.channel.send("Your request will be processed!")
    response.delete(delay=15)

    # Remove command from channel immediately
    msg.delete()
    # Save state
    write_json('../student_queue.json', queue)
    # Return log message
    return msg.author.name + " has been added to the queue."


def request_accept(msg, args, uuids):
    # Wrong Channel
    if msg.channel.id != uuids["RequestsRoom"]:
        msg.delete()
        return
    
    student_queue = read_json('../student_queue.json')
    office_queue = read_json('../offices.json')
    if len(student_queue) < 1:
        response = msg.channel.send("There are currently no students needing help!")
        response.delete(delay=10)
        msg.delete()
        return msg.author.nick + " tried to help, but nobody was there."

    if len(office_queue["openRooms"]) < 1:
        response = msg.channel.send("There are currently no available office hour rooms!")
        response.delete(delay=10)
        msg.delete()
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
    student_queue.remove(s_id)
    # Get member objects
    teacher = msg.guild.get_member(t_id)
    student = msg.guild.get_member(s_id)
    # Delete the request
    msg.channel.fetch_message(s_info["requestID"]).delete()
    # Add occupants
    office["teachers"].append(t_id)
    office["students"].append(s_id)
    # Give teacher and student room role
    teacher.add_roles(role)
    student.add_roles(role)
    message = "<@" + t_id + "> and <@" + s_id + ">"
    msg.guild.get_channel(office["room"]).send(message)
    message = "Here is your room! You may close this room with `!close`."
    msg.guild.get_channel(office["room"]).send(message)
    # Remove command from channel immediately
    msg.delete()
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


def execute_command(msg, args, uuids):
    cmd = args[0]
    if cmd in commands:
        return cmd(msg, args, uuids)
    return "Command did not exist."