from tut_tests import MarionTest
from flask.ext.security import SQLAlchemyUserDatastore
import tutorial
from tutorial.models import User, Role
from tutorial.models import Gps_remap, Gps_cache
from tutorial.geocache import remap_has_key, cache_has_key, get_location, get_locations_and_unknowns, get_locations_and_unknowns_nocache
from flask_security.utils import login_user, logout_user
from marion_biblio import wos_reader, wos_reader_query


class GPSTest(MarionTest):

    """
    Tests both the GPS lookup and some biblio functions that rely on it
    """
    def setUp(self):
        self.user_datastore = SQLAlchemyUserDatastore(tutorial.db, User, Role)
        tutorial.db.create_all()
        # u = User( nickname='test1', email='test1@test.com' )
        self.remap_from = "University of Oxford"
        self.remap_to = "Oxford, United Kingdom"
        self.cache_loc = "Oxford, United Kingdom"
        self.cache_lat = 51.7519
        self.cache_lon = -1.2578

        self.user = self.user_datastore.create_user(nickname='test1',
                                                    email='test1@test.com',
                                                    password='password')
        tutorial.db.session.add(self.user)
        tutorial.db.session.commit()

        oxford_remap = Gps_remap(from_location=self.remap_from,
                                 to_location=self.remap_to)
        tutorial.db.session.add(oxford_remap)

        oxford_lookup = Gps_cache(location=self.cache_loc,
                                  latitude=self.cache_lat,
                                  longitude=self.cache_lon)
        tutorial.db.session.add(oxford_lookup)

        tutorial.db.session.commit()

    def _logout(self):
        logout_user()

    def tearDown(self):
        self._logout()
        tutorial.db.session.remove()
        tutorial.db.drop_all()

    def test_retrieval(self):
        remap = Gps_remap.query.get(self.remap_from)
        self.assertEqual(remap.from_location, self.remap_from)

        cache = Gps_cache.query.get(self.cache_loc)
        self.assertAlmostEqual(cache.latitude, self.cache_lat)
        self.assertAlmostEqual(cache.longitude, self.cache_lon)

    def test_has_keys(self):
        self.assertAlmostEqual(remap_has_key(self.remap_from), True)
        self.assertAlmostEqual(cache_has_key(self.cache_loc), True)

    def test_get_location(self):
        self.assertEqual(get_location("blorfing"), None)
        self.assertAlmostEqual(get_location(self.cache_loc)['lat'],
                               self.cache_lat)
        self.assertAlmostEqual(get_location("london")['lon'], -0.1277583)

    def test_get_locations_and_unknowns(self):
        locs, unks = get_locations_and_unknowns(
            ["University of Oxford", "blorfing"],
            False)
        self.assertAlmostEqual(locs["University of Oxford"]['lon'],
                               self.cache_lon)
        self.assertEqual(unks[0], "blorfing")

    def test_paper_lat_lon_query(self):
        """
        """
        with wos_reader.open_wos_h5("test_data/irwin.h5") as w5:
            locresults = wos_reader_query.paperLatLonQuery(
                w5, get_locations_and_unknowns_nocache)
        tmp = self.maxDiff
        self.maxDiff = None
        irwin_network = {'not_located': ['Kyushu Univ, Dept Phys, Fukuoka 812, Japan', 'Natl Res Inst Astron & Geophys, Dept Astron, Cairo 11421, Egypt; Natl Res Inst Astron & Geophys, Kottamia Ctr Sci Excellence Astron & Space Sci KC, Cairo 11421, Egypt', 'Natl Res Inst Astron & Geophys, Dept Astron, Cairo 11421, Egypt'], 'paper_locations': {'10.1051/mmnp/20138208': {'edges': {0: {'to': 1, 'text': '10.1051/mmnp/20138208', 'from': 0, 'val': 0}, 1: {'to': 2, 'text': '10.1051/mmnp/20138208', 'from': 0, 'val': 0}, 2: {'to': 3, 'text': '10.1051/mmnp/20138208', 'from': 0, 'val': 0}, 3: {'to': 4, 'text': '10.1051/mmnp/20138208', 'from': 0, 'val': 0}, 4: {'to': 2, 'text': '10.1051/mmnp/20138208', 'from': 1, 'val': 0}, 5: {'to': 3, 'text': '10.1051/mmnp/20138208', 'from': 1, 'val': 0}, 6: {'to': 4, 'text': '10.1051/mmnp/20138208', 'from': 1, 'val': 0}, 7: {'to': 3, 'text': '10.1051/mmnp/20138208', 'from': 2, 'val': 0}, 8: {'to': 4, 'text': '10.1051/mmnp/20138208', 'from': 2, 'val': 0}, 9: {'to': 4, 'text': '10.1051/mmnp/20138208', 'from': 3, 'val': 0}}, 'nodes': {0: {'text': '10.1051/mmnp/20138208: Univ Southern Denmark, MEMPHYS Ctr Biomembrane Phys, Dept Phys Chem & Pharm, DK-5230 Odense M, Denmark', 'val': 0, 'lon': 10.4033399, 'lat': 55.37906169999999}, 1: {'text': '10.1051/mmnp/20138208: Univ Potsdam, Inst Phys & Astron, D-14476 Potsdam, Germany; Tech Univ Tampere, Dept Phys, FI-33101 Tampere, Finland', 'val': 0, 'lon': 23.7610254, 'lat': 61.4981508}, 2: {'text': '10.1051/mmnp/20138208: Univ Oxford, Rudolf Peierls Ctr Theoret Phys, Oxford OX1 3NP, England', 'val': 0, 'lon': -1.259116, 'lat': 51.7595933}, 3: {'text': '10.1051/mmnp/20138208: Inst Theoret Phys NSC KIPT, UA-61108 Kharkov, Ukraine; Max Planck Inst Phys Komplexer Syst, D-01187 Dresden, Germany', 'val': 0, 'lon': 13.7090684, 'lat': 51.0266014}, 4: {'text': '10.1051/mmnp/20138208: Humboldt Univ, Inst Phys, D-12489 Berlin, Germany', 'val': 0, 'lon': 13.5470509, 'lat': 52.4370179}}}}, 'failed_papers': ['', '10.1016/j.newast.2014.02.011']}
        self.assertEqual(locresults['paper_locations'].keys(),
                         irwin_network['paper_locations'].keys())
        self.assertEqual(set(locresults['failed_papers']),
                         set(irwin_network['failed_papers']))
        self.assertEqual(set(locresults['not_located']),
                         set(irwin_network['not_located']))
        self.maxDiff = tmp

    def test_paper_hexbin_query(self):
        with wos_reader.open_wos_h5("test_data/irwin.h5") as w5:
            locresults = wos_reader_query.paperHexbinQuery(
                w5,
                get_locations_and_unknowns_nocache)
        expected_results = {'not_located': ['Kyushu Univ, Dept Phys, Fukuoka 812, Japan', 'Natl Res Inst Astron & Geophys, Dept Astron, Cairo 11421, Egypt', 'Natl Res Inst Astron & Geophys, Dept Astron, Cairo 11421, Egypt; Natl Res Inst Astron & Geophys, Kottamia Ctr Sci Excellence Astron & Space Sci KC, Cairo 11421, Egypt'], 'paper_locations': {'10.1051/mmnp/20138208': {'nodes': {'3': {'val': 0, 'text': '10.1051/mmnp/20138208: Humboldt Univ, Inst Phys, D-12489 Berlin, Germany', 'lat': 52.4370179, 'lon': 13.5470509}, '2': {'val': 0, 'text': '10.1051/mmnp/20138208: Univ Potsdam, Inst Phys & Astron, D-14476 Potsdam, Germany; Tech Univ Tampere, Dept Phys, FI-33101 Tampere, Finland', 'lat': 61.4981508, 'lon': 23.7610254}, '1': {'val': 0, 'text': '10.1051/mmnp/20138208: Univ Oxford, Rudolf Peierls Ctr Theoret Phys, Oxford OX1 3NP, England', 'lat': 51.7595933, 'lon': -1.259116}, '0': {'val': 0, 'text': '10.1051/mmnp/20138208: Univ Southern Denmark, MEMPHYS Ctr Biomembrane Phys, Dept Phys Chem & Pharm, DK-5230 Odense M, Denmark', 'lat': 55.37906169999999, 'lon': 10.4033399}, '4': {'val': 0, 'text': '10.1051/mmnp/20138208: Inst Theoret Phys NSC KIPT, UA-61108 Kharkov, Ukraine; Max Planck Inst Phys Komplexer Syst, D-01187 Dresden, Germany', 'lat': 51.0266014, 'lon': 13.7090684}}, 'edges': {'3': {'val': 0, 'to': 4, 'from': 0, 'text': '10.1051/mmnp/20138208'}, '2': {'val': 0, 'to': 3, 'from': 0, 'text': '10.1051/mmnp/20138208'}, '1': {'val': 0, 'to': 2, 'from': 0, 'text': '10.1051/mmnp/20138208'}, '0': {'val': 0, 'to': 1, 'from': 0, 'text': '10.1051/mmnp/20138208'}, '7': {'val': 0, 'to': 3, 'from': 2, 'text': '10.1051/mmnp/20138208'}, '6': {'val': 0, 'to': 4, 'from': 1, 'text': '10.1051/mmnp/20138208'}, '5': {'val': 0, 'to': 3, 'from': 1, 'text': '10.1051/mmnp/20138208'}, '4': {'val': 0, 'to': 2, 'from': 1, 'text': '10.1051/mmnp/20138208'}, '9': {'val': 0, 'to': 4, 'from': 3, 'text': '10.1051/mmnp/20138208'}, '8': {'val': 0, 'to': 4, 'from': 2, 'text': '10.1051/mmnp/20138208'}}}}, 'failed_papers': ['', '10.1016/j.newast.2014.02.011'], 'hexbin': {'nodes': [{'text': '10.1051/mmnp/20138208: Univ Southern Denmark, MEMPHYS Ctr Biomembrane Phys, Dept Phys Chem & Pharm, DK-5230 Odense M, Denmark', 'lng': 10.4033399, 'lat': 55.37906169999999, 'pubcount': 1}, {'text': '10.1051/mmnp/20138208: Univ Oxford, Rudolf Peierls Ctr Theoret Phys, Oxford OX1 3NP, England', 'lng': -1.259116, 'lat': 51.7595933, 'pubcount': 1}, {'text': '10.1051/mmnp/20138208: Univ Potsdam, Inst Phys & Astron, D-14476 Potsdam, Germany; Tech Univ Tampere, Dept Phys, FI-33101 Tampere, Finland', 'lng': 23.7610254, 'lat': 61.4981508, 'pubcount': 1}, {'text': '10.1051/mmnp/20138208: Humboldt Univ, Inst Phys, D-12489 Berlin, Germany', 'lng': 13.5470509, 'lat': 52.4370179, 'pubcount': 1}, {'text': '10.1051/mmnp/20138208: Inst Theoret Phys NSC KIPT, UA-61108 Kharkov, Ukraine; Max Planck Inst Phys Komplexer Syst, D-01187 Dresden, Germany', 'lng': 13.7090684, 'lat': 51.0266014, 'pubcount': 1}], 'edges': [{'fromlng': 10.4033399, 'fromlat': 55.37906169999999, 'tolng': -1.259116, 'weight': 1, 'tolat': 51.7595933}, {'fromlng': 10.4033399, 'fromlat': 55.37906169999999, 'tolng': 23.7610254, 'weight': 1, 'tolat': 61.4981508}, {'fromlng': 10.4033399, 'fromlat': 55.37906169999999, 'tolng': 13.5470509, 'weight': 1, 'tolat': 52.4370179}, {'fromlng': 10.4033399, 'fromlat': 55.37906169999999, 'tolng': 13.7090684, 'weight': 1, 'tolat': 51.0266014}, {'fromlng': -1.259116, 'fromlat': 51.7595933, 'tolng': 23.7610254, 'weight': 1, 'tolat': 61.4981508}, {'fromlng': -1.259116, 'fromlat': 51.7595933, 'tolng': 13.5470509, 'weight': 1, 'tolat': 52.4370179}, {'fromlng': -1.259116, 'fromlat': 51.7595933, 'tolng': 13.7090684, 'weight': 1, 'tolat': 51.0266014}, {'fromlng': 23.7610254, 'fromlat': 61.4981508, 'tolng': 13.5470509, 'weight': 1, 'tolat': 52.4370179}, {'fromlng': 23.7610254, 'fromlat': 61.4981508, 'tolng': 13.7090684, 'weight': 1, 'tolat': 51.0266014}, {'fromlng': 13.5470509, 'fromlat': 52.4370179, 'tolng': 13.7090684, 'weight': 1, 'tolat': 51.0266014}]}}
        self.assertEqual(len(locresults['hexbin']['nodes']),
                         len(expected_results['hexbin']['nodes']))
        self.assertEqual(len(locresults['hexbin']['edges']),
                         len(expected_results['hexbin']['edges']))
