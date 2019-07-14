import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    db = get_db()
    cur = db.execute(query, args)
    if one:
        rv = cur.fetchone()
    else:
        rv = cur.fetchall()
    cur.close()
    
    return rv

def get_data(table, where_fields=(), where_values=(), one=False):
    db = get_db()
    query = 'SELECT * FROM %s' % table
    if len(where_fields) > 0:
        query += ' WHERE %s' % (' and '.join(['%s=?' % where_field for where_field in where_fields]))
    cur = db.execute(query, where_values)
    if one:
        rv = cur.fetchone()
    else:
        rv = cur.fetchall()
    cur.close()

    return rv

def insert_db(table, fields=(), values=()):
    db = get_db()
    query = 'INSERT INTO %s (%s) VALUES (%s)' % (
        table,
        ', '.join(fields),
        ', '.join(['?'] * len(values))
    )
    cur = db.execute(query, values)
    db.commit()
    id = cur.lastrowid
    cur.close()
    
    return id

def update_db(table, fields=(), values=(), where_fields=(), where_values=()):
    db = get_db()
    query = 'UPDATE %s SET %s WHERE %s' % (
        table,
        ','.join(['%s=?' % field for field in fields]),
        ' and '.join(['%s=?' % where_field for where_field in where_fields])
    )
    cur = db.execute(query, values+where_values)
    db.commit()
    id = cur.rowcount
    cur.close()
    
    return id

def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    
    db.commit()

@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)