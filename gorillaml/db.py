import click
from flask import g, current_app
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
    role = Column('role', String, nullable=False)
    status = Column('status', String, nullable=False)
    created = Column('created', Date, nullable=False, default=datetime.now)
    plugins = relationship('Plugins', back_populates='user')
    form_reference = relationship('Form_reference', back_populates='user')

    def __repr__(self):
        return f"<Users(username='{self.username}', password='{self.password}', role='{self.role}')>"


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


class Configs(Base):
    __tablename__ = 'configs'
    id = Column(Integer, primary_key=True)
    key = Column('key', String, nullable=False, unique=True)
    value = Column('value', String, nullable=False)

    def __repr__(self):
        return f"<Configs(key='{self.key}', value='{self.value}')>"


class Form_reference(Base):
    __tablename__ = 'form_reference'
    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('users.id'))
    name = Column('name', String, nullable=False)
    callback = Column('callback', String, nullable=False)
    method = Column('method', String, nullable=False)
    enctype = Column('enctype', String, nullable=True)
    user = relationship('Users', back_populates='form_reference')
    form_reference_fields = relationship('Form_reference_fields', back_populates='form_references', order_by='Form_reference_fields.weight', cascade='save-update, merge, delete')

    def __repr__(self):
        return f"<Form_reference(name='{self.name}')>"


class Form_reference_fields(Base):
    __tablename__ = 'form_reference_fields'
    id = Column(Integer, primary_key=True)
    fid = Column(Integer, ForeignKey('form_reference.id'))
    name = Column('name', String, nullable=False)
    title = Column('title', String, nullable=False)
    type = Column('type', String, nullable=False)
    choiced = Column('choiced', String, nullable=True)
    weight = Column('weight', Integer, nullable=False)
    required = Column('required', String, nullable=False)
    form_references = relationship('Form_reference', back_populates='form_reference_fields')

    def __repr__(self):
        return f"<Form_reference_fields(name='{self.name}', type='{self.type}')>"


def get_db():
    if 'db' not in g:
        engine = create_engine(f"sqlite:///{current_app.instance_path}/{__name__}.sqlite")
        dbsession = sessionmaker(bind=engine)
        g.db = dbsession()

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    engine = create_engine(f"sqlite:///{current_app.instance_path}/{__name__}.sqlite")
    Base.metadata.create_all(engine)

    dbsession = sessionmaker(bind=engine)
    session = dbsession()
    admin = Users(username='admin', password='admin', role='admin', status='enabled')
    session.add(admin)
    session.add(Configs(key='site_logo', value='logo.png'))
    session.add(Configs(key='site_name', value='GorillaML'))
    session.add(Configs(key='site_slogan', value='Gorilla Managed Lab'))
    session.add(Configs(key='page_title', value='Gorilla Managed Lab'))
    session.add(Configs(key='copyrights', value='yes'))
    session.add(Configs(key='available_version', value=current_app.config['VERSION']))
    session.add(Configs(key='available_version_check_date', value=datetime.today()))
    session.commit()
    session.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Initialized the database.')