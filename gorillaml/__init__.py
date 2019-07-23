import os
import sys
import click
import importlib
from gorillaml.lab import authorize, securetoken, reload
from gorillaml import db
from gorillaml import form
from flask import (
    Flask, render_template, request, flash, redirect, url_for, session
)
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask.cli import FlaskGroup


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.urandom(12),
        PLUGIN_UPLOAD_FOLDER=os.path.join(app.instance_path, 'addons')
    )

    CORS(app)
    form.csrf.init_app(app)
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
        dbconn = db.get_db()
        plugin = form.PluginUploadForm()

        if plugin.validate_on_submit():
            filename = secure_filename(plugin.upload.data.filename)
            parse_file_name = filename.split('.')

            try:
                add_plugin = db.Plugins(author_id=session['user_id'], name=parse_file_name[0])
                dbconn.add(add_plugin)
                dbconn.commit()
            except:
                flash('Plugin already exist. It should be unique for each upload.', 'error')
                return redirect(url_for('plugin_upload'))

            flash('Your plugin successfully uploaded and pending for approval.', 'success')

            return redirect(
                url_for('plugin_upload')
            )

        return render_template('plugin_upload.html', form=plugin)

    @app.route('/register-local', methods=['GET', 'POST'])
    @authorize
    def register_local():
        dbconn = db.get_db()
        local_plugin = form.RegisterLocalPluginForm()

        if local_plugin.validate_on_submit():
            try:
                add_plugins = db.Plugins(author_id=session['user_id'], name=local_plugin.local_plugin_name.data,
                                         plugin_path=local_plugin.local_plugin_path.data)
                dbconn.add(add_plugins)
                dbconn.commit()
            except:
                flash('Plugin already exist. It should be unique for each upload.', 'error')
                return redirect(url_for('register_local'))

            flash('Your plugin successfully uploaded and pending for approval.', 'success')

            return redirect(
                url_for('register_local')
            )

        return render_template('register_local.html', form=local_plugin)

    @app.route('/site-config', methods=['GET','POST'])
    @authorize
    def site_config():
        dbconn = db.get_db()
        siteconfig = dbconn.query(db.Configs).all()
        config = form.RegisterSiteConfigForm(siteconfig)

        for item in siteconfig:
            if item.key == 'site_logo':
                config.site_logo.data = item.value
            elif item.key == 'site_name':
                config.site_name.data = item.value
            elif item.key == 'site_slogan':
                config.site_slogan.data = item.value
            elif item.key == 'page_title':
                config.page_title.data = item.value

        if config.validate_on_submit():
            try:
                dbconn.add(db.Configs(key='site_logo', value=config.site_logo.data))
            except:
                dbconn.query(db.Configs).filter(db.Configs.key == 'site_logo').update({'value': config.site_logo.data})

            try:
                dbconn.add(db.Configs(key='site_name', value=config.site_name.data))
            except:
                dbconn.query(db.Configs).filter(db.Configs.key == 'site_name').update({'value': config.site_name.data})

            try:
                dbconn.add(db.Configs(key='site_slogan', value=config.site_slogan.data))
            except:
                dbconn.query(db.Configs).filter(db.Configs.key == 'site_slogan').update({'value': config.site_slogan.data})

            try:
                dbconn.add(db.Configs(key='page_title', value=config.page_title.data))
            except:
                dbconn.query(db.Configs).filter(db.Configs.key == 'page_title').update({'value': config.page_title.data})

            dbconn.commit()
            flash('Configuration updated successfully.', 'success')

        return render_template('site_config.html', form=config)

    @app.route('/')
    @authorize
    def home():
        return redirect(url_for('plugins'))

    @app.route('/logout')
    @authorize
    def logout():
        session.pop('user_id', None)
        session.pop('username', None)
        session.pop('password', None)

        return redirect(url_for('login'))

    @app.route('/myaccount', methods=['GET', 'POST'])
    @authorize
    def myaccount():
        if request.args.get('plugins') == 'recreate':
            reload()
            flash('Plugins cache reloaded successfully. Refresh this page again.', 'success')
            return redirect(url_for('myaccount', token=securetoken()))

        else:
            dbconn = db.get_db()
            myaccount = form.MyaccountForm()
            if myaccount.validate_on_submit():
                dbconn.query(db.Users).filter(db.Users.id == session['user_id']).update({'password': myaccount.confirm.data})
                dbconn.commit()
                flash('Password updated successfully.', 'success')
                return redirect(url_for('logout'))

        return render_template('myaccount.html', form=myaccount)

    @app.route('/plugins')
    @authorize
    def plugins():
        dbconn = db.get_db()
        name = request.args.get('name')
        if name:
            results = dbconn.query(db.Plugins).filter(db.Plugins.name == name).all()
        else:
            results = dbconn.query(db.Plugins).all()

        return render_template('plugins.html', plugins=results)

    @app.route('/plugin-activation/<string:status>/<int:pid>')
    @authorize
    def plugin_activation(status, pid):
        pstatus = {'installed': 1, 'uninstalled': 2, 'pending': 0}
        dbconn = db.get_db()
        dbconn.query(db.Plugins).filter(db.Plugins.id == pid).update({'status': pstatus[status]})
        dbconn.commit()
        return redirect(url_for('plugins'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            dbconn = db.get_db()
            getuser = dbconn.query(db.Users).filter(db.Users.username == request.form['username'] and
                                                    db.Users.password == request.form['password']).first()
            if getuser:
                session['user_id'] = getuser.id
                session['username'] = getuser.username
                session['password'] = getuser.password
                return redirect(
                    url_for('plugins')
                )
            else:
                flash('Login failed. Please try again.', 'error')
                return redirect(request.url)

        return render_template('login.html')

    @app.context_processor
    def username():
        if 'username' in session:
            return dict(username=session['username'])
        else:
            return ''

    with app.app_context():
        dbconn = db.get_db()
        try:
            allplugins = dbconn.query(db.Plugins).filter(db.Plugins.status == 1).all()
            for plugin in allplugins:
                try:
                    if plugin.plugin_path == 'system':
                        plugin_libs = importlib.import_module('addons.%s.%s.api' % (plugin.user.username, plugin.name))
                        bp = getattr(plugin_libs, 'gorillaml')
                        app.register_blueprint(bp)
                    else:
                        if plugin.plugin_path not in sys.path:
                            sys.path.append(plugin.plugin_path)

                        plugin_libs = importlib.import_module('%s.api' % plugin.name)
                        bp = getattr(plugin_libs, 'gorillaml')
                        app.register_blueprint(bp)
                except Exception as e:
                    pass
        except Exception as e:
            pass

    return app


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    os.environ['FLASK_ENV'] = 'development'
