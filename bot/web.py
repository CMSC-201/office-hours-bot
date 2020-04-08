from flask import Flask
from flask import render_template

from globals import get_globals
from queues import QueueAuthority

app = Flask(__name__)

@app.route('/')
def hello_world():

    queue = QueueAuthority.queue_for_web()
    for item in queue:
        item["member"] = item["member-id"]
    return render_template('index.html', queue=queue)