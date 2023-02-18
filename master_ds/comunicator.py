import json
import logging
import sys
import threading
import subprocess
import time

import backoff
import requests

from datetime import datetime

logs_filename = 'master.log'
logging.basicConfig(filename=logs_filename, filemode='a', level=logging.INFO,
                    format='%(asctime)s :: %(levelname)-8s :: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


class MessageQueueContext:
    nodes_health_status = {}
    master_counter = 0
    queue = []

    def get_nodes_by_status(self, expected_status):
        return {ip: status for ip, status in self.nodes_health_status.items() if status == expected_status}

    def set_node_status(self, ip, status):
        self.nodes_health_status[ip] = status


context = MessageQueueContext()


def health_check(ip):
    return subprocess.call(['ping', '-c', '2', '-W', '1', ip], stdout=subprocess.DEVNULL)


def restore_queue_for_alive_node(node_ip):
    try:
        _post_message_to_node(node_ip, json.dumps(context.queue), purpose='restore')
    except requests.ConnectTimeout:
        logging.warning(f"[Restore Retry Failed] Node {node_ip} is not available again!")


def health_check_of_unhealthy_nodes():
    while True:
        unhealthy_nodes_ip_list = context.get_nodes_by_status('Unhealthy')
        print(datetime.now())
        if unhealthy_nodes_ip_list:
            logging.warning(f"[Heartbeat] Unhealthy nodes: {unhealthy_nodes_ip_list}")
        else:
            logging.info("[Heartbeat] - all good")

        for unhealthy_node_ip in unhealthy_nodes_ip_list:
            health_result = health_check(unhealthy_node_ip)
            if health_result == 0:
                # additional check
                context.set_node_status(unhealthy_node_ip, 'Suspended')
                logging.info(f"[Heartbeat success] {unhealthy_node_ip} connection is restoring (Suspended).")

                threading.Event().wait(4)
                additional_health_result = health_check(unhealthy_node_ip)
                if additional_health_result != 0:
                    continue

                context.set_node_status(unhealthy_node_ip, 'Healthy')
                logging.info(f"[Heartbeat success] {unhealthy_node_ip} connection is restored.")
                restore_queue_for_alive_node(unhealthy_node_ip)
            else:
                logging.warning(f"[Heartbeat warn] {unhealthy_node_ip} is still out!")
        threading.Event().wait(60)


def get_available_nodes(ip_range):
    available_nodes = []
    for i in range(3, 255):
        ip = ip_range + '.' + str(i)
        result = health_check(ip)
        if result == 0:
            available_nodes.append(ip)
        else:
            break
    return available_nodes


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5,
                      on_backoff=lambda details: context.set_node_status(ip=details['args'][0], status='Suspended')
                      if details['tries'] == 1 else 0,
                      on_giveup=lambda details: context.set_node_status(ip=details['args'][0], status='Unhealthy'),
                      on_success=lambda details: context.set_node_status(ip=details['args'][0], status='Healthy'))
def _post_message_to_node(node, encoded_message_to_send, purpose='append'):
    resp = requests.post(f'http://{node}/get_info',
                         data=encoded_message_to_send,
                         timeout=2,
                         params={'purpose': purpose})
    return resp.status_code


def sending_to_node(node, message, barrier, responses_dict):
    # for test
    print(node, datetime.now())
    #####
    logging.info(f"Sending message to {node} secondary node.")

    try:
        # We can use docker compose --scale to scale secondary and use their dns name to communicate
        responses_dict[node] = _post_message_to_node(node, json.dumps(message))
        logging.info(f"Node ({node}) respond with {responses_dict[node]} status code.")
        barrier.wait()
    except requests.ConnectTimeout:
        logging.warning(f"[Retry failed] Node {node} is not available.")


def handle_responses_for_client(responses_from_nodes, nodes_ip, write_concern, message_to_send):
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
    return return_message


def send_to_nodes(message_to_send, write_concern):
    nodes_ip = context.get_nodes_by_status('Healthy').keys()
    if not write_concern or write_concern > len(nodes_ip) + 1:
        write_concern = len(nodes_ip) + 1
    print(f'{write_concern=}')

    responses_from_nodes = {}
    # timeout_for_sending = 15
    barrier = threading.Barrier(parties=write_concern)
    for node_ip in nodes_ip:
        thr = threading.Thread(target=sending_to_node, args=(node_ip, message_to_send, barrier, responses_from_nodes))
        thr.start()
    try:
        barrier.wait()
    except threading.BrokenBarrierError:
        logging.warning('<<<<<< error. BarrierError happened >>>>>>>')
    print("Responses: ", responses_from_nodes)
    return_message = handle_responses_for_client(responses_from_nodes, nodes_ip, write_concern, message_to_send)
    logging.warning(return_message)
    return return_message
