from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
import os
import subprocess
import threading
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'rdlab_secret_key_2357'

BASE_DIR = '/home/vitoupro/code/fe-thesis-bachelor'
PDF_PATH = os.path.join(BASE_DIR, 'thesis.pdf')

USERNAME = 'rdlab'
PASSWORD = 'rdlab2357'

def compile_latex():
    """Compile LaTeX document in background"""
    try:
        print("Starting LaTeX compilation...")
        result = subprocess.run(['latexmk', '-xelatex', 'thesis.tex'], 
                              cwd=BASE_DIR, 
                              capture_output=True, 
                              text=True, 
                              timeout=120)  # Increased timeout to 2 minutes
        print(f"LaTeX compilation finished with result: {result.returncode}")
        if result.stdout:
            print(f"LaTeX stdout: {result.stdout}")
        if result.stderr:
            print(f"LaTeX stderr: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("LaTeX compilation timed out after 2 minutes")
    except Exception as e:
        print(f"LaTeX compilation error: {e}")

@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/api/files')
def get_files():
    if 'logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    def get_directory_tree(path, prefix=''):
        items = []
        try:
            for item in sorted(os.listdir(path)):
                if item.startswith('.'):
                    continue
                item_path = os.path.join(path, item)
                relative_path = os.path.relpath(item_path, BASE_DIR)
                
                if os.path.isdir(item_path):
                    items.append({
                        'name': item,
                        'type': 'directory',
                        'path': relative_path,
                        'children': get_directory_tree(item_path, prefix + '  ')
                    })
                else:
                    items.append({
                        'name': item,
                        'type': 'file',
                        'path': relative_path
                    })
        except PermissionError:
            pass
        return items
    
    return jsonify(get_directory_tree(BASE_DIR))

@app.route('/api/file/<path:file_path>')
def get_file_content(file_path):
    if 'logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    full_path = os.path.join(BASE_DIR, file_path)
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    except UnicodeDecodeError:
        return jsonify({'error': 'Cannot read binary file'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/file/<path:file_path>', methods=['POST'])
def save_file_content(file_path):
    if 'logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    full_path = os.path.join(BASE_DIR, file_path)
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Trigger LaTeX compilation in background for .tex files
        if file_path.endswith('.tex'):
            threading.Thread(target=compile_latex, daemon=True).start()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pdf')
def get_pdf():
    if 'logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if os.path.exists(PDF_PATH):
        return send_file(PDF_PATH, as_attachment=False)
    else:
        return jsonify({'error': 'PDF not found'}), 404

@app.route('/api/file/<path:file_path>', methods=['DELETE'])
def delete_file(file_path):
    if 'logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Check password for delete operation
    data = request.get_json()
    if not data or data.get('password') != PASSWORD:
        return jsonify({'error': 'Invalid password for delete operation'}), 401
    
    full_path = os.path.join(BASE_DIR, file_path)
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        if os.path.isfile(full_path):
            os.remove(full_path)
        elif os.path.isdir(full_path):
            import shutil
            shutil.rmtree(full_path)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    target_path = request.form.get('path', '')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        filename = secure_filename(file.filename)
        full_target_path = os.path.join(BASE_DIR, target_path)
        
        if not os.path.exists(full_target_path):
            os.makedirs(full_target_path, exist_ok=True)
        
        file_path = os.path.join(full_target_path, filename)
        file.save(file_path)
        
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/image/<path:image_path>')
def get_image(image_path):
    if 'logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    full_path = os.path.join(BASE_DIR, image_path)
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        return jsonify({'error': 'Image not found'}), 404
    
    return send_file(full_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8485, debug=True)