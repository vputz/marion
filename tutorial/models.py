from flask import current_app
from flask.ext.security import Security, UserMixin, RoleMixin
import os
import werkzeug
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime
from biblio.wos_reader import open_wos_tab, make_pytable

db = SQLAlchemy()

roles_users = db.Table('roles_users',
                       db.Column('id_user', db.Integer(), db.ForeignKey('user.id') ),
                       db.Column('id_role', db.Integer(), db.ForeignKey('role.id') ) )

class Role( db.Model, RoleMixin ) :
    id = db.Column( db.Integer(), primary_key=True )
    name = db.Column( db. String(64), unique = True )
    description = db.Column( db.String(255) )

class User(db.Model, UserMixin ) :
    id = db.Column( db.Integer, primary_key=True )
    nickname = db.Column( db.String(64), index=True, unique=True )
    email = db.Column( db.String(128), index=True, unique=True )
    password = db.Column( db.String( 255 ) )
    active = db.Column( db.Boolean() )
    confirmed_at = db.Column( db.DateTime() )
    roles = db.relationship( 'Role', secondary=roles_users,
                             backref = db. backref('users', lazy='dynamic') )
    datasets = db.relationship("Dataset", backref='owner', lazy='dynamic')
    

    def storage_path( self ) :
        return os.path.join( current_app.config['STORAGE_BASEDIR'], 'user_'+str(self.id) )
    
    def is_authenticated( self ) :
        return True

    def is_active(self ) :
        return True

    def is_anonymous( self ) :
        return False

    def get_id(self) :
        try :
            return unicode( self.id )
        except NameError:
            return str(self.id)
    
    def __repr__(self) :
        return '<User %r (%r)>' % (self.nickname, self.email)

    def add_file( self, werkzeug_file ) :
        filename = werkzeug.secure_filename( werkzeug_file.filename )
        if not os.path.exists( self.storage_path() ):
            os.makedirs( self.storage_path() )
        werkzeug_file.save( os.path.join( self.storage_path(), filename ))

    def add_dataset( self, description, query_text ) :
        new_set = Dataset(description=description,
                          query_text=query_text,
                          owner=self,
                          date_created=datetime.utcnow() )
        db.session.add(new_set)
        db.session.commit()

class Dataset(db.Model) :
    id = db.Column( db.Integer, primary_key=True )
    id_user = db.Column( db.Integer, db.ForeignKey('user.id') )
    description = db.Column( db.String( 255 ) )
    query_text = db.Column( db.String( 1024 ) )
    date_created = db.Column( db.DateTime() )
    csv_files = db.relationship( "Csv_fileref", backref="dataset", lazy='dynamic' )
    h5_files = db.relationship( "H5_fileref", backref="dataset", lazy='dynamic' )

    def tab_storage_path( self ) :
        return os.path.join( self.owner.storage_path(), 'dataset_'+str(self.id),'tabs' )

    def h5_storage_path( self ) :
        return os.path.join( self.owner.storage_path(), 'dataset_'+str(self.id) )
        
    def add_csv( self, werkzeug_file ) :
        fileref = Csv_fileref( dataset=self, filename = werkzeug_file.filename )
        db.session.add( fileref )
        db.session.commit()
        if not os.path.exists( self.tab_storage_path() ) :
            os.makedirs( self.tab_storage_path() )
        werkzeug_file.save( fileref.stored_fullpath() )

    def regenerate_h5_file( self ) :
        if len(list(self.h5_files)) == 0 :
            h5 = H5_fileref( dataset=self )
            db.session.add(h5)
            db.session.commit()
        else :
            h5 = self.h5_files[0]
        tabfiles = [ tab.stored_fullpath() for tab in self.csv_files ]
        with open_wos_tab( tabfiles ) as wos :
            make_pytable( wos, h5.stored_fullpath(), self.description )

    def delete_missing_filerefs( self ) :
        # delete missing tabfiles
        csvfiles = list(self.csv_files)
        for tab in csvfiles :
            if not os.path.isfile( tab.stored_fullpath() ) :
                db.session.delete( tab )
                db.session.commit()

        # now same for h5
        h5files = list(self.h5_files)
        for h5 in h5files :
            if not os.path.isfile( tab.stored_fullpath() ) :
                db.session.delete(tab)
                db.session.commit()
            
    def h5_file_is_up_to_date( self ) :
        # if we don't have an h5, it's not up to date
        if len(list(self.h5_files)) == 0 :
            return False
        # if we do have one, check the dates of the files and make sure the H5 is
        # past that
        self.delete_missing_filerefs()
        if len(list(self.h5_files)) == 1 :
            h5 = self.h5_files[0]
            h5_date = os.path.getmtime( h5.stored_fullpath() )

            for csv in self.csv_files :
                #TODO trouble if files are wedged
                csv_date = os.path.getmtime( csv.stored_fullpath() )
                if csv_date > h5_date :
                    return False
        return True
        
        
        
        
class Csv_fileref(db.Model) :
    id = db.Column( db.Integer(), primary_key=True )
    id_dataset = db.Column( db.Integer, db.ForeignKey('dataset.id') )
    filename = db.Column( db.String( 1024 ) )

    def stored_filename( self ) :
        return "tab_" + str( self.id )

    def stored_fullpath( self ) :
        return os.path.join( self.dataset.tab_storage_path(), self.stored_filename() )
    
class H5_fileref( db.Model ) :
    id = db.Column( db.Integer(), primary_key=True )
    id_dataset = db.Column( db.Integer, db.ForeignKey('dataset.id') )
    filename = db.Column( db.String( 1024 ) )

    def stored_filename( self ) :
        return "h5_"+str(self.id)

    def stored_fullpath( self ) :
        return os.path.join( self.dataset.h5_storage_path(), self.stored_filename() )
