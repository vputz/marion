from biblio.wos_reader import open_wos_h5, Wos_h5_reader
from collections import Counter
import json
import unittest
from itertools import chain, islice, combinations

"""
Given a "query" in the form of a JSON datastructure, output another JSON
datastructure (queryResult) with the results.  The "query" is really a template; this is
a move to creating reports based on bibliometric data

Example query:

{
  'pubs' : { 'queryType' : 'categoricalSummary',
             'queryString' : '(x['journal'] for x in w5.h5.root.papers)' }
}
"""

def resultFromQuery( w5, q ):
    """
    Given a wos_h5 and a query dict, run all the query elements and return a result,
    which is a dictionary of the query keys and the result objects.  Should be
    changed to JSON for storage
    """
    result = {}
    for (k,v) in q.items() :
        if v['queryType'] == 'categoricalSummary' :
            thisResult = categoricalSummaryQuery( w5, v['queryString'] )
        elif v['queryType'] == 'paperLocationQuery' :
            thisResult = paperLocationQuery( w5 )
        elif v['queryType'] == 'paperLatLonQuery' :
            thisResult = paperLatLonQuery( w5, v['paperLocationFunc'] )
        result[k] = thisResult
        
    return result

# queries return objects, not JSON (the "result" is a JSON string)
     
def categoricalSummaryQuery( w5, queryString ) :
    """
    Returns a counter, which is a dictionary of 'label':count pairings.  Takes
    a queryString which is evaluated across the wos reader to sum up the
    quantities by bin.  Due to the fact that the queryString is eval'ed, this is
    titanically dangerous and shouldn't be exposed to the public, but it does make
    the function extremely flexible
    """
    result = Counter()
    # THIS IS INCREDIBLY DANGEROUS
    print( "*** "+str( queryString ) )
    result.update( [x for x in eval(queryString, dict( w5=w5, chain=chain ))] )
    # so now we have a counter, but what we need to return is a sorted list of dictionaries,
    # by value, with "label" and "value" fields
    resultList = [ { "label" : x[0], "value" : x[1] } for x in result.most_common() ]
    return resultList

def paperLocationQuery(w5):
    """
    Returns a dictionary
    {
      doi(string): [ set_of_addresses ]
    }
    """
    result = {}
    for row in w5.h5.root.papers :
        addresses = set(w5.addresses_from_paper( row['index'] ))
        result[ row['doi'] ] = addresses
    return result
    
def paperLatLonQuery( w5, paperLocationFunc ):
    """
    Like paperlocationquery, but returns a more complex object, a tuple of
    paper_locations : {doi :
    {
      nodes : { id(int) : { lat: float, lon: float, text: string, val: float } }
      edges : { id(int) : { from: int, to: int, text:string, val: float } }
    } },
    failed_papers : [ doi ]
    not_located : [ string ] 
    

    arg paperLocationFunc: callable python function in the form
    func(string)-> ( {loc(string): { lat: float, lon: float } }, [ string ])
    """
    address_sets = paperLocationQuery( w5 )
    result = { "paper_locations" : {}, 'failed_papers' : [], "not_located" : [] }
    for doi, addresses in address_sets.items() :

        locs, unknowns = paperLocationFunc( addresses )
        if len (unknowns) != 0 :
            result['failed_papers'].append( doi )
            result['not_located'].extend( unknowns )
        else :
            this_result = { "nodes" : {}, "edges" : {} }
            node_index = 0
            latlngs = [ locs[x] for x in addresses ]
            for latlng in latlngs :
                this_result['nodes'][node_index] = { 'lat' : latlng['lat'], 'lon' : latlng['lon'], 'text' : doi, 'val' : 0 }
                node_index = node_index + 1
            # now build the edges; this allows no self-loops
            edge_combos = list(combinations( range( node_index ), 2 ))
            edge_index = 0 
            for edge in edge_combos:
                this_result['edges'][edge_index] = { 'from' : edge_combos[edge_index][0],
                                                     'to' : edge_combos[edge_index][1],
                                                     'text' : doi,
                                                     'val' : 0 }
                edge_index = edge_index + 1
            result['paper_locations'][doi] = this_result
    # just compress the "not locateds" into a set
    result['not_located'] = set(result['not_located'])
    return result
                
                
    

# for reference, some handy queries.  This is fairly torturous, but it does work!
"""
universities: c = categoricalSummaryQuery( w5, "list(chain(*[ [x['address'].split(',')[0] for x in w5.h5.root.authortable.where( 'author == \"{y}\"'.format(y=y))] for y in chain( *(list(z) for z in w5.h5.root.authors) ) ]))")
"""

def run_query( toFile, w5File, queryFile ) :
    """
    Run the query stored in JSON file queryFile on the h5 file noted by w5File,
    and store the result in JSON file toFile
    """
    q = json.loads( open(queryFile, "r").read() )
    result = None
    with open_wos_h5( w5File ) as w5 :
        result = resultFromQuery( w5, q )
    with open( toFile, "w" ) as outFile :
        outFile.write( json.dumps( result ) )

def dictFromLabeledList( l ) :
    return dict( [ (x['label'], x['value']) for x in l ] )

class TestQueries( unittest.TestCase ) :

    def setUp( self ) :
        self.w5 = Wos_h5_reader("switz.h5")

    def testCategoricalSummaryQueryByField(self) :
        c = categoricalSummaryQuery( self.w5, "(x['journal'] for x in w5.h5.root.papers)" )
        self.assertEqual( dictFromLabeledList(c)['ABSTR PAP AM CHEM S'], 53 )

    def testResultFromQueryString( self ) :
        q = json.loads( """{ "pubs" : { "queryType" : "categoricalSummary", "queryString" : "(x[\\"journal\\"] for x in w5.h5.root.papers)" }, "authors" : { "queryType" : "categoricalSummary", "queryString" : "(x for x in chain(*(list(y) for y in w5.h5.root.authors)))" } }""")
        c = resultFromQuery( self.w5, q )
        self.assertEqual( dictFromLabeledList(c['pubs'])['ABSTR PAP AM CHEM S'], 53 )
        self.assertEqual( dictFromLabeledList(c['authors'])['Wang, J'], 36 )

def do_tests() :
    suite = unittest.TestLoader().loadTestsFromTestCase( TestQueries )
    unittest.TextTestRunner().run(suite)
    
#do_tests()
