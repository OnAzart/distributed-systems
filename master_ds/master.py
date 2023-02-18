import threading

from comunicator import get_available_nodes, context, health_check_of_unhealthy_nodes
from webserver import app


def form_cluster_info():
    return {ip: 'Healthy' for ip in get_available_nodes('172.30.0')}


def main():
    context.nodes_health_status = form_cluster_info()
    print(context.nodes_health_status)

    health_check_thread = threading.Thread(target=health_check_of_unhealthy_nodes)
    health_check_thread.daemon = True
    health_check_thread.start()

    app.run(host='0.0.0.0', debug=True, port=80)


if __name__ == '__main__':
    main()
