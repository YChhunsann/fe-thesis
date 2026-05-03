from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from pathlib import Path
import os
import shutil
import subprocess
import threading
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / 'templates'

app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
app.secret_key = 'rdlab_secret_key_2357'

PDF_PATH = BASE_DIR / 'thesis.pdf'
TEX_MAIN = BASE_DIR / 'thesis.tex'
LATEXMK_PATH = os.getenv('LATEXMK_PATH')

USERNAME = 'rdlab'
PASSWORD = 'rdlab2357'

def compile_latex():
    """Compile LaTeX document in background"""
    try:
        print("Starting LaTeX compilation...")
        latexmk_cmd = LATEXMK_PATH or shutil.which('latexmk')
        if not latexmk_cmd:
            print("latexmk not found. Add it to PATH or set LATEXMK_PATH.")
            return
        result = subprocess.run(
            [latexmk_cmd, '-xelatex', TEX_MAIN.name],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=120,  # Increased timeout to 2 minutes
        )
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

def resolve_workspace_path(relative_path):
    candidate = (BASE_DIR / relative_path).resolve()
    try:
        candidate.relative_to(BASE_DIR)
    except ValueError:
        return None
    return candidate

@app.route('/api/files')
def get_files():
    if 'logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    def get_directory_tree(path):
        items = []
        try:
            for item_path in sorted(path.iterdir(), key=lambda p: p.name.lower()):
                if item_path.name.startswith('.'):
                    continue
                relative_path = str(item_path.relative_to(BASE_DIR))
                
                if item_path.is_dir():
                    items.append({
                        'name': item_path.name,
                        'type': 'directory',
                        'path': relative_path,
                        'children': get_directory_tree(item_path)
                    })
                else:
                    items.append({
                        'name': item_path.name,
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
    
    full_path = resolve_workspace_path(file_path)
    if full_path is None:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not full_path.exists() or not full_path.is_file():
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
    
    full_path = resolve_workspace_path(file_path)
    if full_path is None:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not full_path.exists():
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
    
    if PDF_PATH.exists():
        response = send_file(str(PDF_PATH), as_attachment=False, max_age=0)
        response.headers['Cache-Control'] = 'no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
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
    
    full_path = resolve_workspace_path(file_path)
    if full_path is None:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not full_path.exists():
        return jsonify({'error': 'File not found'}), 404
    
    try:
        if full_path.is_file():
            full_path.unlink()
        elif full_path.is_dir():
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
        full_target_path = resolve_workspace_path(target_path or '.')
        if full_target_path is None:
            return jsonify({'error': 'Invalid path'}), 400
        
        if not full_target_path.exists():
            full_target_path.mkdir(parents=True, exist_ok=True)
        
        file_path = full_target_path / filename
        file.save(str(file_path))
        
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/image/<path:image_path>')
def get_image(image_path):
    if 'logged_in' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    full_path = resolve_workspace_path(image_path)
    if full_path is None:
        return jsonify({'error': 'Invalid path'}), 400
    
    if not full_path.exists() or not full_path.is_file():
        return jsonify({'error': 'Image not found'}), 404
    
    return send_file(str(full_path))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8485, debug=True)