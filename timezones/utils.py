from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_str
from django.contrib.gis.geos import Point

import pytz
import re


def localtime_for_timezone(value, timezone):
    """
    Given a ``datetime.datetime`` object in UTC and a timezone represented as
    a string, return the localized time for the timezone.
    """
    return adjust_datetime_to_timezone(value, settings.TIME_ZONE, timezone)


def adjust_datetime_to_timezone(value, from_tz, to_tz=None):
    """
    Given a ``datetime`` object adjust it according to the from_tz timezone
    string into the to_tz timezone string.
    """
    if to_tz is None:
        to_tz = settings.TIME_ZONE
    if value.tzinfo is None:
        if not hasattr(from_tz, "localize"):
            from_tz = pytz.timezone(smart_str(from_tz))
        value = from_tz.localize(value)
    return value.astimezone(pytz.timezone(smart_str(to_tz)))


def coerce_timezone_value(value):
    try:
        return pytz.timezone(value)
    except pytz.UnknownTimeZoneError:
        raise ValidationError("Unknown timezone")


def validate_timezone_max_length(max_length, zones):
    def reducer(x, y):
        return x and (len(y) <= max_length)
    if not reduce(reducer, zones, True):
        raise Exception("timezones.fields.TimeZoneField MAX_TIMEZONE_LENGTH is too small")


# for reading coordinates out of zone.tab
COORDINATES_RE = re.compile(r"""^
    (?P<lat_sign>[+-])
    (?P<lat_degrees>\d\d)
    (?P<lat_minutes>\d\d)
    (?P<lat_seconds>\d\d)?
    (?P<lng_sign>[+-])
    (?P<lng_degrees>\d\d\d)
    (?P<lng_minutes>\d\d)
    (?P<lng_seconds>\d\d)?
    $""", re.VERBOSE)
WGS84_SRID = 4326
_coordinates = None # saved coordinates
def _dms_to_point(coordinates):
    m = COORDINATES_RE.match(coordinates)
    lat = (int(m.group('lat_degrees')) +
        (int(m.group('lat_minutes')) * 60 +
            int(m.group('lat_seconds') or 0)) / 3600.0)
    if m.group('lat_sign') == '-':
        lat = -lat
    lng = (int(m.group('lng_degrees')) +
        (int(m.group('lng_minutes')) * 60 +
            int(m.group('lng_seconds') or 0)) / 3600.0)
    if m.group('lng_sign') == '-':
        lng = -lng
    return Point(lng, lat, srid=WGS84_SRID)

def get_timezone_coordinates(timezone):
    global _coordinates
    if not _coordinates:
        _coordinates = {}
        zone_tab = pytz.open_resource('zone.tab')
        for line in zone_tab.readlines():
            if line.startswith('#'):
                continue
            code, coordinates, zone = line.split(None, 4)[:3]
            _coordinates[zone] = _dms_to_point(coordinates)
    if hasattr(timezone, 'zone'):
        return _coordinates.get(timezone.zone)
    return _coordinates.get(timezone)

