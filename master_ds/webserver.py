from flask import Flask, request, render_template
from comunicator import send_to_nodes, logging, logs_filename, context


app = Flask(__name__, template_folder='src')


@app.route('/', methods=["GET", "POST"])
def handle_forms():
    max_write_concern = len(context.get_nodes_by_status('Healthy')) + 1
    if request.method == 'POST':
        message_to_append = (request.form['messageToAppend'])
        write_concern = int(request.form['writeConcern']) if request.form['writeConcern'].isdigit() else None

        full_message = (context.master_counter, message_to_append)
        context.master_counter += 1

        context.queue.append(full_message)
        logging.info(f'"{full_message}"({write_concern}) is saved on master.')

        response_text = send_to_nodes(full_message, write_concern)
        return render_template('main.html', append_info=response_text, max_wc=max_write_concern)
    elif request.method == 'GET' and request.args.get('action', None) == 'List':
        return render_template('main.html', list_messages=context.queue, max_wc=max_write_concern)
    else:
        return render_template('main.html', list_messages=context.queue, max_wc=max_write_concern)


@app.route('/logs', methods=["GET"])
def logs_out():
    with open(logs_filename, 'r') as log_file:
        logs_lines = log_file.readlines()
        # return f"<h1> </h2> <br>  <p>{content_of_file}</p>"
        return render_template('logs.html', logs_lines=logs_lines)


@app.route('/health', methods=["GET"])
def health():
    node_status_dict = context.nodes_health_status
    message = 'Nodes status:<br>'
    for ip, status in node_status_dict.items():
        message += f'{ip} –– {status}<br>'
    return message
