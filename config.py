# used to configure flask extensions
import os

basedir=os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_BINDS = {
    'gps_cache' : 'sqlite:///' + os.path.join( basedir, 'gps_cache.db' )
    }
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
STORAGE_BASEDIR = os.path.join(basedir, "user_storage")
QUERIES_BASEDIR = os.path.join(basedir, "tutorial/wos_queries" )

#required for forms
WTF_CSRF_ENABLE = True
SECRET_KEY = "you-will-never-guess"
#OPENID_PROVIDERS = [
#    {'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id'},
#    {'name': 'Yahoo', 'url': 'https://me.yahoo.com'},
#    {'name': 'AOL', 'url': 'http://openid.aol.com/<username>'},
#    {'name': 'Flickr', 'url': 'http://www.flickr.com/<username>'},
#    {'name': 'MyOpenID', 'url': 'https://www.myopenid.com'}]

SECURITY_REGISTERABLE = True
# currently no email provider
SECURITY_SEND_REGISTER_EMAIL = False
SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False
