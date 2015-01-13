from flask import Flask, request, current_app

from flask.ext.login import LoginManager
from flask.ext.security import Security, SQLAlchemyUserDatastore, login_required

from tutorial.views import tutorial_bp

from tutorial.api import api
from tutorial.models import User, Role, db
user_datastore = SQLAlchemyUserDatastore(db, User, Role )
lm = LoginManager()
security = Security()

import local_conf

def create_app( config_object ) :
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.debug = False
    db.init_app(app)
    api.init_app(app)
    lm.init_app(app)
    security.init_app( app, user_datastore )
    app.register_blueprint( tutorial_bp )

    if not app.debug :
        import logging
        from logging import FileHandler
        handler = FileHandler(local_conf.logfile)
        handler.setLevel( logging.WARNING )
        app.logger.addHandler(handler)
    return app



app = create_app('config')

#lm.login_view = 'login'


