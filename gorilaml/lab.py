import importlib
import sys
import base64
import os
from functools import wraps
from flask import (
    session, flash, redirect, url_for, request, g
)
from gorilaml import db

def authorize(fun):
    @wraps(fun)
    def wrapper(*args, **kws):
        if 'username' not in session:
            if request.args.get('token'):
                token_string = base64.b64decode(request.args.get('token')).decode('utf-8').split(':')
                getuser = db.query_db('SELECT * FROM user WHERE username=? and password=?', (token_string[0], token_string[1]), True)
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

def getplugins(app):
    with app.app_context():
        allplugins = db.query_db('SELECT t1.*,t2.username FROM plugins t1 join user t2 ON t1.author_id=t2.id WHERE t1.status=1')
    
    plugin_dict = {}
    for plugin in allplugins:
        try:
            plugin_libs = importlib.import_module('addons.%s.%s.api' % (addon['username'], addon['name']))
            plugin_dict[plugin['name']] = getattr(plugin_libs, 'gorilaml')
        except:
            pass

    return plugin_dict