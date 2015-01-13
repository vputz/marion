from biblio.wos_reader import open_wos_h5, Wos_h5_reader
from collections import Counter
import json
import unittest
from itertools import chain, islice

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
    Returns a list [ [set_of_addresses_for_paper_1], [set_of_addresses_for_paper_2] ]
    """
    result = []
    for row in w5.h5.root.papers :
        addresses = set(w5.addresses_from_paper( 0 ))
        result.append(addresses)
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
