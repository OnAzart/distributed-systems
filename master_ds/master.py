from flask import Flask, request, render_template

from comunicator import send_to_nodes, logging, logs_filename

app = Flask(__name__, template_folder='src')

queue = []


@app.route('/', methods=["GET", "POST"])
def handle_forms():
    if request.method == 'POST':
        message_to_append = (request.form['messageToAppend'])
        write_concern = int(request.form['writeConcern']) if request.form['writeConcern'].isdigit() else None

        queue.append(message_to_append)
        logging.info(f'"{message_to_append}"({write_concern}) is saved on master.')

        response_text = send_to_nodes(message_to_append, write_concern)
        return render_template('main.html', append_info=response_text)
    elif request.method == 'GET' and request.args.get('action', None) == 'List':
        return render_template('main.html', list_messages=queue)
    else:
        return render_template('main.html', list_messages=queue)


@app.route('/logs', methods=["GET"])
def logs_out():
    with open(logs_filename, 'r') as log_file:
        logs_lines = log_file.readlines()
        # return f"<h1> </h2> <br>  <p>{content_of_file}</p>"
        return render_template('logs.html', logs_lines=logs_lines)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=80)
