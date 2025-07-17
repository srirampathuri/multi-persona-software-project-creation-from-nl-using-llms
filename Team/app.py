from flask import Flask, render_template, request, jsonify, send_file
import threading
from orchestrator import run_orchestrator
import os
import zipfile
import io
import json
import time

app = Flask(__name__)
results = {}
HISTORY_FILE = 'history.json'

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def add_to_history(session_id, prompt, status):
    history = load_history()
    entry = {
        'session_id': session_id,
        'prompt': prompt,
        'timestamp': int(time.time()),
        'status': status
    }
    history.append(entry)
    save_history(history)

def update_history_status(session_id, status):
    history = load_history()
    for entry in history:
        if entry['session_id'] == session_id:
            entry['status'] = status
            break
    save_history(history)

def workflow_thread(user_idea, session_id):
    def update_progress(status):
        results[session_id] = {'status': status}
    update_progress('Processing...')
    result = run_orchestrator(user_idea, progress_callback=update_progress)
    results[session_id] = result
    update_history_status(session_id, result.get('status', 'Unknown'))

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    user_idea = request.form['idea']
    session_id = str(len(results) + 1)
    thread = threading.Thread(target=workflow_thread, args=(user_idea, session_id))
    thread.start()
    return jsonify({'session_id': session_id})

@app.route('/status/<session_id>')
def status(session_id):
    result = results.get(session_id, {'status': 'Processing...'})
    response = dict(result)
    if 'project_dir' in result:
        response['download_url'] = f"/download/{session_id}"
    return jsonify(response)

@app.route('/output-directory')
def output_directory():
    output_dir = os.path.join(os.path.dirname(__file__), 'calculator_app')
    if not os.path.exists(output_dir):
        files = []
    else:
        files = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]
    return jsonify({'files': files})

@app.route('/download/<session_id>')
def download_project(session_id):
    result = results.get(session_id)
    if not result or 'project_dir' not in result:
        return 'Project not found or not ready', 404
    project_dir = result['project_dir']
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, project_dir)
                zf.write(file_path, arcname)
    memory_file.seek(0)
    zip_filename = os.path.basename(project_dir.rstrip('/\\')) + '.zip'
    return send_file(memory_file, download_name=zip_filename, as_attachment=True)

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(load_history())

@app.route('/history', methods=['DELETE'])
def clear_history():
    save_history([])
    return '', 204

@app.route('/history/<session_id>', methods=['DELETE'])
def delete_history_item(session_id):
    history = load_history()
    history = [h for h in history if h['session_id'] != session_id]
    save_history(history)
    return '', 204

if __name__ == '__main__':
    app.run(debug=False, use_reloader=False) 