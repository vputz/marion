from tutorial.models import db, Gps_cache, Gps_remap
from geopy import geocoders
from geopy.exc import GeopyError

# TODO: deal with case


def remap_has_key(loc):
    return Gps_remap.query.get(loc) is not None


def cache_has_key(loc):
    return Gps_cache.query.get(loc) is not None


def next_guess(name):
    """
    Takes the name in question assuming it to be an
    address of the form "university, department, address, country"
    and return a simplified version with just the beginning
    and ends
    """
    parts = [s.strip() for s in name.split(",")]
    if len(parts) > 1:
        return ", ".join(parts[1:])
    else:
        raise ValueError('name cannot be split further')


def gps_query(loc):
    """can throw GeopyError"""
    coder = geocoders.GoogleV3()
    partial = coder.geocode(loc, exactly_one=False)
    if (partial is None):
        result = None
    else:
        place, (lat, lon) = partial[0]
        result = {'lat': lat, 'lon': lon}
    return result


def successive_gps_query(loc):
    guess = loc
    result = gps_query(guess)
    while result is None:
        guess = next_guess(guess)
        result = gps_query(guess)
    return result


def get_location(loc, cache_result=False):
    if isinstance(loc, bytes):
        loc = loc.decode('utf-8')
    # get the remapped location
    if remap_has_key(loc):
        remap = Gps_remap.query.get(loc)
        loc = remap.to_location
    # if we've cached this loc, go for it
    if cache_has_key(loc):
        cache = Gps_cache.query.get(loc)
        return {'lat': cache.latitude, 'lon': cache.longitude}
    # if we haven't cached anything, go look it up and
    # throw an exception if it fails
    result = None

    try:
        result = successive_gps_query(loc)
    except (GeopyError, ValueError) as e:
        result = None
    if cache_result is True and result is not None:
        new_cache = Gps_cache(location=loc, latitude=result['lat'],
                              longitude=result['lon'])
        db.session.add(new_cache)
        db.session.commit()
    return result


def get_locations_and_unknowns(locs, cache_result=True):
    # like get_location, but a list; returns a dictionary
    # mapping locs to lat/lon
    # pairs AND a list of unknowns (locs)
    locations = {}
    unknowns = []
    for loc in locs:
        this_result = get_location(loc, cache_result)
        if this_result is None:
            unknowns.append(loc)
        else:
            locations[loc] = this_result
    return locations, unknowns


def get_locations_and_unknowns_nocache(locs):
    """ included for testing """
    return get_locations_and_unknowns(locs, False)
