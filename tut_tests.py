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

    """
    Tests both the GPS lookup and some biblio functions that rely on it
    """
    
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

    def test_paper_lat_lon_query(self):
        """
        """
        with wos_reader.open_wos_h5( "test_data/irwin.h5" ) as w5 :
            locresults = wos_reader_query.paperLatLonQuery( w5, get_locations_and_unknowns )
        tmp = self.maxDiff
        self.maxDiff = None
        irwin_network = {'not_located': ['Kyushu Univ, Dept Phys, Fukuoka 812, Japan', 'Natl Res Inst Astron & Geophys, Dept Astron, Cairo 11421, Egypt; Natl Res Inst Astron & Geophys, Kottamia Ctr Sci Excellence Astron & Space Sci KC, Cairo 11421, Egypt', 'Natl Res Inst Astron & Geophys, Dept Astron, Cairo 11421, Egypt'], 'paper_locations': {'10.1051/mmnp/20138208': {'edges': {0: {'to': 1, 'text': '10.1051/mmnp/20138208', 'from': 0, 'val': 0}, 1: {'to': 2, 'text': '10.1051/mmnp/20138208', 'from': 0, 'val': 0}, 2: {'to': 3, 'text': '10.1051/mmnp/20138208', 'from': 0, 'val': 0}, 3: {'to': 4, 'text': '10.1051/mmnp/20138208', 'from': 0, 'val': 0}, 4: {'to': 2, 'text': '10.1051/mmnp/20138208', 'from': 1, 'val': 0}, 5: {'to': 3, 'text': '10.1051/mmnp/20138208', 'from': 1, 'val': 0}, 6: {'to': 4, 'text': '10.1051/mmnp/20138208', 'from': 1, 'val': 0}, 7: {'to': 3, 'text': '10.1051/mmnp/20138208', 'from': 2, 'val': 0}, 8: {'to': 4, 'text': '10.1051/mmnp/20138208', 'from': 2, 'val': 0}, 9: {'to': 4, 'text': '10.1051/mmnp/20138208', 'from': 3, 'val': 0}}, 'nodes': {0: {'text': '10.1051/mmnp/20138208: Univ Southern Denmark, MEMPHYS Ctr Biomembrane Phys, Dept Phys Chem & Pharm, DK-5230 Odense M, Denmark', 'val': 0, 'lon': 10.4033399, 'lat': 55.37906169999999}, 1: {'text': '10.1051/mmnp/20138208: Univ Potsdam, Inst Phys & Astron, D-14476 Potsdam, Germany; Tech Univ Tampere, Dept Phys, FI-33101 Tampere, Finland', 'val': 0, 'lon': 23.7610254, 'lat': 61.4981508}, 2: {'text': '10.1051/mmnp/20138208: Univ Oxford, Rudolf Peierls Ctr Theoret Phys, Oxford OX1 3NP, England', 'val': 0, 'lon': -1.259116, 'lat': 51.7595933}, 3: {'text': '10.1051/mmnp/20138208: Inst Theoret Phys NSC KIPT, UA-61108 Kharkov, Ukraine; Max Planck Inst Phys Komplexer Syst, D-01187 Dresden, Germany', 'val': 0, 'lon': 13.7090684, 'lat': 51.0266014}, 4: {'text': '10.1051/mmnp/20138208: Humboldt Univ, Inst Phys, D-12489 Berlin, Germany', 'val': 0, 'lon': 13.5470509, 'lat': 52.4370179}}}}, 'failed_papers': ['', '10.1016/j.newast.2014.02.011']}
        self.assertEqual( locresults['paper_locations'].keys(), irwin_network['paper_locations'].keys() )
        self.assertEqual( set(locresults['failed_papers']), set(irwin_network['failed_papers']) )
        self.assertEqual( set(locresults['not_located']), set(irwin_network['not_located']) )
        self.maxDiff = tmp

    def test_paper_hexbin_query(self):
        """
        
        Arguments:
        - `self`: self
        """
        with wos_reader.open_wos_h5( "test_data/irwin.h5" ) as w5 :
            locresults = wos_reader_query.paperHexbinQuery( w5, get_locations_and_unknowns )
        expected_results = {'not_located': ['Kyushu Univ, Dept Phys, Fukuoka 812, Japan', 'Natl Res Inst Astron & Geophys, Dept Astron, Cairo 11421, Egypt', 'Natl Res Inst Astron & Geophys, Dept Astron, Cairo 11421, Egypt; Natl Res Inst Astron & Geophys, Kottamia Ctr Sci Excellence Astron & Space Sci KC, Cairo 11421, Egypt'], 'paper_locations': {'10.1051/mmnp/20138208': {'nodes': {'3': {'val': 0, 'text': '10.1051/mmnp/20138208: Humboldt Univ, Inst Phys, D-12489 Berlin, Germany', 'lat': 52.4370179, 'lon': 13.5470509}, '2': {'val': 0, 'text': '10.1051/mmnp/20138208: Univ Potsdam, Inst Phys & Astron, D-14476 Potsdam, Germany; Tech Univ Tampere, Dept Phys, FI-33101 Tampere, Finland', 'lat': 61.4981508, 'lon': 23.7610254}, '1': {'val': 0, 'text': '10.1051/mmnp/20138208: Univ Oxford, Rudolf Peierls Ctr Theoret Phys, Oxford OX1 3NP, England', 'lat': 51.7595933, 'lon': -1.259116}, '0': {'val': 0, 'text': '10.1051/mmnp/20138208: Univ Southern Denmark, MEMPHYS Ctr Biomembrane Phys, Dept Phys Chem & Pharm, DK-5230 Odense M, Denmark', 'lat': 55.37906169999999, 'lon': 10.4033399}, '4': {'val': 0, 'text': '10.1051/mmnp/20138208: Inst Theoret Phys NSC KIPT, UA-61108 Kharkov, Ukraine; Max Planck Inst Phys Komplexer Syst, D-01187 Dresden, Germany', 'lat': 51.0266014, 'lon': 13.7090684}}, 'edges': {'3': {'val': 0, 'to': 4, 'from': 0, 'text': '10.1051/mmnp/20138208'}, '2': {'val': 0, 'to': 3, 'from': 0, 'text': '10.1051/mmnp/20138208'}, '1': {'val': 0, 'to': 2, 'from': 0, 'text': '10.1051/mmnp/20138208'}, '0': {'val': 0, 'to': 1, 'from': 0, 'text': '10.1051/mmnp/20138208'}, '7': {'val': 0, 'to': 3, 'from': 2, 'text': '10.1051/mmnp/20138208'}, '6': {'val': 0, 'to': 4, 'from': 1, 'text': '10.1051/mmnp/20138208'}, '5': {'val': 0, 'to': 3, 'from': 1, 'text': '10.1051/mmnp/20138208'}, '4': {'val': 0, 'to': 2, 'from': 1, 'text': '10.1051/mmnp/20138208'}, '9': {'val': 0, 'to': 4, 'from': 3, 'text': '10.1051/mmnp/20138208'}, '8': {'val': 0, 'to': 4, 'from': 2, 'text': '10.1051/mmnp/20138208'}}}}, 'failed_papers': ['', '10.1016/j.newast.2014.02.011'], 'hexbin': {'nodes': [{'text': '10.1051/mmnp/20138208: Univ Southern Denmark, MEMPHYS Ctr Biomembrane Phys, Dept Phys Chem & Pharm, DK-5230 Odense M, Denmark', 'lng': 10.4033399, 'lat': 55.37906169999999, 'pubcount': 1}, {'text': '10.1051/mmnp/20138208: Univ Oxford, Rudolf Peierls Ctr Theoret Phys, Oxford OX1 3NP, England', 'lng': -1.259116, 'lat': 51.7595933, 'pubcount': 1}, {'text': '10.1051/mmnp/20138208: Univ Potsdam, Inst Phys & Astron, D-14476 Potsdam, Germany; Tech Univ Tampere, Dept Phys, FI-33101 Tampere, Finland', 'lng': 23.7610254, 'lat': 61.4981508, 'pubcount': 1}, {'text': '10.1051/mmnp/20138208: Humboldt Univ, Inst Phys, D-12489 Berlin, Germany', 'lng': 13.5470509, 'lat': 52.4370179, 'pubcount': 1}, {'text': '10.1051/mmnp/20138208: Inst Theoret Phys NSC KIPT, UA-61108 Kharkov, Ukraine; Max Planck Inst Phys Komplexer Syst, D-01187 Dresden, Germany', 'lng': 13.7090684, 'lat': 51.0266014, 'pubcount': 1}], 'edges': [{'fromlng': 10.4033399, 'fromlat': 55.37906169999999, 'tolng': -1.259116, 'weight': 1, 'tolat': 51.7595933}, {'fromlng': 10.4033399, 'fromlat': 55.37906169999999, 'tolng': 23.7610254, 'weight': 1, 'tolat': 61.4981508}, {'fromlng': 10.4033399, 'fromlat': 55.37906169999999, 'tolng': 13.5470509, 'weight': 1, 'tolat': 52.4370179}, {'fromlng': 10.4033399, 'fromlat': 55.37906169999999, 'tolng': 13.7090684, 'weight': 1, 'tolat': 51.0266014}, {'fromlng': -1.259116, 'fromlat': 51.7595933, 'tolng': 23.7610254, 'weight': 1, 'tolat': 61.4981508}, {'fromlng': -1.259116, 'fromlat': 51.7595933, 'tolng': 13.5470509, 'weight': 1, 'tolat': 52.4370179}, {'fromlng': -1.259116, 'fromlat': 51.7595933, 'tolng': 13.7090684, 'weight': 1, 'tolat': 51.0266014}, {'fromlng': 23.7610254, 'fromlat': 61.4981508, 'tolng': 13.5470509, 'weight': 1, 'tolat': 52.4370179}, {'fromlng': 23.7610254, 'fromlat': 61.4981508, 'tolng': 13.7090684, 'weight': 1, 'tolat': 51.0266014}, {'fromlng': 13.5470509, 'fromlat': 52.4370179, 'tolng': 13.7090684, 'weight': 1, 'tolat': 51.0266014}]}}
        self.assertEqual( len(locresults['hexbin']['nodes']), len(expected_results['hexbin']['nodes'] ) )
        self.assertEqual( len(locresults['hexbin']['edges']), len(expected_results['hexbin']['edges'] ) )
        
from biblio import wos_reader, wos_reader_query
        
class BiblioTest( TestCase ):
    """
    Test the bibliometrics functions
    """

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

        
        

                        
if __name__ == "__main__" :
    unittest.main()
    
        
        
        
