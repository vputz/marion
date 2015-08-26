#!venv/bin/python
from migrate.versioning import api
from local_conf import SQLALCHEMY_DATABASE_URI
from local_conf import SQLALCHEMY_MIGRATE_REPO
from tutorial import db, app
import os.path
from flask.ext.security import SQLAlchemyUserDatastore

from tutorial.models import User, Query, Role, Gps_remap, Gps_cache, Tabdata_query

print(SQLALCHEMY_MIGRATE_REPO)


def create_gps_cache() :
    db.create_all( bind = 'gps_cache' )
    
def replace_query( db, name, description, filename, template ):
    existing = Query.query.filter_by(name=name)
    for q in existing:
        db.session.delete(q)
    newq = Query(name=name, description=description, filename=filename, template=template)
    db.session.add(newq)
    db.session.commit()

def replace_tabdata_query(db, name, description, parameters, template):
    existing = Tabdata_query.query.filter_by(name=name)
    for q in existing:
        db.session.delete(q)
    newq = Tabdata_query(name=name, description=description, parameters=parameters, template=template)
    db.session.add(newq)
    db.session.commit()

with app.app_context() :
    db.create_all()
    db.session.commit()

    # create queries
    replace_query(db, name = "Subject", description = "Analysis of a subject; most-published journals, authors, universities, countries", filename = "subject_query.json", template="subject_query.html" )
    replace_query(db, name = "Country", description = "Analysis of a country; number of papers by subject, university, collaborating country", filename = "country_query.json", template="country_query.html" )
    replace_query(db, name = "Hexbin", description = "Hexbin-and-arcs display of papers in a dataset; keep sets small!", filename = "hexbin_query.json", template="hexbin_query.html" )

    # create tabdata queries
    replace_tabdata_query(db, name="Tabdata_hexbin", description="Hexbin of geographical data", parameters='{ "locationColumn" : 0, "valueColumn" : 0, "textColumn" : 0 }', template="tabdata_hexbin_query.html" )
    replace_tabdata_query(db, name="Tabdata_markercluster", description="Markercluster map of geographical data", parameters='{ "locationColumn" : 0, "valueColumn" : 0, "textColumn" : 0 }', template="tabdata_markercluster_query.html" )

        # create users
    user_datastore = SQLAlchemyUserDatastore( db, User, Role )
    if user_datastore.find_user(nickname="admin") is None :
        admin = user_datastore.create_user( nickname = "admin", email="vputz@nyx.net", password="marion" )
        db.session.add( admin )
        db.session.commit()

    create_gps_cache()

    
    
if not os.path.exists(SQLALCHEMY_MIGRATE_REPO) :
    api.create( SQLALCHEMY_MIGRATE_REPO, 'database repository')
    api.version_control( SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
else :
    api.version_control( SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO, api.version( SQLALCHEMY_MIGRATE_REPO))

    
