import base64
import os
import time
from functools import wraps
from flask import (
    session, flash, redirect, url_for, request
)
from gorilaml import db

def authorize(fun):
    @wraps(fun)
    def wrapper(*args, **kws):
        if 'username' not in session:
            if request.args.get('token'):
                token_string = base64.b64decode(request.args.get('token')).decode('utf-8').split(':')
                getuser = db.query_db('SELECT * FROM user WHERE username=? and password=?', (token_string[1], token_string[2]), True)
                if getuser is None:
                    flash('Login expired. Please login again.','error')
                    return redirect(url_for('login'))
                else:
                    session['user_id'] = getuser['id']
                    session['username'] = getuser['username']
                    session['password'] = getuser['password']
                    return fun(*args, **kws)
            else:
                flash('Login expired. Please login again.','error')
                return redirect(url_for('login'))
        else:
            return fun(*args, **kws)
        
    return wrapper

def securetoken():
    return base64.b64encode((str(session['user_id'])+':'+session['username']+':'+session['password']).encode())

def reload():
    fp = open('%s/reloader.py' % __name__, 'w+')
    fp.write("last_reloaded='%s'" % time.time())
    fp.close()