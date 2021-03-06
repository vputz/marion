#!venv/bin/python

import os
import shutil
import unittest
import numpy
from config import basedir
import tutorial
from tutorial.models import User, Role
from tutorial.models import Gps_remap, Gps_cache
from tutorial.geocache import remap_has_key, cache_has_key, get_location, get_locations_and_unknowns, get_locations_and_unknowns_nocache
from io import BytesIO
from flask import g, current_app
from flask_security.utils import login_user, logout_user
from flask.ext.testing import TestCase
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import SQLAlchemyUserDatastore, current_user
from flask.ext.bower import Bower

class MarionTest( TestCase ) :
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite://' #/' + os.path.join(basedir, 'test.db')
    SQLALCHEMY_BINDS =  { 
        'gps_cache' : 'sqlite:///' + os.path.join( "/tmp", 'test_gps_cache.db' )
    }
    STORAGE_BASEDIR = '/tmp'
    SECRET_KEY = "you-will-never-guess"
    PRESERVE_CONTEXT_ON_EXCEPTION=False

    _user_basedir = os.path.join( STORAGE_BASEDIR, 'user_1' )
    
    def create_app(self) :
        result = tutorial.create_app( self )
        Bower(result)
        return result

class UserTest( MarionTest ) :

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
                           }, follow_redirects=True )
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
        
        
from marion_biblio import wos_reader, wos_reader_query
        
class BiblioTest( MarionTest ):
    """
    Test the bibliometrics functions
    """
    def setUp( self ):
        """
        """
        self.w5 = wos_reader.Wos_h5_reader( "test_data/putz.h5" )

    def tearDown( self ):
        """
        """
        self.w5.h5.close()

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

    def test_paper_location_query( self ):
        """
        """
        locresults = wos_reader_query.paperLocationQuery( self.w5 )
        self.assertDictEqual( locresults, {b'10.1039/c0sm00164c': {b'Univ Oxford, Rudolf Peierls Ctr Theoret Phys, Oxford OX1 3NP, England'}, b'10.1140/epjst/e2010-01278-y': {b'Univ Oxford, Rudolf Peierls Ctr Theoret Phys, Oxford OX1 3NP, England'}, b'10.1016/j.chemphys.2010.04.025': {b'Univ Oxford, Rudolf Peierls Ctr Theoret Phys, Oxford OX1 3NP, England'}, b'10.1007/s10955-009-9826-x': {b'Univ Oxford, Rudolf Peierls Ctr Theoret Phys, Oxford OX1 3NP, England'}} )


        
class CountryCollaborationQueryTest(MarionTest):
    """
    Test the CountryCollaborationQuery code using Irwin's test set
    """
        
    def create_app(self) :
        result = tutorial.create_app( self )
        Bower(result)
        return result


    def setUp( self ) :
        self.w5 = wos_reader.Wos_h5_reader( "test_data/irwin.h5" )

    def tearDown(self):
        """
        
        Arguments:
        - `self`:
        """
        self.w5.h5.close()

    def test_country_index( self ) :
        k = wos_reader_query.countryIndex( self.w5 )
        self.assertEqual( k, ['Denmark', 'Egypt', 'England', 'Finland', 'Germany', 'Japan', 'Ukraine'] )

    def testCountryCollaborationQuery( self ) :
        queryResult = wos_reader_query.countryCollaborationQuery( self.w5 )
        m = queryResult['matrix']
        self.assertEqual( (m == numpy.array( [[ 0,0.,1,1,1,0,1],
                                           [ 0,0,0,0,0,0,0 ],
                                           [ 1,0,0,1,1,2,1 ],
                                           [ 1,0,1,0,1,0,1 ],
                                           [ 1,0,1,1,0,0,1 ],
                                           [ 0,0,2,0,0,0,0 ],
                                           [ 1,0,1,1,1,0,0 ]])).all(), True )

                        
if __name__ == "__main__" :
    unittest.main()
    
        
        
        
