import os
from werkzeug.utils import secure_filename
from zipfile import ZipFile
from flask import current_app, session
from wtforms import TextField, validators, ValidationError
from flask_wtf import FlaskForm, file
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()


def plugin_validate(form, field):
    uploaded_file = field.data
    filename = secure_filename(uploaded_file.filename)
    parse_file_name = filename.split('.')
    user_folder = os.path.join(current_app.config['PLUGIN_UPLOAD_FOLDER'], session['username'])
    
    if os.path.isdir(user_folder) == False:
        os.mkdir(user_folder)
    
    if os.path.isdir(os.path.join(user_folder, parse_file_name[0])):
        raise ValidationError('Plugin already exist. It should be unique for each upload')
    else:
        file_path = os.path.join(user_folder, filename)
        uploaded_file.save(file_path)

        with ZipFile(file_path, 'r') as zip:
            zip.extractall(user_folder)

        os.remove(file_path)

    if os.path.isdir(os.path.join(user_folder, parse_file_name[0])) == False:
        raise ValidationError('Plugin folder name insize zip file should be same as zip file name')


def register_plugin_validate(form, field):
    if os.path.isdir(field.data) == False:
        raise ValidationError('Plugin path does not exist')
    
    elif os.path.isdir(os.path.join(field.data, form.local_plugin_name.data)) == False:
        raise ValidationError('Plugin name does not exist inside your plugin path')


class PluginUploadForm(FlaskForm):
    upload = file.FileField('Choose your addon file',[file.FileRequired(), file.FileAllowed(['zip'], 'Zip file only!'), plugin_validate])


class RegisterLocalPluginForm(FlaskForm):
    local_plugin_name = TextField('Plugin Name', [validators.DataRequired()])
    local_plugin_path = TextField('Plugin Path', [validators.DataRequired(), register_plugin_validate])