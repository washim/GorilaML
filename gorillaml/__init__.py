import os
import sys
import click
import importlib
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask.cli import FlaskGroup
from gorillaml import db
from gorillaml import form
from gorillaml.lab import (
    authorize, admin_login_required, securetoken, check_new_version
)
from flask import (
    Flask, render_template, request, flash, redirect, url_for, session
)


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.urandom(12),
        PLUGIN_UPLOAD_FOLDER=os.path.join(app.instance_path, 'addons'),
        VERSION='0.0.7'
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

    @app.route('/')
    @authorize
    def home():
        return redirect(url_for('plugins'))

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
    @admin_login_required
    @authorize
    def site_config():
        dbconn = db.get_db()

        sitedata = {}
        siteconfig = dbconn.query(db.Configs).all()

        for item in siteconfig:
            if item.key == 'site_logo':
                sitedata['site_logo'] = item.value
            elif item.key == 'site_name':
                sitedata['site_name'] = item.value
            elif item.key == 'site_slogan':
                sitedata['site_slogan'] = item.value
            elif item.key == 'page_title':
                sitedata['page_title'] = item.value
            elif item.key == 'copyrights':
                sitedata['copyrights'] = item.value

        config = form.RegisterSiteConfigForm(site_name=sitedata['site_name'], site_slogan=sitedata['site_slogan'],
                                             page_title=sitedata['page_title'], copyrights=sitedata['copyrights'])

        if config.validate_on_submit():
            uploaded_file = config.site_logo.data

            try:
                filename = secure_filename(uploaded_file.filename)
                file_path = os.path.join(app.root_path, 'static/img', filename)
                uploaded_file.save(file_path)

                dbconn.query(db.Configs).filter(db.Configs.key == 'site_logo').update({'value': filename})
            except:
                pass

            dbconn.query(db.Configs).filter(db.Configs.key == 'site_name').update({'value': config.site_name.data})
            dbconn.query(db.Configs).filter(db.Configs.key == 'site_slogan').update({'value': config.site_slogan.data})
            dbconn.query(db.Configs).filter(db.Configs.key == 'page_title').update({'value': config.page_title.data})
            dbconn.query(db.Configs).filter(db.Configs.key == 'copyrights').update({'value': config.copyrights.data})

            dbconn.commit()

            flash('Configuration updated successfully.', 'success')
            return redirect(url_for('site_config'))

        return render_template('site_config.html', form=config, context=dict(site_logo=sitedata['site_logo']))

    @app.route('/plugins-cache-recreate', methods=['GET', 'POST'])
    @admin_login_required
    @authorize
    def plugins_cache_recreate():
        shutdown = request.environ.get('werkzeug.server.shutdown')
        if shutdown:
            shutdown()

        return ''

    @app.route('/plugin-activation/<string:status>/<int:pid>')
    @admin_login_required
    @authorize
    def plugin_activation(status, pid):
        pstatus = {'installed': 1, 'uninstalled': 2, 'pending': 0}
        dbconn = db.get_db()
        dbconn.query(db.Plugins).filter(db.Plugins.id == pid).update({'status': pstatus[status]})
        dbconn.commit()
        return redirect(url_for('plugins'))

    @app.route('/plugins')
    @authorize
    def plugins():
        dbconn = db.get_db()
        name = request.args.get('name')
        if name:
            results = dbconn.query(db.Plugins).filter(db.Plugins.name.like(f'%{name}%')).all()
        else:
            results = dbconn.query(db.Plugins).all()

        return render_template('plugins.html', plugins=results)

    @app.route('/create-user', methods=['GET', 'POST'])
    @admin_login_required
    @authorize
    def create_user():
        dbconn = db.get_db()

        if request.args.get('id'):
            user = dbconn.query(db.Users).filter(db.Users.id == request.args.get('id'))
            userdata = user.first()
            createuser = form.CreateUserForm(username=userdata.password, password=userdata.password, confirm=userdata.password,
                                             role=userdata.role, status=userdata.status)
        else:
            createuser = form.CreateUserForm()

        if createuser.validate_on_submit():
            try:
                adduser = db.Users(username=createuser.username.data, password=createuser.password.data,
                                   role=createuser.role.data, status=createuser.status.data)
                dbconn.add(adduser)
                dbconn.commit()
                flash('User created successfully.', 'success')

            except:
                dbconn.rollback()
                if request.args.get('id'):
                    user.update({'password': createuser.password.data, 'role': createuser.role.data, 'status': createuser.status.data})
                    dbconn.commit()
                    flash('User updated successfully.', 'success')

            redirect(url_for('create_user'))

        return render_template('create_user.html', form=createuser)

    @app.route('/list-users')
    @admin_login_required
    @authorize
    def list_users():
        dbconn = db.get_db()
        list_users = dbconn.query(db.Users).all()
        return render_template('list_users.html', users=list_users)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            dbconn = db.get_db()
            getuser = dbconn.query(db.Users).filter((db.Users.username == request.form['username']) &
                                                    (db.Users.password == request.form['password']) &
                                                    (db.Users.status == 'enabled')).first()
            if getuser:
                session['user_id'] = getuser.id
                session['username'] = getuser.username
                session['password'] = getuser.password
                session['role'] = getuser.role
                session['status'] = getuser.status

                return redirect(url_for('plugins'))

            else:
                flash('Login failed. Please try again.', 'error')
                return redirect(request.url)

        return render_template('login.html')

    @app.route('/reauth', methods=['GET', 'POST'])
    @admin_login_required
    @authorize
    def reauth():
        flash('Plugins cache reloaded successfully.', 'success')
        return redirect(url_for('myaccount'))

    @app.route('/myaccount', methods=['GET', 'POST'])
    @authorize
    def myaccount():
        dbconn = db.get_db()
        myaccount = form.MyaccountForm()
        if myaccount.validate_on_submit():
            dbconn.query(db.Users).filter(db.Users.id == session['user_id']).update(
                {'password': myaccount.confirm.data})
            dbconn.commit()
            flash('Password updated successfully.', 'success')
            return redirect(url_for('logout'))

        return render_template('myaccount.html', form=myaccount, token=securetoken())

    @app.route('/logout')
    @authorize
    def logout():
        session.pop('user_id', None)
        session.pop('username', None)
        session.pop('password', None)
        session.pop('role', None)
        session.pop('status', None)

        return redirect(url_for('login'))

    @app.context_processor
    def context():
        dbconn = db.get_db()
        siteconfig = dbconn.query(db.Configs).all()
        site_context = {}

        for item in siteconfig:
            if item.key == 'site_logo':
                site_context['site_logo'] = item.value
            elif item.key == 'site_name':
                site_context['site_name'] = item.value
            elif item.key == 'site_slogan':
                site_context['site_slogan'] = item.value
            elif item.key == 'page_title':
                site_context['page_title'] = item.value
            elif item.key == 'copyrights':
                site_context['copyrights'] = item.value
            elif item.key == 'available_version':
                site_context['available_version'] = item.value
            elif item.key == 'available_version_check_date':
                site_context['available_version_check_date'] = item.value

        if 'username' in session:
            site_context['username'] = session['username']
            site_context['role'] = session['role']
            site_context['status'] = session['status']
        else:
            site_context['username'] = 'Anonymous'

        duration = datetime.today() - datetime.strptime(site_context['available_version_check_date'], '%Y-%m-%d %H:%M:%S.%f')

        if duration.days > 5:
            check_new_version()

        site_context['version'] = app.config['VERSION']
        site_context['available_version'] = site_context['available_version']

        return site_context

    with app.app_context():
        dbconn = db.get_db()
        allplugins = []

        try:
            allplugins = dbconn.query(db.Plugins).filter(db.Plugins.status == 1).all()
        except:
            pass

        for plugin in allplugins:
            try:
                if plugin.plugin_path == 'system':
                    plugin_libs = importlib.import_module('addons.%s.%s.plugin' % (plugin.user.username, plugin.name))
                    bp = getattr(plugin_libs, 'gorillaml')
                    app.register_blueprint(bp)

                else:
                    if plugin.plugin_path not in sys.path:
                        sys.path.append(plugin.plugin_path)

                    plugin_libs = importlib.import_module('%s.plugin' % plugin.name)
                    bp = getattr(plugin_libs, 'gorillaml')
                    app.register_blueprint(bp)

            except Exception as e:
                pass

    return app


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    os.environ['FLASK_ENV'] = 'production'