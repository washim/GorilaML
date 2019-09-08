import os
import shutil
from werkzeug.utils import secure_filename
from zipfile import ZipFile
from flask import current_app, session
from wtforms import StringField, PasswordField, SelectField, TextAreaField, SubmitField, validators, ValidationError
from wtforms.widgets import PasswordInput
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
        shutil.rmtree(os.path.join(user_folder, parse_file_name[0]), ignore_errors=True)

    file_path = os.path.join(user_folder, filename)
    uploaded_file.save(file_path)

    with ZipFile(file_path, 'r') as zip:
        zip.extractall(user_folder)

    os.remove(file_path)

    if os.path.isdir(os.path.join(user_folder, parse_file_name[0])) == False:
        raise ValidationError('Plugin folder name insize zip file should be same as zip file name')


def register_plugin_validate(form, field):
    if os.path.isdir(field.data) == False:
        raise ValidationError('Provide valid plugin path.')

def password_validate(form, field):
    if session['password'] != field.data:
        raise ValidationError('Current password does not match.')


class PluginUploadForm(FlaskForm):
    upload = file.FileField('Choose your addon file', [file.FileRequired(), file.FileAllowed(['zip'], 'Zip file only!'), plugin_validate])
    submit = SubmitField('Upload')


class RegisterLocalPluginForm(FlaskForm):
    local_plugin_path = StringField('Plugin Path', [validators.DataRequired(), register_plugin_validate])
    submit = SubmitField('Register')


class MyaccountForm(FlaskForm):
    current_password = PasswordField('Current Password', [validators.DataRequired(), password_validate])
    password = PasswordField('New Password', [validators.DataRequired(),
                                              validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [validators.DataRequired()])
    submit = SubmitField('Save')


class CreateUserForm(FlaskForm):
    username = StringField('Username', [validators.DataRequired()])
    password = PasswordField('New Password', [validators.DataRequired(),
                                              validators.EqualTo('confirm', message='Passwords must match')],
                             widget=PasswordInput(hide_value=False))
    confirm = PasswordField('Repeat Password', [validators.DataRequired()], widget=PasswordInput(hide_value=False))
    role = SelectField('User role', choices=[('developer', 'Developer'), ('admin', 'Administrator')])
    status = SelectField('Status', choices=[('enabled', 'Enable'), ('disabled', 'Disable')])
    submit = SubmitField('Save')


class RegisterSiteConfigForm(FlaskForm):
    site_name = StringField('Site name', [validators.DataRequired()])
    site_slogan = StringField('Site slogan', [validators.DataRequired()])
    site_logo = file.FileField('Site logo', [file.FileAllowed(['png', 'jpeg', 'jpg', 'gif'])])
    page_title = StringField('Page title', [validators.DataRequired()])
    copyrights = SelectField('Copyrights footer', choices=[('yes', 'Enabled'), ('no', 'Disabled')])
    submit = SubmitField('Save')

class FormBuilder(FlaskForm):
    name = StringField('Name', [validators.DataRequired()])
    callback = StringField('Callback', [validators.DataRequired()])
    method = SelectField('Method', choices=[('POST', 'POST'), ('GET', 'GET')])
    enctype = SelectField('Encryption', choices=[('normal', 'Normal'), ('multipart/form-data', 'File Upload')])
    submit = SubmitField('Save')

class FormBuilderFields(FlaskForm):
    name = StringField('Name', [validators.DataRequired()])
    title = StringField('Title', [validators.DataRequired()])
    type = SelectField('Type', choices=[
        ('StringField', 'StringField'),
        ('SelectField', 'SelectField'),
        ('IntegerField', 'IntegerField'),
        ('SelectMultipleField', 'SelectMultipleField'),
        ('TextAreaField', 'TextAreaField'),
        ('BooleanField', 'BooleanField'),
        ('FileField', 'FileField'),
        ('SubmitField', 'SubmitField'),
        ('FloatField', 'FloatField'),
        ('DecimalField', 'DecimalField'),
        ('RadioField', 'RadioField'),
        ('HiddenField', 'HiddenField'),
        ('PasswordField', 'PasswordField')
    ])
    weight = SelectField('Weight', choices=[(item, item) for item in range(-100, 100, 1)], coerce=int, default=0)
    choiced = TextAreaField('Choices', default="[('key', 'value'), ('key1', 'value1')]")
    required = SelectField('Required', choices=[('yes', 'Yes'), ('no', 'No')])
    submit = SubmitField('Save')

class FileManager(FlaskForm):
    content = TextAreaField('Content', [validators.DataRequired()])
    submit = SubmitField('Save')