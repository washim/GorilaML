import click
from flask import g
from flask.cli import with_appcontext
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column('username', String, nullable=False, unique=True)
    password = Column('password', String, nullable=False)
    created = Column('created', Date, nullable=False, default=datetime.now)
    plugins = relationship('Plugins', back_populates='user')

    def __repr__(self):
        return f"<Users(username='{self.username}', password='{self.password}')>"


class Plugins(Base):
    __tablename__ = 'plugins'
    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('users.id'))
    name = Column('name', String, nullable=False)
    plugin_path = Column('plugin_path', String, nullable=False, default='system')
    status = Column('status', Integer, nullable=False, default=0)
    created = Column('created', Date, nullable=False, default=datetime.now)
    user = relationship('Users', back_populates='plugins')

    def __repr__(self):
        return f"<Plugins(name='{self.name}', plugin_path='{self.plugin_path}')>"


def get_db():
    if 'db' not in g:
        engine = create_engine(f"sqlite:///instance/{__name__}.sqlite")
        dbsession = sessionmaker(bind=engine)
        g.db = dbsession()

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    engine = create_engine(f"sqlite:///instance/{__name__}.sqlite")
    Base.metadata.create_all(engine)

    dbsession = sessionmaker(bind=engine)
    session = dbsession()
    admin = Users(username='admin', password='admin')
    session.add(admin)
    session.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Initialized the database.')