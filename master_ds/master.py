import json
import sys
import threading
import logging

from flask import Flask, request, render_template
import requests

app = Flask(__name__, template_folder='src')
logging.basicConfig(filename='master.log', filemode='w', level=logging.INFO,
                    format='%(asctime)s :: %(levelname)-8s :: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

queue = []


@app.route('/', methods=["GET", "POST"])
def handle_forms():
    if request.method == 'POST':
        message_to_append = (request.form['messageToAppend'])
        queue.append(message_to_append)
        logging.info(f'"{message_to_append}" is saved on master.')
        response_text = send_to_nodes(message_to_append)
        return render_template('main.html', append_info=response_text)
    elif request.method == 'GET' and request.args.get('action', None) == 'List':
        return render_template('main.html', list_messages=queue)
    else:
        return render_template('main.html', list_messages=queue)


def send_to_nodes(message_to_send):
    encoded_message_to_send = json.dumps(message_to_send)

    def sending_to_node(node, responses_dict):
        logging.info(f"Sending message to {node} secondary node.")
        try:
            resp = requests.post(f'http://{node}/get_info', data=encoded_message_to_send)
        except ConnectionError or TimeoutError:
            logging.warning(f"Connection error for {node} node.")
            return 1
        logging.info(f"Node ({node}) respond with {resp.status_code} status code.")
        responses_dict[node] = resp.status_code

    nodes_ip = ['172.30.0.3', '172.30.0.4']
    threads = []
    responses = {}
    for node_ip in nodes_ip:
        thr = threading.Thread(target=sending_to_node, args=(node_ip, responses))
        thr.start()
        threads.append(thr)
    for thr in threads:
        thr.join(timeout=7)
        print(f"{thr.name} joined")

    print("Responses: ", responses)
    if not responses:
        # TODO: Retry for all nodes
        return_message = f"Message '{message_to_send}' is NOT replicated at all."
        logging.warning(return_message)
        return return_message
    elif not list(filter(lambda x: x != 200, responses.values())):
        return_message = f"Message '{message_to_send}' is replicated to all nodes."
        logging.info(return_message)
        return return_message
    else:
        # TODO: Retry for certain node and change log
        return_message = "Message is NOT replicated to certain nodes."
        logging.warning(return_message)
        return return_message


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=80)
