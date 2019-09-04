import os
import sys
import click
import shutil
import importlib
import threading
from ast import literal_eval
from datetime import datetime
from PyQt5 import QtWidgets
from werkzeug.utils import secure_filename
from werkzeug.serving import run_simple
from flask_wtf import FlaskForm
from flask_cors import CORS
from flask.cli import FlaskGroup
from gorillaml import db
from gorillaml import form
from gorillaml.widget import Ui_MainWindow
from gorillaml.lab import (
    authorize, admin_login_required, securetoken, check_new_version
)
from flask import (
    Flask, render_template, request, flash, redirect, url_for, session
)
from wtforms import (
    StringField, SelectField, IntegerField, FloatField, DecimalField, RadioField, HiddenField, PasswordField,
    SelectMultipleField, TextAreaField, BooleanField, FileField, SubmitField, validators
)

plugins_context_rebuild = False

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.urandom(12),
        PLUGIN_UPLOAD_FOLDER=os.path.join(app.instance_path, 'addons'),
        VERSION='0.1.3'
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
        dbconn = db.get_db()
        users = dbconn.query(db.Users).all()
        plugins = dbconn.query(db.Plugins).all()

        return render_template('home.html', users=users, plugins=plugins)

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

        metadata = {
            'info': {
                'title': 'Upload your plugin',
                'class': 'col-md-12',
                'body_class': None,
                'type': None,
                'footer': '<button type="Create" class="btn btn-primary" frmtarget="#form_addon_upload">Upload</button>'
            },
            'form_data': {
                'form_id': 'form_addon_upload',
                'form': plugin,
                'method': 'POST',
                'encryption': 'multipart/form-data',
                'extra': None
            }
        }

        return render_template('plugin_upload.html', metadata=metadata)

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

        metadata = {
            'info': {
                'title': 'Register your plugin from your local machine',
                'class': 'col-md-12',
                'body_class': None,
                'type': None,
                'footer': '<button type="submit" class="btn btn-primary" frmtarget="#form_register_plugin">Register</button>'
            },
            'form_data': {
                'form_id': 'form_register_plugin',
                'form': local_plugin,
                'method': 'POST',
                'encryption': None,
                'extra': None
            }
        }

        return render_template('register_local.html', metadata=metadata)

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

        metadata = {
            'info': {
                'title': 'Site Configurations',
                'class': 'col-md-12',
                'body_class': None,
                'type': None,
                'footer': '<button type="submit" class="btn btn-primary" frmtarget="#form_site_config">Save Config</button>'
            },
            'form_data': {
                'form_id': 'form_site_config',
                'form': config,
                'method': 'POST',
                'encryption': 'multipart/form-data',
                'extra': None
            }
        }

        return render_template('site_config.html', metadata=metadata)

    @app.route('/plugins-cache-recreate', methods=['GET', 'POST'])
    @admin_login_required
    @authorize
    def plugins_cache_recreate():
        global plugins_context_rebuild
        plugins_context_rebuild = True
        return redirect(url_for('reauth', token=securetoken()))

    @app.route('/plugin-activation/<string:status>/<int:pid>')
    @admin_login_required
    @authorize
    def plugin_activation(status, pid):
        try:
            pstatus = {'installed': 1, 'uninstalled': 2, 'pending': 0}
            dbconn = db.get_db()
            plugin = dbconn.query(db.Plugins).filter(db.Plugins.id == pid)
            if status == 'delete':
                plugin_details = plugin.first()
                if plugin_details.plugin_path == 'system':
                    user_folder = os.path.join(app.config['PLUGIN_UPLOAD_FOLDER'], session['username'])
                    shutil.rmtree(os.path.join(user_folder, plugin_details.name), ignore_errors=True)
                flash('Plugin deleted successfully.', 'success')
                plugin.delete(synchronize_session=False)
            else:
                flash('Plugin updated successfully.', 'success')
                plugin.update({'status': pstatus[status]})

            dbconn.commit()
            global plugins_context_rebuild
            plugins_context_rebuild = True

        except:
            flash('Permission denied.', 'error')

        return redirect(url_for('plugins', token=securetoken()))

    @app.route('/user-activation/<string:status>/<int:uid>')
    @admin_login_required
    @authorize
    def user_activation(status, uid):
        if session['user_id'] == uid:
            flash('Permission denied to disable your own account.', 'error')
            return redirect(url_for('list_users'))

        try:
            dbconn = db.get_db()
            dbconn.query(db.Users).filter(db.Users.id == uid).update({'status': status})
            dbconn.commit()
            flash('Users updated successfully.', 'success')

        except:
            flash('Permission denied.', 'error')

        return redirect(url_for('list_users'))

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
        user_plugins = []
        if request.args.get('id'):
            user = dbconn.query(db.Users).filter(db.Users.id == request.args.get('id'))
            userdata = user.first()
            createuser = form.CreateUserForm(username=userdata.password, password=userdata.password, confirm=userdata.password,
                                             role=userdata.role, status=userdata.status)
            user_plugins = userdata.plugins
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

        metadata = {
            'info': {
                'title': 'Create User',
                'class': 'col-md-5',
                'body_class': None,
                'type': None,
                'footer': '<button type="Create" class="btn btn-primary" frmtarget="#form_register_user">Save user</button>'
            },
            'form_data': {
                'form_id': 'form_register_user',
                'form': createuser,
                'method': 'POST',
                'encryption': None,
                'extra': None
            }
        }

        return render_template('create_user.html', metadata=metadata, plugins=user_plugins)

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

                return redirect(url_for('home'))

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
            dbconn.query(db.Users).filter(db.Users.id == session['user_id']).update({'password': myaccount.confirm.data})
            dbconn.commit()
            flash('Password updated successfully.', 'success')
            return redirect(url_for('logout'))

        metadata = {
            'info': {
                'title': 'Create new user',
                'class': 'col-md-12',
                'body_class': None,
                'type': None,
                'footer': '<button type="Create" class="btn btn-primary" frmtarget="#form_change_password">Change Password</button>'
            },
            'form_data': {
                'form_id': 'form_change_password',
                'form': myaccount,
                'method': 'POST',
                'encryption': None,
                'extra': None
            }
        }

        return render_template('myaccount.html', metadata=metadata, token=securetoken())

    @app.route('/logout')
    @authorize
    def logout():
        session.pop('user_id', None)
        session.pop('username', None)
        session.pop('password', None)
        session.pop('role', None)
        session.pop('status', None)

        return redirect(url_for('login'))

    @app.route('/form-builder/<string:action>/<int:fid>/<string:child_action>/<int:cid>', methods=['GET', 'POST'])
    @app.route('/form-builder/<string:action>/<int:fid>', methods=['GET', 'POST'])
    @app.route('/form-builder', methods=['GET', 'POST'])
    @authorize
    def form_builder(action=None, fid=None, child_action=None, cid=None):
        dbconn = db.get_db()
        if action == 'open':
            if fid:
                field_reff = dbconn.query(db.Form_reference).filter(db.Form_reference.id == fid and db.db.Form_reference.author_id == session['user_id']).first()
                if field_reff:
                    if child_action == 'delete' and cid:
                        child_field = dbconn.query(db.Form_reference_fields).get(cid)

                        if child_field is None:
                            flash('Permission denied.', 'error')
                            return redirect(url_for('form_builder'))
                        
                        dbconn.delete(child_field)
                        dbconn.commit()
                        return redirect(url_for('form_builder', action='open', fid=fid))

                    elif child_action == 'edit' and cid:
                        child_field = dbconn.query(db.Form_reference_fields).get(cid)
                        
                        if child_field is None:
                            flash('Permission denied.', 'error')
                            return redirect(url_for('form_builder'))
                        
                        formbuilder_fields = form.FormBuilderFields(
                            name=child_field.name,
                            title=child_field.title,
                            type=child_field.type,
                            weight=child_field.weight,
                            choiced=child_field.choiced,
                            required=child_field.required
                        )

                    else:
                        formbuilder_fields = form.FormBuilderFields()

                    if formbuilder_fields.validate_on_submit():
                        if child_action == 'edit' and cid:
                            child_field = dbconn.query(db.Form_reference_fields).filter(db.Form_reference_fields.id == cid)
                            child_field.update({
                                'name': formbuilder_fields.name.data,
                                'title': formbuilder_fields.title.data,
                                'type': formbuilder_fields.type.data,
                                'weight': formbuilder_fields.weight.data,
                                'choiced': formbuilder_fields.choiced.data,
                                'required': formbuilder_fields.required.data
                            })
                            dbconn.commit()

                        else:
                            field_reff_field = db.Form_reference_fields(
                                fid=fid,
                                name=formbuilder_fields.name.data,
                                title=formbuilder_fields.title.data,
                                type=formbuilder_fields.type.data,
                                weight=formbuilder_fields.weight.data,
                                choiced=formbuilder_fields.choiced.data,
                                required=formbuilder_fields.required.data
                            )
                            dbconn.add(field_reff_field)
                            dbconn.commit()

                        return redirect(url_for('form_builder', action=action, fid=fid))

                    metadata = {
                        'info': {
                            'title': 'Save field',
                            'class': 'col-md-3',
                            'body_class': None,
                            'type': None,
                            'footer': '<button class="btn btn-primary" frmtarget="#form_field_reff_fields">Save Field</button>'
                        },
                        'form_data': {
                            'form_id': 'form_field_reff_fields',
                            'form': formbuilder_fields,
                            'method': 'POST',
                            'encryption': None,
                            'extra': {
                                'choiced': '<div id="choiced-editor"></div>'
                            }
                        }
                    }

                    return render_template('form_builder_fields.html', metadata=metadata, action=action, field_reff_fields=field_reff)

                else:
                    flash('Permission denied.', 'error')
                    return redirect(url_for('form_builder'))

        elif action == 'edit':
            if fid:
                field_reff_conn = dbconn.query(db.Form_reference).filter(db.Form_reference.id == fid and db.Form_reference.author_id == session['user_id'])
                field_reff = field_reff_conn.first()

                if field_reff is None:
                    flash('Permission denied.', 'error')
                    return redirect(url_for('form_builder'))

                formbuilder = form.FormBuilder(name=field_reff.name, callback=field_reff.callback, method=field_reff.method, enctype=field_reff.enctype)
                collections = dbconn.query(db.Form_reference).all()
                if formbuilder.validate_on_submit():
                    field_reff_conn.update({'name': formbuilder.name.data, 'callback': formbuilder.callback.data, 'method': formbuilder.method.data, 'enctype': formbuilder.enctype.data})
                    dbconn.commit()
                    return redirect(url_for('form_builder'))

                metadata = {
                    'info': {
                        'title': 'Form Builder',
                        'class': 'col-md-3',
                        'body_class': None,
                        'type': None,
                        'footer': '<button class="btn btn-primary" frmtarget="#form_field_reff">Save Form</button>'
                    },
                    'form_data': {
                        'form_id': 'form_field_reff',
                        'form': formbuilder,
                        'method': 'POST',
                        'encryption': None,
                        'extra': None
                    }
                }

                return render_template('form_builder.html', metadata=metadata, action=action, fid=fid, collections=collections)

        elif action == 'delete':
            if fid:
                field_reff = dbconn.query(db.Form_reference).get(fid)

                if field_reff is None:
                    flash('Permission denied.', 'error')
                    return redirect(url_for('form_builder'))

                dbconn.delete(field_reff)
                dbconn.commit()

            return redirect(url_for('form_builder'))

        else:
            formbuilder = form.FormBuilder()
            collections = dbconn.query(db.Form_reference).all()
            if formbuilder.validate_on_submit():
                field_reff = db.Form_reference(author_id=session['user_id'], name=formbuilder.name.data, callback=formbuilder.callback.data, method=formbuilder.method.data, enctype=formbuilder.enctype.data)
                dbconn.add(field_reff)
                dbconn.commit()
                dbconn.refresh(field_reff)
                return redirect(url_for('form_builder'))

            metadata = {
                'info': {
                    'title': 'Form Builder',
                    'class': 'col-md-3',
                    'body_class': None,
                    'type': None,
                    'footer': '<button class="btn btn-primary" frmtarget="#form_field_reff">Save Form</button>'
                },
                'form_data': {
                    'form_id': 'form_field_reff',
                    'form': formbuilder,
                    'method': 'POST',
                    'encryption': None,
                    'extra': None
                }
            }

            return render_template('form_builder.html', metadata=metadata, collections=collections)

    @app.errorhandler(404)
    def page_not_found(error_code):
        return render_template('404.html')

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('500.html', error=error)

    @app.before_request
    def before_request():
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

    @app.context_processor
    def context():
        def form_builder(id):
            dbconn = db.get_db()
            fields = dbconn.query(db.Form_reference).get(id)
            record_count = dbconn.query(db.Form_reference_fields).filter(db.Form_reference_fields.fid == id).count()

            class FormBuilderForm(FlaskForm):
                pass

            if fields:
                for field in fields.form_reference_fields:
                    if field.type == 'StringField':
                        setattr(FormBuilderForm, field.name, StringField(field.title, [validators.DataRequired()]))

                    elif field.type == 'SelectField':
                        setattr(FormBuilderForm, field.name, SelectField(field.title, [validators.DataRequired()], choices=literal_eval(field.choiced)))

                    elif field.type == 'IntegerField':
                        setattr(FormBuilderForm, field.name, IntegerField(field.title, [validators.DataRequired()]))

                    elif field.type == 'SelectMultipleField':
                        setattr(FormBuilderForm, field.name, SelectMultipleField(field.title, [validators.DataRequired()], choices=literal_eval(field.choiced)))

                    elif field.type == 'TextAreaField':
                        setattr(FormBuilderForm, field.name, TextAreaField(field.title, [validators.DataRequired()]))

                    elif field.type == 'BooleanField':
                        setattr(FormBuilderForm, field.name, BooleanField(field.title, [validators.DataRequired()]))

                    elif field.type == 'FileField':
                        setattr(FormBuilderForm, field.name, FileField(field.title, [validators.DataRequired()]))

                    elif field.type == 'SubmitField':
                        setattr(FormBuilderForm, field.name, SubmitField(field.title, [validators.DataRequired()]))

                    elif field.type == 'FloatField':
                        setattr(FormBuilderForm, field.name, FloatField(field.title, [validators.DataRequired()]))

                    elif field.type == 'DecimalField':
                        setattr(FormBuilderForm, field.name, DecimalField(field.title, [validators.DataRequired()]))

                    elif field.type == 'RadioField':
                        setattr(FormBuilderForm, field.name, RadioField(field.title, [validators.DataRequired()]))

                    elif field.type == 'HiddenField':
                        setattr(FormBuilderForm, field.name, HiddenField(field.title, [validators.DataRequired()]))

                    elif field.type == 'PasswordField':
                        setattr(FormBuilderForm, field.name, PasswordField(field.title, [validators.DataRequired()]))

            dform = FormBuilderForm()
            return dict(info=fields, elements=dform, count=record_count)

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
        site_context['build'] = form_builder

        return site_context

    app.cli.add_command(start_server)
    app.cli.add_command(gui)
    return app


class AppReloader(object):
    def __init__(self, gorilla_app):
        self.gorilla_app = gorilla_app
        self.app = gorilla_app()

    def get_application(self):
        global plugins_context_rebuild
        if plugins_context_rebuild:
            self.app = self.gorilla_app()
            plugins_context_rebuild = False

        return self.app

    def __call__(self, environ, start_response):
        app = self.get_application()
        return app(environ, start_response)


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    os.environ['FLASK_ENV'] = 'production'


@click.command('start-forever')
def start_server():
    application = AppReloader(create_app)
    run_simple('localhost', 5000, application, use_reloader=False, use_debugger=True)


@click.command('gui')
def gui():
    application = AppReloader(create_app)
    threading.Thread(target=run_simple, args=('localhost', 5000, application, False, True), daemon=True).start()

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    MainWindow.setMinimumSize(1052, 799)
    MainWindow.showMaximized()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())