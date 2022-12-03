import json
import logging
import sys
import threading

import requests

logs_filename = 'master.log'
logging.basicConfig(filename=logs_filename, filemode='a', level=logging.INFO,
                    format='%(asctime)s :: %(levelname)-8s :: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

nodes_ip = ['172.30.0.3', '172.30.0.4']


def retry_handle(responses):
    logging.info("Retrying in Future")


def sending_to_node(node, message, barrier, responses_dict):
    encoded_message_to_send = json.dumps(message)
    logging.info(f"Sending message to {node} secondary node.")
    try:
        # We can use docker compose --scale to scale secondary and use their dns name to communicate
        resp = requests.post(f'http://{node}/get_info', data=encoded_message_to_send)
        logging.info(f"Node ({node}) respond with {resp.status_code} status code.")
        responses_dict[node] = resp.status_code
        barrier.wait()
    except ConnectionError or TimeoutError:
        logging.warning(f"Connection (timeout) error for {node} node.")
        return 1


def send_to_nodes(message_to_send, write_concern):
    if not write_concern or write_concern > len(nodes_ip) + 1:
        write_concern = len(nodes_ip) + 1
    print(f'{write_concern=}')

    responses_from_nodes = {}
    timeout_for_sending = 5
    barrier = threading.Barrier(parties=write_concern, timeout=timeout_for_sending)
    for node_ip in nodes_ip:
        thr = threading.Thread(target=sending_to_node, args=(node_ip, message_to_send, barrier, responses_from_nodes))
        thr.start()
    try:
        barrier.wait()
    except threading.BrokenBarrierError:
        print('<<<<<< error. BarrierError happened >>>>>>>')
        # retry_handle(responses_from_nodes)

    print("Responses: ", responses_from_nodes)
    respond_nodes = responses_from_nodes.keys()
    successful_nodes = [node_ip for node_ip, code in responses_from_nodes.items() if code == 200]
    nodes_with_failed_response_dict = {node_ip: code for node_ip, code in responses_from_nodes.items() if code != 200}
    missed_nodes = list(set(nodes_ip) - set(respond_nodes))

    all_failed_nodes = set(list(nodes_with_failed_response_dict.keys()) + missed_nodes)
    is_w_concern_satisfied = (len(nodes_ip) + 1 - len(all_failed_nodes)) >= write_concern

    is_same_amount_of_responses_and_nodes = len(successful_nodes) == len(nodes_ip)
    if not responses_from_nodes:
        # TODO: Retry for all nodes
        return_message = f"🛑 '{message_to_send}' is NOT replicated at all."
    elif is_same_amount_of_responses_and_nodes:
        return_message = f"✅ '{message_to_send}' is replicated to all nodes."
    else:
        # TODO: Retry for certain node and change log
        return_message = f"✔️ '{message_to_send}' is replicated to few nodes."

    satisfied_w_concern_text = "satisfied ✅" if is_w_concern_satisfied else "not satisfied ⛔️"
    return_message += f" {write_concern=} {satisfied_w_concern_text}."
    return_message += f" Bad response: {nodes_with_failed_response_dict}." if nodes_with_failed_response_dict else ""
    return_message += f" No response : {missed_nodes}." if missed_nodes else ""

    logging.warning(return_message)
    return return_message

