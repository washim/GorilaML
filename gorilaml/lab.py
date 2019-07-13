import importlib
import sys
import base64
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
                    session['username'] = getuser['username']
                    session['password'] = getuser['password']
                    return fun(*args, **kws)
            else:
                flash('Login expired. Please login again.','error')
                return redirect(url_for('login'))
        else:
            return fun(*args, **kws)
        
    return wrapper

class contribaddons:
    def __init__(self, instance, alladdons):
        self.instance = instance
        self.alladdons = alladdons
        sys.path.append(self.instance)
    
    def getAddons(self):
        addons = {}
        for addon in self.alladdons:
            try:
                addons_libs = importlib.import_module('addons.%s.%s.api' % ('admin',addon['name']))
                addons[addon['name']] = getattr(addons_libs, 'gorilaml')
            except:
                pass

        return addons