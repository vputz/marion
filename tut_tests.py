#!venv/bin/python

import os
import shutil
import unittest

from config import basedir
import tutorial
from tutorial.models import User, Role
from tutorial.models import Gps_remap, Gps_cache
from tutorial.geocache import remap_has_key, cache_has_key, get_location, get_locations_and_unknowns
from io import BytesIO
from flask import g, current_app
from flask_security.utils import login_user, logout_user
from flask.ext.testing import TestCase
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import SQLAlchemyUserDatastore, current_user


class UserTest( TestCase) :

    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite://' #/' + os.path.join(basedir, 'test.db')
    STORAGE_BASEDIR = '/tmp'
    SECRET_KEY = "you-will-never-guess"

    _user_basedir = os.path.join( STORAGE_BASEDIR, 'user_1' )
    
    def create_app(self) :
        return tutorial.create_app( self )
    
    def setUp( self ) :
        self.user_datastore = SQLAlchemyUserDatastore(tutorial.db, User, Role )
        tutorial.db.create_all()
        #u = User( nickname='test1', email='test1@test.com' )
        self.user = self.user_datastore.create_user( nickname = 'test1', email='test1@test.com', password='password' )
        tutorial.db.session.add(self.user)
        tutorial.db.session.commit()
        # must commit before ID exists
        self.first_id = self.user.id

    def get_user( self ) :
        return User.query.get(1)
        
    def _login( self, email = "test1@test.com", password="password") :
        data = { 'email' : email,
                 'password' : password,
                 'remember' : 'y' }
        #print( "login: " + str(current_user) )
        rv= self.client.post('/login', data=data, follow_redirects=True )
        #print(rv)
        #print( rv.data )
        #u = User.query.get( self.first_id )
        #login_user(u)

    def _logout( self ) :
        logout_user()
        
    def tearDown( self ) :
        self._logout()
        tutorial.db.session.remove()
        tutorial.db.drop_all()
        self.clear_test_data_directory()

    def test_create_user( self ) :
        u = User.query.get( self.first_id )
        self.assertEqual( u.nickname, 'test1' )

    def test_query_user( self ) :
        rv = self.client.get('/api/1.0/users/1')
        self.assertEqual( rv.json['nickname'], 'test1' )

    def fileContents( self, filename ) :
        result = ""
        with open(filename, 'r') as f :
            result = f.read()
        return result
        
    def test_upload_form( self ) :

        self._login()
        rv = self.client.post('/upload_file/', buffered=True,
                           content_type='multipart/form-data',
                           data={
                               'file_1' : (BytesIO(b'Hello, World!'), 'test.txt')
                           }, follow_redirects=True)
        # check to see if the file is there
        filename = os.path.join(self._user_basedir, 'test.txt' )
        self.assertTrue(os.path.isfile( filename ))
        self.assertEqual( self.fileContents( filename ), "Hello, World!" )

    def test_upload_api( self ) :

        self._login()
        rv = self.client.post('/api/1.0/upload', buffered=True,
                           content_type='multipart/form-data',
                           data={
                               'files' : (BytesIO(b'Hello, World!'), 'test.txt')
                           }, follow_redirects=True)
        # check to see if the file is there
        filename = os.path.join(self._user_basedir, 'test.txt' )
        self.assertTrue(os.path.isfile( filename ))
        self.assertEqual( self.fileContents( filename ), "Hello, World!" )
        self._logout()

    def clear_test_data_directory( self ) :
        if os.path.exists( self._user_basedir ) :
            shutil.rmtree( self._user_basedir )
        
    dataset_description = "Description"
    dataset_query = "Query"
        
    def add_basic_dataset( self ) :
        rv = self.client.post("/add_dataset/", buffered=True,
                              data= { 'descriptionField' : self.dataset_description,
                                      'queryField' : self.dataset_query },
                              follow_redirects = True )
        
    def test_add_dataset_form( self ) :
        self._login()
        u = self.get_user()
        self.add_basic_dataset()
        self.assertEqual( len(list(u.datasets)), 1 )
        self.assertEqual( u.datasets[0].description, self.dataset_description )
        self.assertEqual( u.datasets[0].query_text, self.dataset_query )

    def add_tabfiles( self, dataset_id, filename ) :
        with open( os.path.join( 'test_data', filename ), 'rb' ) as f1 :
            rv = self.client.post("/edit_dataset/"+str(dataset_id), buffered=True,
                                  data = { 'file_1' : (f1, filename ) },
                                  follow_redirects = True)
            f1.close()
            print( rv )
        
    def test_dataset_h5_up_to_date( self ) :
        self._login()
        u = self.get_user()
        self.add_basic_dataset()
        d = u.datasets[0]
        self.add_tabfiles( d.id, 'metamaterials_1.tab' )
        self.assertEqual( len(list(d.csv_files)), 1 )
        self.assertEqual( d.h5_file_is_up_to_date(), False )
        self.client.post('/regenerate_h5/'+str(d.id) )
        self.assertEqual( d.h5_file_is_up_to_date(), True )
        self.add_tabfiles( d.id, 'metamaterials_2.tab' )
        self.assertEqual( len(list(d.csv_files)), 2 )
        self.assertEqual( d.h5_file_is_up_to_date(), False )
        self.client.post('/regenerate_h5/'+str(d.id) )
        self.assertEqual( d.h5_file_is_up_to_date(), True )
        
class GPSTest( TestCase) :

    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite://' #/' + os.path.join(basedir, 'test.db')
    SQLALCHEMY_BINDS =  { 
        'gps_cache' : 'sqlite:///' + os.path.join( basedir, 'test_gps_cache.db' )
    }
    STORAGE_BASEDIR = '/tmp'
    SECRET_KEY = "you-will-never-guess"

    _user_basedir = os.path.join( STORAGE_BASEDIR, 'user_1' )
    
    def create_app(self) :
        return tutorial.create_app( self )

    def setUp( self ) :
        self.user_datastore = SQLAlchemyUserDatastore(tutorial.db, User, Role )
        tutorial.db.create_all()
        #u = User( nickname='test1', email='test1@test.com' )
        self.remap_from = "University of Oxford"
        self.remap_to = "Oxford, United Kingdom"
        self.cache_loc = "Oxford, United Kingdom"
        self.cache_lat = 51.7519
        self.cache_lon = -1.2578
        
        self.user = self.user_datastore.create_user( nickname = 'test1', email='test1@test.com', password='password' )
        tutorial.db.session.add(self.user)
        tutorial.db.session.commit()

        oxford_remap = Gps_remap( from_location=self.remap_from, to_location = self.remap_to )
        tutorial.db.session.add(oxford_remap)

        oxford_lookup = Gps_cache( location = self.cache_loc, latitude = self.cache_lat, longitude = self.cache_lon )
        tutorial.db.session.add( oxford_lookup )

        tutorial.db.session.commit()

    def _logout( self ) :
        logout_user()

    def tearDown( self ) :
        self._logout()
        tutorial.db.session.remove()
        tutorial.db.drop_all()

    def test_retrieval( self ) :
        remap = Gps_remap.query.get( self.remap_from )
        self.assertEqual( remap.from_location, self.remap_from )

        cache = Gps_cache.query.get( self.cache_loc )
        self.assertAlmostEqual( cache.latitude, self.cache_lat )
        self.assertAlmostEqual( cache.longitude, self.cache_lon )

    def test_has_keys( self ) :
        self.assertAlmostEqual( remap_has_key( self.remap_from ), True )
        self.assertAlmostEqual( cache_has_key( self.cache_loc ), True )

    def test_get_location( self ) :
        self.assertEqual( get_location( "blorfing" ), None )
        self.assertAlmostEqual( get_location( self.cache_loc )['lat'], self.cache_lat )
        self.assertAlmostEqual( get_location( "london" )['lon'], -0.1277583 )

    def test_get_locations_and_unknowns( self ) :
        locs, unks = get_locations_and_unknowns( ["University of Oxford", "blorfing"] )
        self.assertAlmostEqual( locs["University of Oxford"]['lon'], self.cache_lon )
        self.assertEqual( unks[0], "blorfing" )

from biblio import wos_reader
        
class BiblioTest( TestCase ):
    """
    Test the bibliometrics functions
    """
    
    def create_app(self) :
        return tutorial.create_app( self )

    def setUp( self ):
        """
        """

    def tearDown( self ):
        """
        """

    def test_dict_from_addresses( self ) :
        s1 = "[ Author, A A.; Author, A B.] Univ A"
        d = wos_reader.dict_from_addresses( s1 )
        self.assertTrue( 'Author, A A.' in d )
        self.assertEqual( d['Author, A A.'], "Univ A" )
        s2 = "[Author, A A.; Author, A B.] Univ A; [Author, A C.] Univ B"
        d = wos_reader.dict_from_addresses( s2 )
        self.assertTrue( 'Author, A A.' in d )
        self.assertTrue( 'Author, A B.' in d )
        self.assertTrue( 'Author, A C.' in d )
        self.assertEqual( d['Author, A C.'], 'Univ B' )
                        
if __name__ == "__main__" :
    unittest.main()
    
        
        
        
