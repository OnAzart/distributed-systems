import json
from time import sleep
from random import randint

from flask import Flask, request, render_template
import requests

app = Flask(__name__, template_folder='src')
reserve_queue = []


@app.route('/get_info', methods=["POST"])
def receive_message():
    print('tryyying to receive')
    message_to_append = json.loads(request.data)
    reserve_queue.append(message_to_append)
    sleep(1 + randint(0, 3))
    print('Message has been received to the node.')
    return "good"


# LIST
@app.route('/', methods=["POST"])
def list_messages():
    print(request.form)
    return render_template('secondary.html', list_messages=reserve_queue)


@app.route('/', methods=["GET"])
def welcome():
    if request.args.get('action', None) == 'List':
        return render_template('secondary.html', list_messages=reserve_queue)
    return render_template('secondary.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=80)
