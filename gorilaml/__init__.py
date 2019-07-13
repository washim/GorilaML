import os, time, base64
from gorilaml.lab import contribaddons, authorize
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
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    if 'GORILAML_SETTINGS' in os.environ:
        app.config.from_pyfile(os.environ['GORILAML_SETTINGS'])
    
    try:
        os.mkdir(app.instance_path)
    except:
        pass
    
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
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], session['username'], filename)
                file.save(file_path)
                
                if os.path.exists(file_path):
                    with ZipFile(file_path, 'r') as zip:
                        zip.extractall(os.path.join(app.config['UPLOAD_FOLDER'], session['username']))
                    
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

    @app.route('/addons')
    @authorize
    def addons():
        return 'inprogress'

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
    
    with app.app_context():
        allAddons = db.query_db('SELECT * FROM addons WHERE status=? and author_id=?', (1, 1))
    
    for addon in contribaddons(app.instance_path, allAddons).getAddons().values():
        try:
            app.register_blueprint(addon)
        except:
            pass

    return app