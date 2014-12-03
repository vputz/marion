#!venv/bin/python
from migrate.versioning import api
from config import SQLALCHEMY_DATABASE_URI
from config import SQLALCHEMY_MIGRATE_REPO
from tutorial import db, app
import os.path
from flask.ext.security import SQLAlchemyUserDatastore

from tutorial.models import User, Query, Role, Gps_remap, Gps_cache

def create_gps_cache() :
    db.create_all( bind = 'gps_cache' )
    

with app.app_context() :
    db.create_all()
    user_datastore = SQLAlchemyUserDatastore( db, User, Role )
    admin = user_datastore.create_user( nickname = "admin", email="vputz@nyx.net", password="marion" )
    db.session.add( admin )
    db.session.commit()
    
    # create queries
    q = Query( name = "Subject", description = "Analysis of a subject; most-published journals, authors, universities, countries", filename = "subject_query.json", template="subject_query.html" )
    db.session.add( q )
    db.session.commit()
    q = Query( name = "Country", description = "Analysis of a country; number of papers by subject, university, collaborating country", filename = "country_query.json", template="country_query.html" )
    db.session.add( q )
    db.session.commit()

    create_gps_cache()

    
    
if not os.path.exists(SQLALCHEMY_MIGRATE_REPO) :
    api.create( SQLALCHEMY_MIGRATE_REPO, 'database repository')
    api.version_control( SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
else :
    api.version_control( SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO, api.version( SQLALCHEMY_MIGRATE_REPO))

    
