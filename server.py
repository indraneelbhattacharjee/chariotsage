#!/usr/bin/env python3
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from functools import lru_cache

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'PyJHora/src'))

from jhora.horoscope.info import Horoscope
from jhora.horoscope.dhasa.graha.vimsottari import get_vimsottari_dhasa_bhukthi
from jhora import utils

# Load cities database
CITIES_DB = {}
try:
    with open(os.path.join(ROOT, 'cities.json'), 'r') as f:
        CITIES_DB = json.load(f).get('cities', {})
except Exception:
    pass

ZODIAC_ORDER = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]
ZODIAC_SYMBOLS = {
    '♈': 'Aries', '♉': 'Taurus', '♊': 'Gemini', '♋': 'Cancer', '♌': 'Leo', '♍': 'Virgo',
    '♎': 'Libra', '♏': 'Scorpio', '♐': 'Sagittarius', '♑': 'Capricorn', '♒': 'Aquarius', '♓': 'Pisces'
}
PLACE_DATABASE = os.path.join(ROOT, 'PyJHora/src/jhora/data/geonames_places_5k.db')
PLANET_LABELS = {
    'asc': 'Ascendant', 'lagna': 'Ascendant', 'su': 'Sun', 'sun': 'Sun',
    'mo': 'Moon', 'moon': 'Moon', 'ma': 'Mars', 'mars': 'Mars',
    'me': 'Mercury', 'mercury': 'Mercury', 'ju': 'Jupiter', 'jupiter': 'Jupiter',
    've': 'Venus', 'venus': 'Venus', 'sa': 'Saturn', 'saturn': 'Saturn',
    'ra': 'Rahu', 'rahu': 'Rahu', 'raagu': 'Rahu',
    'ke': 'Ketu', 'ketu': 'Ketu', 'kethu': 'Ketu',
    'ur': 'Uranus', 'uranus': 'Uranus', 'ne': 'Neptune', 'neptune': 'Neptune',
    'pl': 'Pluto', 'pluto': 'Pluto'
}


def parse_birth_date(value: str):
    raw = (value or '').strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError('Please enter a valid birth date.')


def parse_birth_time(value: str):
    raw = (value or '').strip()
    if not raw:
        raise ValueError('Please enter a valid birth time.')
    if ':' not in raw:
        raise ValueError('Please enter a valid birth time.')
    try:
        hh, mm = raw.split(':', 1)[0], raw.split(':', 1)[1]
        hh = int(hh)
        mm = int(str(mm).split()[0])
    except (TypeError, ValueError):
        raise ValueError('Please enter a valid birth time.') from None
    if not 0 <= hh <= 23 or not 0 <= mm <= 59:
        raise ValueError('Please enter a valid birth time.')
    return f'{hh:02d}:{mm:02d}'


def extract_sign(text: str):
    if not text:
        return None
    for symbol, name in ZODIAC_SYMBOLS.items():
        if symbol in text:
            return name
    for sign in ZODIAC_ORDER:
        if sign.lower() in text.lower():
            return sign
    return None


def format_lords(lords):
    if not lords:
        return 'Unknown'
    parts = []
    for value in lords:
        if isinstance(value, int) and 0 <= value < len(utils.PLANET_NAMES):
            parts.append(english_planet_name(utils.PLANET_NAMES[value]) or 'Unknown')
        else:
            parts.append(english_planet_name(value) or str(value))
    return ' / '.join(parts)


def normalize_place_name(pob: str):
    """Normalize place name using cities database for better geocoding."""
    if not pob:
        return 'Kolkata'
    pob_lower = pob.lower().strip()
    
    # First, try exact match in database
    if pob_lower in CITIES_DB:
        return CITIES_DB[pob_lower]
    
    # Try partial match
    for key, value in CITIES_DB.items():
        if key in pob_lower or pob_lower in key:
            return value
    
    # If "new delhi" type case, try to simplify
    if 'new' in pob_lower and 'delhi' in pob_lower:
        return 'Delhi'
    if 'new' in pob_lower and 'york' in pob_lower:
        return 'New York'
    
    # If not found, return original (PyJHora will handle it)
    return pob


def resolve_place(place_name: str):
    """Resolve a selected place locally so chart creation never depends on a web geocoder."""
    search_parts = [part.strip() for part in place_name.split(',') if part.strip()]
    city = search_parts[0] if search_parts else place_name.strip()
    country = search_parts[-1] if len(search_parts) > 1 else ''
    if not city:
        raise ValueError('Please select or enter a place of birth.')

    with sqlite3.connect(PLACE_DATABASE) as connection:
        connection.row_factory = sqlite3.Row
        if country:
            row = connection.execute(
                """SELECT display_label, latitude, longitude, timezone_hours
                   FROM places
                   WHERE lower(place_name) = lower(?) AND lower(country) = lower(?)
                   ORDER BY CASE WHEN lower(display_label) = lower(?) THEN 0 ELSE 1 END
                   LIMIT 1""",
                (city, country, place_name)
            ).fetchone()
        else:
            row = connection.execute(
                """SELECT display_label, latitude, longitude, timezone_hours
                   FROM places WHERE lower(place_name) = lower(?) LIMIT 1""",
                (city,)
            ).fetchone()

        if row is None:
            row = connection.execute(
                """SELECT display_label, latitude, longitude, timezone_hours
                   FROM places WHERE lower(display_label) LIKE lower(?) LIMIT 1""",
                (f'{city}%',)
            ).fetchone()
    if row is None:
        raise ValueError('That place was not found. Try a nearby city or a more specific name.')
    return row['display_label'], row['latitude'], row['longitude'], row['timezone_hours']


def english_planet_name(raw_name):
    cleaned = re.sub(r'[^A-Za-z ]', '', str(raw_name)).strip().lower()
    if not cleaned:
        return None
    for key in sorted(PLANET_LABELS, key=len, reverse=True):
        if cleaned == key or cleaned.startswith(key):
            return PLANET_LABELS[key]
    return cleaned.title()


def extract_planets_from_bhava(bhava_chart_info: list):
    """Extract planets from bhava_chart_info and map to houses."""
    planets_by_house = {}
    if not bhava_chart_info:
        return planets_by_house
    
    for bhava_info in bhava_chart_info:
        try:
            house_name = bhava_info[0]  # e.g., 'House-1'
            planets_str = bhava_info[4] if len(bhava_info) > 4 else ''  # e.g., 'Ascℒ\nJu♃'
            
            if not house_name.startswith('House-'):
                continue
            
            house_num = int(house_name.split('-')[1])
            
            # Parse planets from the string
            planets_list = []
            if planets_str:
                # Split by newline and clean up
                planet_items = planets_str.split('\n')
                for item in planet_items:
                    item = item.strip()
                    if item:
                        english_name = english_planet_name(item)
                        if english_name:
                            planets_list.append(english_name)
            
            planets_by_house[house_num] = planets_list
        except Exception:
            continue
    
    return planets_by_house


def build_chart_payload(payload: dict):
    name = (payload.get('name') or 'Seeker').strip() or 'Seeker'
    dob = parse_birth_date(payload.get('dob'))
    tob = parse_birth_time(payload.get('tob'))
    pob = normalize_place_name((payload.get('pob') or '').strip())
    chart_type = (payload.get('chartType') or 'lagna').strip().lower()

    pob, latitude, longitude, timezone_offset = resolve_place(pob)
    horoscope = Horoscope(
        place_with_country_code=pob,
        latitude=latitude,
        longitude=longitude,
        timezone_offset=timezone_offset,
        date_in=dob,
        birth_time=tob,
        language='en'
    )
    
    chart_info = horoscope.get_horoscope_information_for_chart()
    chart_data = chart_info[0] if isinstance(chart_info, tuple) and chart_info else {}

    asc_sign = extract_sign(chart_data.get('Custom Kundali (Dn)-Ascendantℒ', '')) or 'Aries'
    moon_sign = extract_sign(chart_data.get('Custom Kundali (Dn)-Moon☾', '')) or 'Cancer'
    sun_sign = extract_sign(chart_data.get('Custom Kundali (Dn)-Sun☉', '')) or 'Leo'
    base_sign = moon_sign if chart_type == 'moon' else asc_sign

    # Extract planets in houses from bhava_chart_info
    planets_by_house = extract_planets_from_bhava(horoscope.bhava_chart_info)

    start_index = ZODIAC_ORDER.index(base_sign)
    houses = []
    for index in range(12):
        house_num = index + 1
        sign = ZODIAC_ORDER[(start_index + index) % 12]
        planets_in_house = planets_by_house.get(house_num, [])
        houses.append({
            'house': house_num,
            'signNumber': ZODIAC_ORDER.index(sign) + 1,
            'sign': sign,
            'planets': planets_in_house,
            'planet': 'Ascendant' if index == 0 else 'House'
        })

    dasha_result = get_vimsottari_dhasa_bhukthi(horoscope.julian_day, horoscope.Place)
    dasha_entries = dasha_result[1][:6] if isinstance(dasha_result, tuple) and len(dasha_result) > 1 else []
    dasha_sequence = []
    for entry in dasha_entries[:6]:
        dasha_sequence.append(format_lords(entry[0]))

    return {
        'name': name,
        'place': pob,
        'dob': payload.get('dob') or 'Birth date',
        'tob': payload.get('tob') or 'Time of birth',
        'type': chart_type,
        'ascSign': asc_sign,
        'moonSign': moon_sign,
        'sunSign': sun_sign,
        'houseNumber': 1,
        'planet': 'Moon' if chart_type == 'moon' else 'Ascendant',
        'houses': houses,
        'currentDasha': dasha_sequence[0] if dasha_sequence else 'Vimshottari',
        'nextDasha': dasha_sequence[1] if len(dasha_sequence) > 1 else 'Awaiting',
        'subDasha': dasha_sequence[2] if len(dasha_sequence) > 2 else 'Awaiting',
        'sequence': dasha_sequence,
        'highlights': [
            f'{"Moon" if chart_type == "moon" else "Lagna"} is anchored in {base_sign}.',
            f'Sun is moving through {sun_sign}, adding clarity and direction.',
            f'The engine shows a strong {moon_sign} influence for the natal atmosphere.'
        ]
    }


class ChartRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self._send_json({'ok': True, 'service': 'chariot-sage-chart'})
            return
        if self.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            with open(os.path.join(ROOT, 'index.html'), 'rb') as handle:
                self.wfile.write(handle.read())
            return
        if self.path.startswith('/styles.css') or self.path.startswith('/script.js'):
            filename = self.path.lstrip('/')
            self.send_response(200)
            content_type = 'text/css; charset=utf-8' if filename.endswith('.css') else 'application/javascript; charset=utf-8'
            self.send_header('Content-Type', content_type)
            self.end_headers()
            with open(os.path.join(ROOT, filename), 'rb') as handle:
                self.wfile.write(handle.read())
            return
        self.send_error(404, 'Not Found')

    def do_POST(self):
        if self.path != '/api/chart':
            self.send_error(404, 'Not Found')
            return
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length).decode('utf-8') if length else '{}'
        try:
            payload = json.loads(body or '{}')
        except json.JSONDecodeError:
            self.send_error(400, 'Invalid JSON')
            return
        try:
            self._send_json(build_chart_payload(payload))
        except ValueError as error:
            self._send_json({'error': str(error)}, status=400)
        except Exception:
            self._send_json(
                {'error': 'The astrology engine could not complete this chart. Please verify the details and try again.'},
                status=500
            )

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def main():
    port = int(os.getenv('PORT', '3000'))
    server = ThreadingHTTPServer(('127.0.0.1', port), ChartRequestHandler)
    print(f'Starting Chariot Sage chart server on http://127.0.0.1:{port}')
    server.serve_forever()


if __name__ == '__main__':
    main()
