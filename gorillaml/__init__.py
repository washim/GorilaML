import os
import sys
import importlib
from gorillaml.lab import authorize, securetoken, reload
from gorillaml import db
from gorillaml.reloader import last_reloaded
from gorillaml.form import csrf, PluginUploadForm, RegisterLocalPluginForm, MyaccountForm
from flask import (
    Flask, render_template, request, flash, redirect, url_for, session
)
from werkzeug.utils import secure_filename
from flask_cors import CORS


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.urandom(12),
        DATABASE=os.path.join(app.instance_path, '%s.sqlite' % __name__),
        PLUGIN_UPLOAD_FOLDER=os.path.join(app.instance_path, 'addons')
    )

    CORS(app)
    csrf.init_app(app)
    db.init_app(app)
    
    if 'GORILAML_SETTINGS' in os.environ:
        app.config.from_pyfile(os.environ['GORILAML_SETTINGS'])

    if os.path.isdir(app.instance_path) == False:
        os.mkdir(app.instance_path)
    
    if os.path.isdir(app.config['PLUGIN_UPLOAD_FOLDER']) == False:
        os.mkdir(app.config['PLUGIN_UPLOAD_FOLDER'])
    
    sys.path.append(app.instance_path)

    @app.route('/plugin-upload', methods=['GET', 'POST'])
    @authorize
    def plugin_upload():
        plugin = PluginUploadForm()
        if plugin.validate_on_submit():
            filename = secure_filename(plugin.upload.data.filename)
            parse_file_name = filename.split('.')
            
            try:
                db.insert_db('plugins', ('author_id', 'name', 'status'), (session['user_id'], parse_file_name[0], 1))
            except:
                flash('Plugin already exist. It should be unique for each upload.','error')
                return redirect(url_for('plugin_upload'))
            
            reload()
            flash('Your plugin successfully installed.', 'success')
            
            return redirect(
                url_for('plugin_upload', token=securetoken())
            )
        
        return render_template('plugin_upload.html', form=plugin)
    
    @app.route('/register-local', methods=['GET', 'POST'])
    @authorize
    def register_local():
        local_plugin = RegisterLocalPluginForm()
        if local_plugin.validate_on_submit():
            try:
                db.insert_db('plugins', ('author_id', 'name', 'plugin_path', 'status'),
                             (session['user_id'], local_plugin.local_plugin_name.data,
                              local_plugin.local_plugin_path.data, 1))
            except:
                flash('Plugin already exist. It should be unique for each upload.','error')
                return redirect(url_for('register_local'))

            reload()
            flash('Your plugin successfully installed.', 'success')

            return redirect(
                url_for('register_local', token=securetoken())
            )
        
        return render_template('register_local.html', form=local_plugin)

    @app.route('/')
    @authorize
    def home():
        return render_template('home.html')

    @app.route('/logout')
    @authorize
    def logout():
        session.pop('username', None)
        return redirect(url_for('login'))

    @app.route('/myaccount', methods=['GET', 'POST'])
    @authorize
    def myaccount():
        if request.args.get('plugins') == 'recreate':
            reload()
            flash('Plugins cache reloaded successfully. Refresh this page again.', 'success')
            return redirect(url_for('myaccount', token=securetoken()))

        else:
            form = MyaccountForm()
            if form.validate_on_submit():
                db.update_db('user', ('password',), (form.confirm.data,), ('id',), (session['user_id'],))
                flash('Password updated successfully.', 'success')
                return redirect(url_for('myaccount'))

        return render_template('myaccount.html', form=form)

    @app.route('/plugins')
    @authorize
    def plugins():
        name = request.args.get('name')
        if name:
            results = db.query_db('SELECT t1.*,t2.username FROM plugins t1 join user t2 ON t1.author_id=t2.id WHERE t1.name LIKE ?', (f'%{name}%',))
        else:
            results = db.query_db('SELECT t1.*,t2.username FROM plugins t1 join user t2 ON t1.author_id=t2.id')
        return render_template('plugins.html', plugins=results)

    @app.route('/plugin-activation/<string:status>/<int:pid>')
    @authorize
    def plugin_activation(status, pid):
        pstatus = {'installed': 1, 'uninstalled': 0}
        db.update_db('plugins', ('status',), (pstatus[status],), ('id',), (pid,))

        return redirect(url_for('plugins', token=securetoken()))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            getuser = db.query_db('SELECT * FROM user WHERE username=? and password=?',
                                  (request.form['username'], request.form['password']), True)
            if getuser:
                session['user_id'] = getuser['id']
                session['username'] = getuser['username']
                session['password'] = getuser['password']
                return redirect(
                    url_for('plugins', token=securetoken())
                )
            else:
                flash('Login failed. Please try again.','error')
                return redirect(request.url)
        
        return render_template('login.html')
    
    @app.context_processor
    def username():
        if 'username' in session:
            return dict(username=session['username'])
        else:
            return ''

    try:
        with app.app_context():
            allplugins = db.query_db('SELECT t1.*,t2.username FROM plugins t1 join user t2 ON t1.author_id=t2.id WHERE t1.status=1')
        
        for plugin in allplugins:
            try:
                if plugin['plugin_path'] == 'system':
                    plugin_libs = importlib.import_module('addons.%s.%s.api' % (plugin['username'], plugin['name']))
                    bp = getattr(plugin_libs, 'gorilaml')
                    app.register_blueprint(bp)
                else:
                    if plugin['plugin_path'] not in sys.path:
                        sys.path.append(plugin['plugin_path'])
                    
                    plugin_libs = importlib.import_module('%s.api' % plugin['name'])
                    bp = getattr(plugin_libs, 'gorilaml')
                    app.register_blueprint(bp)
            except:
                pass
    except:
        pass

    return app