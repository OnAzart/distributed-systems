import json
import sys
from time import sleep
from random import randint
import logging

from flask import Flask, request, render_template

app = Flask(__name__, template_folder='src')
logs_filename = 'secondary.log'
logging.basicConfig(filename=logs_filename, filemode='w', level=logging.INFO,
                    format='%(asctime)s :: %(levelname)-8s :: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

reserve_queue = []

# # Limit access (only master and host)
# from flask import abort, request
# @app.before_request
# def limit_remote_addr():
#     print(request.remote_addr)
#     if request.remote_addr not in ('172.30.0.1', '172.30.0.2'):
#         abort(403)  # Forbidden


@app.route('/get_info', methods=["POST"])
def receive_message():
    logging.info(f'start receiving message')

    # making delay
    delay_time = 1 + randint(2, 4)
    logging.info(f"<<<<{delay_time=}")
    sleep(delay_time)

    message_to_append = json.loads(request.data)
    reserve_queue.append(message_to_append)

    logging.info('Message has been received to the node.')
    return "good"


@app.route('/', methods=["GET"])
def welcome():
    if request.args.get('action', None) == 'List':
        return render_template('secondary.html', list_messages=reserve_queue)
    return render_template('secondary.html')


@app.route('/logs', methods=["GET"])
async def logs_out():
    with open(logs_filename, 'r') as log_file:
        logs_lines = log_file.readlines()
        return render_template('logs.html', logs_lines=logs_lines)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=80)
