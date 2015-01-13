from tutorial.models import db, Gps_cache, Gps_remap
from geopy import geocoders

#TODO: deal with case

def remap_has_key( loc ) :
    return Gps_remap.query.get( loc ) != None

def cache_has_key( loc ) :
    return Gps_cache.query.get( loc ) != None

def get_location( loc, cache_result = False ) :
    # get the remapped location
    if remap_has_key( loc ) :
        remap = Gps_remap.query.get( loc )
        loc = remap.to_location
    # if we've cached this loc, go for it
    if cache_has_key( loc ) :
        cache = Gps_cache.query.get( loc )
        return { 'lat' : cache.latitude, 'lon' : cache.longitude }
    # if we haven't cached anything, go look it up and throw an exception if it fails
    coder = geocoders.GoogleV3()
    try :
        result = coder.geocode( loc, exactly_one = False )
        if (result == None) :
            return None
        place, (lat,lon) = result[0]
        return { 'lat': lat, 'lon' : lon }
        if cache_result :
            new_cache = Gps_cache( location = loc, latitude=lat, longitude=lon )
            db.session.add( new_cache )
            db.session.commit()
    except e :
        return e

def get_locations_and_unknowns( locs ) :
    # like get_location, but a list; returns a dictionary mapping locs to lat/lon
    # pairs AND a list of unknowns (locs)
    locations = {}
    unknowns = []
    for loc in locs :
        this_result = get_location(loc)
        if this_result == None :
            unknowns.append( loc )
        else :
            locations[loc] = this_result
    return locations, unknowns
