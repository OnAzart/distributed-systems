from threading import Thread

from comunicator import context, eternal_heartbeat
from webserver import app


def main():
    context.form_cluster_info()
    print(context.nodes_health_status)

    health_check_thread = Thread(target=eternal_heartbeat)
    health_check_thread.daemon = True
    health_check_thread.start()

    app.run(host='0.0.0.0', debug=True, port=80)


if __name__ == '__main__':
    main()
