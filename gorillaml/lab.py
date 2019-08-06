import base64
import requests
import io
from functools import wraps
from flask import (
    session, flash, redirect, url_for, request, current_app
)
from gorillaml import db
from bs4 import BeautifulSoup
from datetime import datetime


def authorize(fun):
    @wraps(fun)
    def wrapper(*args, **kws):
        if 'username' not in session:
            if request.args.get('token'):
                dbconn = db.get_db()
                try:
                    token_string = base64.b64decode(request.args.get('token')).decode('utf-8').split(':')
                except:
                    return redirect(url_for('logout'))

                getuser = dbconn.query(db.Users).filter(db.Users.username == token_string[1] and db.Users.password == token_string[2]).first()
                if getuser is None:
                    flash('Login expired. Please login again.','error')
                    return redirect(url_for('login'))
                else:
                    session['user_id'] = getuser.id
                    session['username'] = getuser.username
                    session['password'] = getuser.password
                    session['role'] = getuser.role
                    session['status'] = getuser.status

                    return fun(*args, **kws)
            else:
                flash('Login expired. Please login again.','error')
                return redirect(url_for('login'))
        else:
            return fun(*args, **kws)
        
    return wrapper


def admin_login_required(fun):
    @wraps(fun)
    def wrapper(*args, **kws):
        if session.get('username'):
            if session.get('role') == 'admin':
                return fun(*args, **kws)
            else:
                flash('You dont have enough permissions to open this page.', 'error')
                return redirect(url_for('plugins'))
        else:
            return fun(*args, **kws)

    return wrapper


def securetoken():
    return base64.b64encode((str(session['user_id'])+':'+session['username']+':'+session['password']).encode())


def fig_to_html(figure, size=100):
    buffer = io.BytesIO()
    figure.savefig(buffer, format='png')
    buffer.seek(0)
    raw_data = base64.b64encode(buffer.read()).decode('utf-8')
    image = f'<image width="{size}%" src="data:image/png;base64,{raw_data}"/>'

    return image


def check_new_version():
    dbconn = db.get_db()
    pypi = requests.get('https://pypi.org/project/gorillaml/', timeout=5)
    soup = BeautifulSoup(pypi.text, 'html.parser')
    dbconn.query(db.Configs).filter(db.Configs.key == 'available_version').update({'value': soup.h1.string.split(' ')[1]})
    dbconn.query(db.Configs).filter(db.Configs.key == 'available_version_check_date').update({'value': datetime.today()})