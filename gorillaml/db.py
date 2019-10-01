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
    menus = relationship('Menus', back_populates='user')

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
    value = Column('value', String, nullable=True)

    def __repr__(self):
        return f"<Configs(key='{self.key}', value='{self.value}')>"


class Menus(Base):
    __tablename__ = 'menus'
    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('users.id'))
    icon = Column('icon', String, nullable=False)
    title = Column('title', String, nullable=False)
    weight = Column('weight', Integer, nullable=False)
    login_required = Column('login_required', String, nullable=False)
    created = Column('created', Date, nullable=False, default=datetime.now)
    user = relationship('Users', back_populates='menus')
    menu_items = relationship('Menu_items', back_populates='menu_items', order_by='Menu_items.weight', cascade='save-update, merge, delete')

    def __repr__(self):
        return f"<Menus(author_id='{self.author_id}', title='{self.title}', weight='{self.weight}')>"


class Menu_items(Base):
    __tablename__ = 'menu_items'
    id = Column(Integer, primary_key=True)
    mid = Column(Integer, ForeignKey('menus.id'))
    icon = Column('icon', String, nullable=False)
    title = Column('title', String, nullable=False)
    path = Column('path', String, nullable=False)
    weight = Column('weight', Integer, nullable=False)
    login_required = Column('login_required', String, nullable=False)
    menu_items = relationship('Menus', back_populates='menu_items')

    def __repr__(self):
        return f"<Menu_items(mid='{self.mid}', title='{self.title}', weight='{self.weight}')>"


class Form_reference(Base):
    __tablename__ = 'form_reference'
    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey('users.id'))
    name = Column('name', String, nullable=False)
    callback = Column('callback', String, nullable=False)
    method = Column('method', String, nullable=False)
    enctype = Column('enctype', String, nullable=True)
    created = Column('created', Date, nullable=False, default=datetime.now)
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
    session.add(Configs(key='login_redirect', value='/'))
    session.add(Configs(key='copyrights', value=''))
    session.add(Configs(key='available_version', value=current_app.config['VERSION']))
    session.add(Configs(key='available_version_check_date', value=datetime.today()))
    session.commit()
    session.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(db_update)


@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Initialized the database.')


@click.command('db-update')
@with_appcontext
def db_update():
    dbconn = get_db()
    sql_cmd = {}

    if len(sql_cmd) > 0:
        for ttl, cmd in sql_cmd.items():
            try:
                dbconn.execute(cmd)
                click.echo(ttl + ': success')

            except Exception:
                click.echo(ttl + ': not required')

    dbconn.query(Configs).filter(Configs.key == 'available_version').update({'value': current_app.config['VERSION']})
    dbconn.commit()

    click.echo('Database updation completed')