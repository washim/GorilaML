import os
import time
import base64
import sys
from gorilaml.lab import getplugins, authorize
from gorilaml import db
from gorilaml.reloader import last_reloaded
from flask import (
    Flask, Blueprint, render_template, jsonify, request, flash, redirect, url_for, session
)
from werkzeug.utils import secure_filename
from flask_cors import CORS
from zipfile import ZipFile
from functools import wraps

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.urandom(12),
        DATABASE=os.path.join(app.instance_path, 'gorilaml.sqlite'),
    )
    
    CORS(app)
    UPLOAD_FOLDER = os.path.join(app.instance_path, 'addons')
    ALLOWED_EXTENSIONS = set(['zip'])
    
    if 'GORILAML_SETTINGS' in os.environ:
        app.config.from_pyfile(os.environ['GORILAML_SETTINGS'])

    if os.path.isdir(app.instance_path) == False:
        os.mkdir(app.instance_path)
        sys.path.append(app.instance_path)
    
    if os.path.isdir(UPLOAD_FOLDER) == False:
        os.mkdir(UPLOAD_FOLDER)
    
    db.init_app(app)

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @app.route('/addon-upload', methods=['GET', 'POST'])
    @authorize
    def upload_file():
        if request.method == 'POST':
            if 'addon-file-name' not in request.files:
                flash('No file part','error')
                return redirect(request.url)
            
            file = request.files['addon-file-name']
            
            if file.filename == '':
                flash('No selected file','error')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                
                if os.path.isdir(os.path.join(UPLOAD_FOLDER, session['username'])) == False:
                    os.mkdir(os.path.join(UPLOAD_FOLDER, session['username']))
                
                file_path = os.path.join(UPLOAD_FOLDER, session['username'], filename)
                file.save(file_path)
                
                if os.path.exists(file_path):
                    with ZipFile(file_path, 'r') as zip:
                        zip.extractall(os.path.join(UPLOAD_FOLDER, session['username']))
                    
                    os.remove(file_path)
                
                flash('Your addon successfully installed.','success')
                
                fp = open('gorilaml/reloader.py', 'w+')
                fp.write("last_reloaded='%s'" % time.time())
                fp.close()
                
                return redirect(
                    url_for('upload_file', token=base64.b64encode((session['username']+':'+session['password']).encode()))
                )
            
            else:
                flash('Please select valid file.','error')
                return redirect(request.url)
        
        return render_template('addon_upload.html')
    
    @app.route('/')
    @authorize
    def home():
        return render_template('home.html')

    @app.route('/logout')
    @authorize
    def logout():
        session.pop('username', None)
        return redirect(url_for('login'))

    @app.route('/myaccount')
    @authorize
    def myaccount():
        return 'inprogress'

    @app.route('/plugins')
    @authorize
    def plugins():
        results = db.get_data('plugins')
        return render_template('plugins.html', plugins=results)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            getuser = db.query_db('SELECT * FROM user WHERE username=? and password=?', (request.form['username'], request.form['password']), True)
            if getuser:
                session['username'] = getuser['username']
                session['password'] = getuser['password']
                flash('Welcome back, you are authenticated successfully.','success')
                return redirect(
                    url_for('home', token=base64.b64encode((session['username']+':'+session['password']).encode()))
                )
            else:
                flash('Login failed. Please try again.','error')
                return redirect(request.url)
        
        return render_template('login.html')
    
    try:
        for addon in getplugins(app):
            try:
                app.register_blueprint(addon)
            except:
                pass
    except:
        pass

    return app