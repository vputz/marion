"""
A module for reading Web of Science tab-delimited (UTF-8, Windows) files

A key to the WoK fields, http://images.webofknowledge.com/WOKRS57B4/help/WOS/hs_wos_fieldtags.html
FN File name
VR Version Number
PT Publication Type (J = journal B = book, S = Series, P=Patent)
AU Authors last name/initial
AF Authors, full name
BA Book Authors
BF Book authors, full name
CA Group Authors
GP Book Group Authors
BE Editors
TI title
SO Source (journal)
SE Series title
LA language
DT Document Type
CT Conferency Title
CY Conference Date
CL Conference Location
SP Conference Sponsors
HO Conference Host
DE Author Keywords
ID KeyWords Plus
AB abstract
C1 Addresses (of authors)
RP Reprint Address
EM Email contact
FU Funding and grant number
FX Funding text
CR Cited References
NR Cited Reference Count
TC WOS Times CIted count
Z9 Total times cited count (WoS, BCI, CSCD)
PU Publisher
PI Publisher City
PA Publisher Address
SN International Standard Serial Number (ISSN)
BN International Standard Book Number (ISBN)
J9 29-char source abbreviation
JI ISO source abbreviation
PD Publication date
PY Year Published
VL Volume
IS Issue
SI Special issue
PN Part Number
SU Supplement
MA Meeting Abstract
BP Beginning Page
EP Ending Page
AR Article Number
DI Digital Object Identifier (DOI)
D2 Book digital object identifier (DOI)
PG Page count
P2 Chapter Count
WC Web of Science categories
SC research areas
GA document delivery number
UT accession number
ER end of record
EF end of file
"""
import csv, fileinput
from collections import Counter
import itertools
import re
import string
from nltk.tokenize import word_tokenize
from nltk import PorterStemmer

def authorlist_from_authorfield( string ) :
    return [x.strip() for x in string.split(";")]

flatten_chain = itertools.chain.from_iterable

Country_words = [x for x in """
Albania
Algeria
Arab Emirates
Argentina
Armenia
Australia
Austria
Azerbaijan
Bangladesh
Belgium
Bolivia
Brazil
Bulgaria
Byelarus
Combodia
Cameroon
Canada
Chile
China
Colombia
Costa Rica
Cote Ivoire
Croatia
Cuba
Cyprus
Czech Republic
Denmark
Egypt
England
Estonia
Ethiopia
Faso
Finland
France
Georgia
Germany
Ghana
Greece
Guatemala
Hungary
Iceland
India
Indonesia
Iran
Ireland
Israel
Italy
Japan
Jordan
Kenya
Kuwait
Kyrgyzstan
Latvia
Lebanon
Liberia
Lithuania
Luxembourg
Malaysia
Malta
Mexico
Moldova
Monaco
Monteneg
Montenegro
Morocco
Netherlands
New Zealand
North Korea
Norway
Oman
Pakistan
Peru
Poland
Portugal
Qatar
Rep Congo
Romania
Russia
Saudi Arabia
Scotland
Serbia
Singapore
Slovakia
Slovenia
South Africa
South Korea
Spain
Spain
Sri Lanka
Sweden
Switzerland
Taiwan
Tanzania
Thailand
Tunisia
Turkey
Uganda
Ukraine
Uruguay
Usa
Uzbekistan
Vietnam
Wales
""".split("\n") if len(x) > 0 ]

Country_regexes = [re.compile( x+"$" ) for x in Country_words]

def country_from_address(s, countries=Country_regexes) :
    """Tries to match a country to the last few words of an address"""
    # strip semicolon and trailing space, lowercase, and capitalize each word
    s=s.strip("; ").lower().title()
    # match to regexes in country_list
    for x in countries :
        m = x.search(s)
        if (m != None) :
            return m.group(0)
    # if no match, print unmatched last two words (to build word list)
    print( "Not found: "+str(s.split()[-2:]))
    return "Error"

def countrylist_from_addresses( s ) :
    """ Creates a list of countries from a string of addresses """
    # break on [author] sections
    strings = [x for x in flatten_chain( [x.split(';') for x in re.split("\[.*?\]", s)]) if len(x.strip()) > 0]
    #print strings
    return list(set([country_from_address(x) for x in strings if len(x) > 0]))

def dict_from_addresses( s ) :
    """ creates an author dict from addresses """
    r = re.compile("\[(.*?)\]\s*(.*?);")
    pairs = r.findall( s )
    result = {}
    for p in pairs :
        names = [x.strip() for x in p[0].split(';')]
        for name in names :
            if name in result :
                result[name] = result[name] + "; " + p[1]
            else :
                result[name] = p[1]
    return result

def cited_dois( item ) :
    return re.findall('DOI\s*([^\s;]*)',item['CR'])

class Wos_reader() :

    def __init__(self, files) :
        self.files = files

    def reader(self) :
        return csv.DictReader( fileinput.FileInput(self.files), dialect='excel-tab' )

    def fields( self, field ) :
        return [row[field] for row in self.reader()]

    def wordle_strings( self, field = "SC" ) :
        return flatten_chain([[x.strip() for x in row[field].split(";")] for row in self.reader()])

    def wordle_string( self, field = "SC" ) :
        ws = self.wordle_strings( field )
        wsc = Counter(ws)
        results = []
        for k,v in wsc.iteritems() :
            results.append( k + ":" + str(v) )
        return "\n".join( results )

    def sources_counter(self) :
        return Counter([row['JI'] for row in self.reader()])

    def authors_counter(self) :
        return Counter(flatten_chain([authorlist_from_authorfield(row['AU']) for row in self.reader()]))

    def set_authors(self) :
        return set(self.authors_counter().iterkeys())

    def countries_counter(self) :
        return Counter(flatten_chain([countrylist_from_addresses(x) for x in self.address_strings()]))

    def address_strings(self) :
        return [row['C1'] for row in self.reader()]

    def set_cited_dois(self) :
        return list(set(flatten_chain( (cited_dois(x) for x in self.reader() ) )))

    def dois( self ) :
        return [x['DI'] for x in self.reader() if x['DI']!= '']

    def set_years( self ) :
        return set((x['PY'] for x in self.reader() if x['PY'].isdigit() and int(x['PY']) > 1900))
    
    def by_year_iterator( self, py ) :
        return (x for x in self.reader() if x['PY'] == py)

    def country_count_by_year( self ) :
        yl = list(self.set_years())
        yl.sort( lambda a,b : cmp(int(a), int(b)) )
        result = {}
        for year in yl :
            result[year] = Counter(flatten_chain([countrylist_from_addresses(x) for x in [row['C1'] for row in self.by_year_iterator(year)]]))
        return result

    def padded_country_count_by_year( self, top_x = 7 ) :
        yl = list(self.set_years())
        cyr = self.country_count_by_year()
        country_counter = self.countries_counter()
        l = country_counter.items()
        l.sort( lambda a,b : cmp(b[1],a[1]) )
        
        countries = [x[0] for x in l[0:top_x]]
        Result = {}
        for year in cyr.iterkeys() :
            Result[year] = {}
            for country in countries :
                if country in cyr[year] :
                    Result[year][country] = cyr[year][country]
                else :
                    Result[year][country] = 0
        return Result

        
def download_names( stem, lastnum ) :
    return [stem+".tab"] + [stem+"_("+str(x)+").tab" for x in range(1,lastnum+1)]

from numpy import array
import tables

class Paper( tables.IsDescription ) :
    index = tables.Int32Col() # index for authors, etc
    doi = tables.StringCol(50) # max in one dump was 31 DI
    title = tables.StringCol(500) # max in one was 174 TI
    journal = tables.StringCol(30) # J9
    pubdate = tables.StringCol(8) # PD
    pubyear = tables.Int16Col() # PY
    #max author was 22

class Author( tables.IsDescription ) :
    author = tables.StringCol( 40 )
    address = tables.StringCol( 40 )

class Keyword( tables.IsDescription ) :
    keyword = tables.StringCol( 80 )
    
def make_pytable( w, filename, title="test" ) :
    """parses the wos reader and converts everything into an HDF5 pytable for faster access"""
    h5file = tables.open_file( filename, mode='w', title = title )
    table = h5file.create_table( h5file.root, 'papers', Paper, 'WOS paper records' )
    authors = h5file.create_vlarray( h5file.root, 'authors', tables.StringAtom(40) )
    countries = h5file.create_vlarray( h5file.root, 'countries', tables.StringAtom(30) )
    cited_papers = h5file.create_vlarray( h5file.root, 'cited_papers', tables.StringAtom(50) )
    abstracts = h5file.create_vlarray( h5file.root, 'abstracts', tables.VLStringAtom() )
    categories = h5file.create_vlarray( h5file.root, 'categories', tables.StringAtom(40) )
    authortable = h5file.create_table( h5file.root, 'authortable', Author, "WOS Author data" )
    index = 0
    for p in w.reader() :
        if p['DI'] == 'DI' :
            continue
        paper = table.row
        paper['index'] = index
        paper['doi'] = p['DI']
        paper['title'] = p['TI']
        paper['journal'] = p['J9']
        paper['pubdate'] = p['PD']
        paper['pubyear'] = int(p['PY']) if p['PY'].isdigit() else -1
        paper.append()

        authors.append(authorlist_from_authorfield( p['AU'] ))
        categories.append(authorlist_from_authorfield( p['WC'] ) )
        # now if each author is not already in the table, add to the author table
        aulist = authorlist_from_authorfield( p['AU'] )
        aflist = authorlist_from_authorfield( p['AF'] )
        if len( aulist ) != len( aflist ) :
            print( "ERROR, AUTHOR LISTS DIFFERENT LENGTH" )
            continue
        adddir = dict_from_addresses( p['C1'] )
        for i in range( len(aulist) ) :
            a = aulist[i]
            matches = [x for x in authortable if x['author'] == a]
            #print matches
            if len(matches) == 0 :
                newauthor = authortable.row
                newauthor['author'] = a
                if aflist[i] in adddir :
                    newauthor['address'] = adddir[aflist[i]]
                newauthor.append()
                authortable.flush()
            else :
                for r in authortable.where( 'author == "' + a + '"' ) :
                    if aflist[i] in adddir :
                        r['address'] = r['address'] + adddir[aflist[i]]
                        authortable.flush()
        countries.append(countrylist_from_addresses( p['C1'] ) )
        cited_papers.append( cited_dois( p ))
        abstracts.append( p['AB'] )
        index = index + 1
        
    table.flush()
    authortable.flush()
    authortable.cols.author.create_index()
    authortable.flush()
    h5file.close()


def stripword( s ) :
    """
    strips punctuation from word
    """
    return re.sub( '[\W\d]', '', s )

def wordbag( text, ignore_words = [] ) :
    """
    A dictionary where the keys are words and the values are counts of words in the text.
    Taking the keys() should get a list of unique words
    """
    iter = (stripword(s) for s in text.lower().split() if stripword(s) not in ignore_words)
    result = {}
    for x in iter :
        if x in result :
            result[x] += 1
        else :
            result[x] = 1
    return result

my_ignore_words = set(('a','von','','the','and','from','with','to','some','for','of','by','on','in','all','do','we','is','it','if','has','was','no','can','so','not','one','any','or','an','as','at','are','us','our','elsevier','institute' ,'edition','little', 'we'))

Ignore_words = wordbag( open('english_stop.txt').read()+" ".join(my_ignore_words), () ).keys()

def words( item, ignore_words = Ignore_words ) :
    result = list(wordbag(item, ignore_words).keys())
    result.sort()
    return result

def stems( item, ignore_words = Ignore_words ): 
    # remove numbers and punctuation
    p = PorterStemmer()
    s = item.translate(None, string.punctuation).translate(None, string.digits)
    result = list(set([p.stem(x).lower() for x in word_tokenize(s) if stripword(x) not in ignore_words]))
    return result

class Wos_h5_reader() :

    def __init__( self, filename ) :
        self.h5 = tables.openFile(filename, 'r')

    def all_dois( self ) :
        return array([ x['doi'] for x in self.h5.root.papers if x['doi'] != '' ])

    def countries_counter( self ) :
        return Counter( flatten_chain( [x for x in self.h5.root.countries] ) )
    
    def all_cited_dois( self ) :
        return array( list(set( flatten_chain( [ x for x in self.h5.root.cited_papers ] ) ) ) )

    def all_authors( self ) :
        return array( list( set( flatten_chain( [ x for x in self.h5.root.authors ] ) ) ) )

    def all_title_words( self ) :
        return list(set(itertools.chain.from_iterable( (words(x['title']) for x in self.h5.root.papers) ) ))

    def all_title_stems( self ) :
        return list(set(itertools.chain.from_iterable( (stems(x['title']) for x in self.h5.root.papers) ) ))

    def dict_doi_to_authors( self ) :
        Result = {}
        for paper in self.h5.root.papers :
            Result[ paper['doi'] ] = self.h5.root.authors[ paper['index'] ]
        return Result

from contextlib import contextmanager

@contextmanager
def open_wos_h5( filename ) :
        w5 = Wos_h5_reader( filename )
        yield ( w5 )
        w5.h5.close()

@contextmanager
def open_wos_tab( filename ) :
    wos = Wos_reader( filename )
    yield( wos )
            
#make_pytable( Wos_reader("metamaterials_cited.tab"), "metamaterials.h5", "Metamaterials" )
#w5 = Wos_h5_reader( "metamaterials.h5" )
w = Wos_reader( ["switz_oct13_1.csv","switz_oct13_2.csv","switz_oct13_3.csv"] )

