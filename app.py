#!/usr/bin/env python3
"""
Aviation Weather API Add-on for Home Assistant
Provides METAR and TAF data from aviationweather.gov
"""

import os
import json
import time
import logging
import threading
import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Dict, List, Tuple
import requests
from flask import Flask, render_template, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

# Initialize Flask app
app = Flask(__name__)

# Add ProxyFix middleware for Ingress support
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Enable CORS and set up for Ingress
@app.before_request
def log_request_info():
    """Log all incoming requests for debugging"""
    logger.debug(f"Request: {request.method} {request.path} from {request.remote_addr}")
    logger.debug(f"Headers: {dict(request.headers)}")

@app.after_request
def after_request(response):
    """Add headers for Ingress compatibility"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    logger.debug(f"Response: {response.status_code} {response.content_type}")
    return response

# Global error handler to ensure JSON responses
@app.errorhandler(Exception)
def handle_error(error):
    """Handle all unhandled exceptions and return JSON"""
    logger.error(f"Unhandled exception: {error}", exc_info=True)
    response = jsonify({
        'status': 'error',
        'message': f'Internal server error: {str(error)}'
    })
    response.headers['Content-Type'] = 'application/json'
    return response, 500

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'info').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "https://aviationweather.gov/api/data"
USER_AGENT = "HomeAssistant-AviationWeather/1.0"
CACHE_FILE = "/data/weather_cache.json"
HASS_API_URL = "http://supervisor/core/api"

# In-memory cache
weather_cache = {
    'metar': {},
    'taf': {},
    'last_update': None
}


def load_cache():
    """Load cached weather data from disk"""
    global weather_cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                weather_cache = json.load(f)
                logger.info("Cache loaded successfully")
    except Exception as e:
        logger.error(f"Error loading cache: {e}")


def save_cache():
    """Save weather data to disk"""
    try:
        os.makedirs('/data', exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(weather_cache, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving cache: {e}")


def read_options():
    """Read add-on options from options.json"""
    try:
        with open('/data/options.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("Options file not found, using defaults")
        return {
            'airport_codes': [],
            'update_interval': 30,
            'include_taf': True,
            'log_level': 'info',
            'create_sensors': False,
            'sensor_airport': 'auto'
        }
    except Exception as e:
        logger.error(f"Error reading options: {e}")
        return {}


def get_ha_location() -> Optional[Tuple[float, float]]:
    """Get Home Assistant's latitude and longitude from Supervisor API"""
    try:
        # First try to get from Supervisor API
        supervisor_token = os.getenv('SUPERVISOR_TOKEN')
        if supervisor_token:
            headers = {
                'Authorization': f'Bearer {supervisor_token}',
                'Content-Type': 'application/json'
            }
            
            # Get core config which includes location
            response = requests.get(
                'http://supervisor/core/api/config',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                config = response.json()
                lat = config.get('latitude')
                lon = config.get('longitude')
                if lat and lon:
                    logger.info(f"Got HA location: {lat}, {lon}")
                    return (float(lat), float(lon))
        
        logger.warning("Could not get HA location from Supervisor")
        return None
        
    except Exception as e:
        logger.error(f"Error getting HA location: {e}", exc_info=True)
        return None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on earth in kilometers
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


def find_nearest_airport(ha_location: Tuple[float, float], airport_list: List[str]) -> Optional[str]:
    """
    Find the nearest airport to HA location from a list of airport codes
    Returns the closest airport code
    """
    if not ha_location or not airport_list:
        return None
    
    ha_lat, ha_lon = ha_location
    closest_airport = None
    closest_distance = float('inf')
    
    for airport_code in airport_list:
        try:
            # Fetch METAR to get airport location
            metar = fetch_metar(airport_code)
            if metar and 'lat' in metar and 'lon' in metar:
                airport_lat = float(metar['lat'])
                airport_lon = float(metar['lon'])
                
                distance = haversine_distance(ha_lat, ha_lon, airport_lat, airport_lon)
                logger.debug(f"{airport_code}: {distance:.2f} km away")
                
                if distance < closest_distance:
                    closest_distance = distance
                    closest_airport = airport_code
        except Exception as e:
            logger.error(f"Error checking distance for {airport_code}: {e}")
            continue
    
    if closest_airport:
        logger.info(f"Nearest airport: {closest_airport} ({closest_distance:.2f} km)")
    
    return closest_airport


def create_ha_sensors(metar_data: Dict, airport_code: str) -> bool:
    """
    Create/Update Home Assistant sensor entities from METAR data via Supervisor API
    """
    try:
        supervisor_token = os.getenv('SUPERVISOR_TOKEN')
        if not supervisor_token:
            logger.error("No SUPERVISOR_TOKEN available")
            return False
        
        headers = {
            'Authorization': f'Bearer {supervisor_token}',
            'Content-Type': 'application/json'
        }
        
        # Base entity ID
        base_id = f"aviation_weather_{airport_code.lower()}"
        
        # Define sensors to create
        sensors = []
        
        # Temperature
        if 'temp' in metar_data:
            sensors.append({
                'entity_id': f'sensor.{base_id}_temperature',
                'state': metar_data['temp'],
                'attributes': {
                    'unit_of_measurement': '°C',
                    'device_class': 'temperature',
                    'friendly_name': f'{airport_code} Temperature',
                    'icon': 'mdi:thermometer',
                    'temp_f': round(metar_data['temp'] * 9/5 + 32, 1)
                }
            })
        
        # Dewpoint
        if 'dewp' in metar_data:
            sensors.append({
                'entity_id': f'sensor.{base_id}_dewpoint',
                'state': metar_data['dewp'],
                'attributes': {
                    'unit_of_measurement': '°C',
                    'device_class': 'temperature',
                    'friendly_name': f'{airport_code} Dewpoint',
                    'icon': 'mdi:water-thermometer',
                    'dewp_f': round(metar_data['dewp'] * 9/5 + 32, 1)
                }
            })
        
        # Wind Speed
        if 'wspd' in metar_data:
            sensors.append({
                'entity_id': f'sensor.{base_id}_wind_speed',
                'state': metar_data['wspd'],
                'attributes': {
                    'unit_of_measurement': 'kt',
                    'friendly_name': f'{airport_code} Wind Speed',
                    'icon': 'mdi:weather-windy',
                    'wind_gust': metar_data.get('wgst')
                }
            })
        
        # Wind Direction
        if 'wdir' in metar_data:
            sensors.append({
                'entity_id': f'sensor.{base_id}_wind_bearing',
                'state': metar_data['wdir'],
                'attributes': {
                    'unit_of_measurement': '°',
                    'friendly_name': f'{airport_code} Wind Direction',
                    'icon': 'mdi:compass'
                }
            })
        
        # Pressure (Altimeter)
        if 'altim' in metar_data:
            sensors.append({
                'entity_id': f'sensor.{base_id}_pressure',
                'state': round(metar_data['altim'] * 33.8639, 1),  # Convert inHg to hPa
                'attributes': {
                    'unit_of_measurement': 'hPa',
                    'device_class': 'atmospheric_pressure',
                    'friendly_name': f'{airport_code} Pressure',
                    'icon': 'mdi:gauge',
                    'altimeter_inhg': metar_data['altim']
                }
            })
        
        # Visibility
        if 'visib' in metar_data:
            sensors.append({
                'entity_id': f'sensor.{base_id}_visibility',
                'state': round(metar_data['visib'] * 1.60934, 1),  # Convert SM to km
                'attributes': {
                    'unit_of_measurement': 'km',
                    'friendly_name': f'{airport_code} Visibility',
                    'icon': 'mdi:eye',
                    'visibility_sm': metar_data['visib']
                }
            })
        
        # Flight Category
        if 'flightCategory' in metar_data:
            sensors.append({
                'entity_id': f'sensor.{base_id}_flight_category',
                'state': metar_data['flightCategory'],
                'attributes': {
                    'friendly_name': f'{airport_code} Flight Category',
                    'icon': 'mdi:airplane'
                }
            })
        
        # Weather Condition
        if metar_data.get('wxDecoded'):
            sensors.append({
                'entity_id': f'sensor.{base_id}_condition',
                'state': metar_data['wxDecoded'],
                'attributes': {
                    'friendly_name': f'{airport_code} Weather Condition',
                    'icon': 'mdi:weather-partly-cloudy',
                    'raw_wx': metar_data.get('wxString', '')
                }
            })
        
        # Raw METAR
        if 'rawOb' in metar_data:
            sensors.append({
                'entity_id': f'sensor.{base_id}_raw_metar',
                'state': metar_data['rawOb'][:255],  # HA state max 255 chars
                'attributes': {
                    'friendly_name': f'{airport_code} Raw METAR',
                    'icon': 'mdi:text',
                    'full_metar': metar_data['rawOb'],
                    'observation_time': metar_data.get('obsTime')
                }
            })
        
        # Create/update each sensor
        success_count = 0
        for sensor in sensors:
            try:
                response = requests.post(
                    f'http://supervisor/core/api/states/{sensor["entity_id"]}',
                    headers=headers,
                    json={
                        'state': sensor['state'],
                        'attributes': sensor['attributes']
                    },
                    timeout=5
                )
                
                if response.status_code in [200, 201]:
                    success_count += 1
                    logger.debug(f"Created/updated {sensor['entity_id']}")
                else:
                    logger.warning(f"Failed to create {sensor['entity_id']}: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error creating sensor {sensor['entity_id']}: {e}")
        
        logger.info(f"Created/updated {success_count}/{len(sensors)} sensors for {airport_code}")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error creating HA sensors: {e}", exc_info=True)
        return False


def map_metar_to_ha_condition(wx_string: str, flight_category: str) -> str:
    """Map METAR weather codes to Home Assistant weather conditions"""
    if not wx_string:
        # Use flight category as fallback
        if flight_category == 'VFR':
            return 'sunny'
        elif flight_category == 'MVFR':
            return 'partlycloudy'
        elif flight_category in ['IFR', 'LIFR']:
            return 'cloudy'
        return 'sunny'
    
    wx_lower = wx_string.lower()
    
    # Thunderstorms
    if 'ts' in wx_lower or 'tsra' in wx_lower:
        if 'ra' in wx_lower:
            return 'lightning-rainy'
        return 'lightning'
    
    # Precipitation types
    if 'sn' in wx_lower or 'sg' in wx_lower or 'ic' in wx_lower:
        if 'ra' in wx_lower:
            return 'snowy-rainy'
        return 'snowy'
    
    if 'pl' in wx_lower or 'gr' in wx_lower or 'gs' in wx_lower:
        return 'hail'
    
    if '+ra' in wx_lower or 'shra' in wx_lower:
        return 'pouring'
    
    if 'ra' in wx_lower or 'dz' in wx_lower:
        return 'rainy'
    
    if 'fg' in wx_lower or 'br' in wx_lower or 'mifg' in wx_lower:
        return 'fog'
    
    # Wind conditions
    # Check flight category for wind-heavy conditions
    if flight_category in ['IFR', 'LIFR']:
        return 'cloudy'
    elif flight_category == 'MVFR':
        return 'partlycloudy'
    
    return 'sunny'


def create_ha_weather_entity(metar_data: Dict, taf_data: Optional[Dict], airport_code: str) -> bool:
    """Create/update a Home Assistant weather entity"""
    try:
        supervisor_token = os.environ.get('SUPERVISOR_TOKEN')
        if not supervisor_token:
            logger.error("SUPERVISOR_TOKEN not available")
            return False
        
        headers = {
            'Authorization': f'Bearer {supervisor_token}',
            'Content-Type': 'application/json'
        }
        
        base_id = f'aviation_weather_{airport_code.lower()}'
        entity_id = f'weather.{base_id}'
        
        # Map METAR to HA weather condition
        wx_string = metar_data.get('wxString', '')
        flight_category = metar_data.get('flightCategory', 'VFR')
        condition = map_metar_to_ha_condition(wx_string, flight_category)
        
        # Build weather entity state
        weather_state = {
            'state': condition,
            'attributes': {
                'friendly_name': f'{airport_code} Aviation Weather',
                'attribution': 'Data provided by Aviation Weather Center',
                'station': airport_code.upper(),
                'observation_time': metar_data.get('obsTime'),
                'observation_time_local': metar_data.get('obsTimeLocal')
            }
        }
        
        # Required: Temperature (convert from C to match HA preference)
        if 'temp' in metar_data and metar_data['temp'] is not None:
            weather_state['attributes']['temperature'] = float(metar_data['temp'])
            weather_state['attributes']['temperature_unit'] = '°C'
        
        # Optional: Humidity
        if 'humidity' in metar_data and metar_data['humidity'] is not None:
            weather_state['attributes']['humidity'] = float(metar_data['humidity'])
        
        # Optional: Pressure (use altimHpa if available, otherwise press)
        pressure_hpa = metar_data.get('altimHpa') or metar_data.get('press')
        if pressure_hpa:
            weather_state['attributes']['pressure'] = float(pressure_hpa)
            weather_state['attributes']['pressure_unit'] = 'hPa'
        
        # Optional: Wind speed (convert from knots to km/h for HA)
        if 'wspd' in metar_data and metar_data['wspd'] is not None:
            # 1 knot = 1.852 km/h
            wind_speed_kmh = float(metar_data['wspd']) * 1.852
            weather_state['attributes']['wind_speed'] = round(wind_speed_kmh, 1)
            weather_state['attributes']['wind_speed_unit'] = 'km/h'
            weather_state['attributes']['wind_speed_kt'] = float(metar_data['wspd'])
        
        # Optional: Wind gust
        if 'wgst' in metar_data and metar_data['wgst'] is not None:
            wind_gust_kmh = float(metar_data['wgst']) * 1.852
            weather_state['attributes']['wind_gust_speed'] = round(wind_gust_kmh, 1)
        
        # Optional: Wind bearing
        if 'wdir' in metar_data and metar_data['wdir'] is not None:
            weather_state['attributes']['wind_bearing'] = float(metar_data['wdir'])
        
        # Optional: Visibility (convert from SM to km)
        if 'visib' in metar_data and metar_data['visib'] is not None:
            # 1 SM = 1.60934 km
            visibility_km = float(metar_data['visib']) * 1.60934
            weather_state['attributes']['visibility'] = round(visibility_km, 1)
            weather_state['attributes']['visibility_unit'] = 'km'
            weather_state['attributes']['visibility_sm'] = float(metar_data['visib'])
        
        # Optional: Cloud coverage (percentage from sky cover)
        cloud_coverage = None
        if 'cover' in metar_data:
            cover_map = {
                'SKC': 0, 'CLR': 0, 'NSC': 0, 'CAVOK': 0,
                'FEW': 25, 'SCT': 50, 'BKN': 75, 'OVC': 100, 'VV': 100
            }
            cloud_coverage = cover_map.get(metar_data['cover'])
        
        if cloud_coverage is not None:
            weather_state['attributes']['cloud_coverage'] = cloud_coverage
        
        # Optional: Dewpoint
        if 'dewp' in metar_data and metar_data['dewp'] is not None:
            weather_state['attributes']['dew_point'] = float(metar_data['dewp'])
        
        # Additional aviation-specific attributes
        weather_state['attributes']['flight_category'] = flight_category
        weather_state['attributes']['raw_metar'] = metar_data.get('rawOb', '')
        
        if metar_data.get('wxDecoded'):
            weather_state['attributes']['weather_decoded'] = metar_data['wxDecoded']
        
        if metar_data.get('cloudLayers'):
            weather_state['attributes']['cloud_layers'] = metar_data['cloudLayers']
        
        # Add forecast if TAF is available
        if taf_data and 'decodedForecasts' in taf_data:
            forecast_periods = []
            for period in taf_data['decodedForecasts'][:8]:  # Limit to 8 periods
                forecast_item = {
                    'datetime': period.get('fromTime'),
                    'condition': map_metar_to_ha_condition(
                        period.get('wxString', ''),
                        period.get('flightCategory', 'VFR')
                    )
                }
                
                # Add temperature if available
                if 'temp' in period and period['temp'] is not None:
                    forecast_item['temperature'] = float(period['temp'])
                
                # Add wind
                if 'wspd' in period and period['wspd'] is not None:
                    forecast_item['wind_speed'] = round(float(period['wspd']) * 1.852, 1)
                
                if 'wdir' in period and period['wdir'] is not None:
                    forecast_item['wind_bearing'] = float(period['wdir'])
                
                # Add visibility
                if 'visib' in period and period['visib'] is not None:
                    forecast_item['visibility'] = round(float(period['visib']) * 1.60934, 1)
                
                forecast_periods.append(forecast_item)
            
            if forecast_periods:
                weather_state['attributes']['forecast'] = forecast_periods
        
        # Create/update weather entity
        response = requests.post(
            f'http://supervisor/core/api/states/{entity_id}',
            headers=headers,
            json=weather_state,
            timeout=5
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"Created/updated weather entity {entity_id}")
            return True
        else:
            logger.warning(f"Failed to create weather entity {entity_id}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating weather entity: {e}", exc_info=True)
        return False


def decode_weather_codes(wx_string: str) -> str:
    """Decode weather phenomenon codes into human-readable text"""
    if not wx_string:
        return ""
    
    # Weather descriptors
    descriptors = {
        'MI': 'Shallow', 'PR': 'Partial', 'BC': 'Patches', 'DR': 'Low Drifting',
        'BL': 'Blowing', 'SH': 'Shower(s)', 'TS': 'Thunderstorm', 'FZ': 'Freezing'
    }
    
    # Weather phenomena
    phenomena = {
        'DZ': 'Drizzle', 'RA': 'Rain', 'SN': 'Snow', 'SG': 'Snow Grains',
        'IC': 'Ice Crystals', 'PL': 'Ice Pellets', 'GR': 'Hail', 'GS': 'Small Hail',
        'UP': 'Unknown Precipitation', 'BR': 'Mist', 'FG': 'Fog', 'FU': 'Smoke',
        'VA': 'Volcanic Ash', 'DU': 'Dust', 'SA': 'Sand', 'HZ': 'Haze',
        'PY': 'Spray', 'PO': 'Dust Whirls', 'SQ': 'Squalls', 'FC': 'Funnel Cloud',
        'SS': 'Sandstorm', 'DS': 'Duststorm'
    }
    
    # Intensity
    intensity = ''
    if wx_string.startswith('-'):
        intensity = 'Light '
        wx_string = wx_string[1:]
    elif wx_string.startswith('+'):
        intensity = 'Heavy '
        wx_string = wx_string[1:]
    
    decoded = intensity
    
    # Check for descriptor
    for code, desc in descriptors.items():
        if wx_string.startswith(code):
            decoded += desc + ' '
            wx_string = wx_string[len(code):]
            break
    
    # Decode phenomena
    remaining = wx_string
    while remaining:
        found = False
        for code, desc in phenomena.items():
            if remaining.startswith(code):
                decoded += desc + ' '
                remaining = remaining[len(code):]
                found = True
                break
        if not found:
            break
    
    return decoded.strip() or wx_string


def convert_to_local_time(utc_time_str) -> Dict[str, str]:
    """Convert UTC timestamp to local time with multiple formats"""
    try:
        if not utc_time_str:
            return {'utc': '', 'local': '', 'local_short': ''}
        
        # Handle Unix timestamp (integer or numeric string)
        if isinstance(utc_time_str, (int, float)):
            utc_dt = datetime.fromtimestamp(utc_time_str, tz=timezone.utc)
        elif isinstance(utc_time_str, str):
            # Try parsing as Unix timestamp first
            try:
                timestamp = int(utc_time_str)
                utc_dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (ValueError, OverflowError):
                # Parse ISO format timestamp
                if 'T' in utc_time_str:
                    utc_dt = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
                else:
                    # Try parsing other common formats
                    utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
                    utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        else:
            return {'utc': str(utc_time_str), 'local': str(utc_time_str), 'local_short': str(utc_time_str)}
        
        # Convert to local timezone (get from system)
        local_dt = utc_dt.astimezone()
        
        return {
            'utc': utc_dt.strftime('%Y-%m-%d %H:%M UTC'),
            'local': local_dt.strftime('%Y-%m-%d %H:%M %Z'),
            'local_short': local_dt.strftime('%m/%d %H:%M'),
            'iso': local_dt.isoformat()
        }
    except Exception as e:
        logger.error(f"Error converting time {utc_time_str}: {e}")
        return {'utc': str(utc_time_str), 'local': str(utc_time_str), 'local_short': str(utc_time_str)}


def decode_taf_forecast(taf_data: Dict) -> List[Dict]:
    """Decode TAF forecast periods into readable segments"""
    forecasts = []
    
    try:
        # Helper: convert wind direction (deg) to cardinal
        def deg_to_cardinal(deg: Optional[float]) -> Optional[str]:
            try:
                if deg is None:
                    return None
                dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                        'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
                ix = int((deg % 360) / 22.5 + 0.5) % 16
                return dirs[ix]
            except Exception:
                return None
        
        if 'forecast' not in taf_data and 'fcsts' not in taf_data:
            logger.warning(f"No 'forecast' or 'fcsts' key in TAF data. Keys available: {list(taf_data.keys())}")
            return forecasts
        
        # API uses 'fcsts' as the field name for forecast periods
        periods = taf_data.get('fcsts') or taf_data.get('forecast', [])
        
        if not periods:
            logger.warning(f"TAF forecast periods list is empty")
            return forecasts
        
        logger.info(f"Decoding {len(periods)} TAF forecast periods")
        
        for period in periods:
            decoded_period = {
                'raw': period.get('raw', ''),
                'type': period.get('fcstChange') or period.get('fcstType', 'Base'),
                'wind': None,
                'visibility': None,
                'weather': None,
                'clouds': [],
                'valid_from': None,
                'valid_to': None
            }
            
            # Time validity - API uses timeFrom/timeTo (Unix timestamps)
            if 'timeFrom' in period:
                times = convert_to_local_time(period['timeFrom'])
                decoded_period['valid_from'] = times['local_short']
                decoded_period['valid_from_full'] = times['local']
            elif 'validTimeFrom' in period:
                times = convert_to_local_time(period['validTimeFrom'])
                decoded_period['valid_from'] = times['local_short']
                decoded_period['valid_from_full'] = times['local']
            
            if 'timeTo' in period:
                times = convert_to_local_time(period['timeTo'])
                decoded_period['valid_to'] = times['local_short']
                decoded_period['valid_to_full'] = times['local']
            elif 'validTimeTo' in period:
                times = convert_to_local_time(period['validTimeTo'])
                decoded_period['valid_to'] = times['local_short']
                decoded_period['valid_to_full'] = times['local']
            
            # Wind
            if 'wdir' in period and 'wspd' in period:
                wdir = period.get('wdir')
                wspd = period.get('wspd')
                wgst = period.get('wgst')
                wind_txt = None
                if wspd is not None:
                    if wdir in (None, 0):
                        # Variable wind when direction missing/0
                        wind_txt = f"VRB at {wspd} kt"
                    else:
                        card = deg_to_cardinal(wdir)
                        wind_txt = f"{wdir}° ({card}) at {wspd} kt" if card else f"{wdir}° at {wspd} kt"
                    if wgst:
                        wind_txt += f" gusting {wgst} kt"
                decoded_period['wind'] = wind_txt
                decoded_period['wind_cardinal'] = deg_to_cardinal(wdir)
            
            # Visibility (skip if null/empty)
            if 'visib' in period:
                vis_val = period.get('visib')
                if vis_val is not None:
                    # Normalize to string and strip
                    vis_text = str(vis_val).strip()
                    if vis_text:
                        decoded_period['visibility'] = f"{vis_text} SM"
            
            # Weather
            if 'wxString' in period and period['wxString']:
                decoded_period['weather'] = decode_weather_codes(period['wxString'])
                decoded_period['weather_raw'] = period['wxString']
            
            # Clouds
            if 'clouds' in period and period['clouds']:
                decoded_period['clouds'] = decode_cloud_layers({'clouds': period['clouds']})
            
            # Flight category
            if 'flightCategory' in period:
                decoded_period['flight_category'] = period['flightCategory']
            
            # Build human-friendly summary line for the entire forecast period
            try:
                parts = []
                # Time window
                if decoded_period.get('valid_from') and decoded_period.get('valid_to'):
                    parts.append(f"{decoded_period['valid_from']}–{decoded_period['valid_to']}")
                # Type (FROM/BECMG/TEMPO/PROBxx)
                if decoded_period.get('type'):
                    parts.append(decoded_period['type'])
                # Wind
                if decoded_period.get('wind'):
                    parts.append(f"Wind {decoded_period['wind']}")
                # Visibility
                if decoded_period.get('visibility'):
                    parts.append(f"Vis {decoded_period['visibility']}")
                # Weather
                if decoded_period.get('weather'):
                    parts.append(decoded_period['weather'])
                # Clouds summary (first 2 layers for brevity)
                if decoded_period.get('clouds'):
                    cloud_summaries = []
                    for cl in decoded_period['clouds'][:2]:
                        text = cl.get('cover_text') or cl.get('cover')
                        if cl.get('altitude_agl'):
                            text += f" @ {cl['altitude_agl']}"
                        if cl.get('cloud_type'):
                            text += f" ({cl['cloud_type']})"
                        cloud_summaries.append(text)
                    if cloud_summaries:
                        parts.append("Clouds: " + ", ".join(cloud_summaries))
                decoded_period['summary'] = "; ".join([p for p in parts if p])
            except Exception as _e:
                logger.debug(f"TAF summary build skipped: {_e}")

            forecasts.append(decoded_period)
        
    except Exception as e:
        logger.error(f"Error decoding TAF: {e}", exc_info=True)
    
    return forecasts


def decode_cloud_layers(metar_data: Dict) -> List[Dict]:
    """Decode cloud layer information from METAR data"""
    cloud_layers = []
    
    # Cloud cover codes
    cover_decode = {
        'SKC': 'Sky Clear',
        'CLR': 'Clear',
        'NSC': 'No Significant Clouds',
        'FEW': 'Few',
        'SCT': 'Scattered',
        'BKN': 'Broken',
        'OVC': 'Overcast',
        'VV': 'Vertical Visibility'
    }
    
    # Coverage descriptions
    coverage_detail = {
        'SKC': '0/8 (0%)',
        'CLR': '0/8 (0%)',
        'NSC': '0/8 (0%)',
        'FEW': '1-2/8 (12-25%)',
        # 'SCT': '3-4/8 (37-50%)',  # Removed per requirements
        'BKN': '5-7/8 (62-87%)',
        'OVC': '8/8 (100%)',
        'VV': 'Sky Obscured'
    }
    
    # Cloud types
    cloud_types = {
        'CB': 'Cumulonimbus',
        'TCU': 'Towering Cumulus',
        'CI': 'Cirrus',
        'CC': 'Cirrocumulus',
        'CS': 'Cirrostratus',
        'AC': 'Altocumulus',
        'AS': 'Altostratus',
        'NS': 'Nimbostratus',
        'SC': 'Stratocumulus',
        'ST': 'Stratus',
        'CU': 'Cumulus'
    }
    
    # Parse individual cloud layers from clouds array if available
    if 'clouds' in metar_data and metar_data['clouds']:
        for cloud in metar_data['clouds']:
            layer = {}
            
            if 'cover' in cloud:
                cover_code = cloud['cover']
                layer['cover'] = cover_code
                layer['cover_text'] = cover_decode.get(cover_code, cover_code)
                layer['coverage_detail'] = coverage_detail.get(cover_code, '')
            
            if 'base' in cloud:
                # Base is typically in feet AGL; can be None for SKC
                altitude_ft = cloud['base']
                layer['altitude'] = altitude_ft
                if isinstance(altitude_ft, (int, float)):
                    layer['altitude_agl'] = f"{int(altitude_ft):,} ft AGL"
                    layer['altitude_msl'] = f"~{int(altitude_ft):,} ft"  # Approximate
            
            if 'type' in cloud and cloud['type']:
                cloud_type_code = cloud['type']
                layer['cloud_type'] = cloud_types.get(cloud_type_code, cloud_type_code)
                layer['cloud_type_code'] = cloud_type_code
            
            cloud_layers.append(layer)
    # Only use overall sky cover if no individual cloud layers found
    elif 'cover' in metar_data and metar_data['cover']:
        cover_code = metar_data['cover']
        if cover_code in cover_decode:
            cloud_layers.append({
                'cover': cover_code,
                'cover_text': cover_decode[cover_code],
                'coverage_detail': coverage_detail.get(cover_code, ''),
                'altitude': None,
                'altitude_agl': None,
                'cloud_type': None
            })
    
    # If no cloud layers found but we have ceiling info
    if not cloud_layers and 'ceiling' in metar_data and metar_data['ceiling']:
        cloud_layers.append({
            'cover': 'Ceiling',
            'cover_text': 'Ceiling',
            'altitude': metar_data['ceiling'],
            'altitude_agl': f"{metar_data['ceiling']:,} ft AGL"
        })
    
    return cloud_layers


def fetch_metar(airport_code: str) -> Optional[Dict]:
    """Fetch METAR data for a specific airport"""
    try:
        url = f"{API_BASE_URL}/metar"
        params = {
            'ids': airport_code.upper(),
            'format': 'json'
        }
        headers = {
            'User-Agent': USER_AGENT
        }
        
        logger.debug(f"Fetching METAR for {airport_code}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 204:
            logger.warning(f"No METAR data available for {airport_code}")
            return None
        
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            metar = data[0]
            # Add decoded weather if present
            if 'wxString' in metar and metar['wxString']:
                metar['wxDecoded'] = decode_weather_codes(metar['wxString'])
            # Add decoded cloud layers
            metar['cloudLayers'] = decode_cloud_layers(metar)
            # Convert observation time to local
            if 'obsTime' in metar:
                metar['obsTimeLocal'] = convert_to_local_time(metar['obsTime'])
            # Normalize and compute pressure/altimeter in inHg
            try:
                # Some feeds may provide altimeter as inches (typical ~27-31) or pressure in hPa (~980-1040)
                altim = metar.get('altim')
                press = metar.get('press')

                # Helper to safely convert strings
                def _to_float(v):
                    try:
                        return float(v)
                    except Exception:
                        return None

                altim_f = _to_float(altim)
                press_f = _to_float(press)

                # If altim looks like hPa (greater than 60), convert to inHg
                if altim_f is not None:
                    if altim_f > 60:  # assume hPa
                        metar['altimHpa'] = altim_f
                        metar['altimInHg'] = round(altim_f * 0.02953, 2)
                    else:  # inches of mercury already
                        metar['altimInHg'] = round(altim_f, 2)
                        metar['altimHpa'] = round(altim_f / 0.02953)
                elif press_f is not None:
                    # If only pressure in hPa available
                    metar['altimHpa'] = press_f
                    metar['altimInHg'] = round(press_f * 0.02953, 2)
            except Exception as _e:
                logger.debug(f"Altimeter normalization skipped due to: {_e}")
            return metar
        
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching METAR for {airport_code}: {e}")
        return None


def fetch_taf(airport_code: str) -> Optional[Dict]:
    """Fetch TAF data for a specific airport"""
    try:
        url = f"{API_BASE_URL}/taf"
        params = {
            'ids': airport_code.upper(),
            'format': 'json'
        }
        headers = {
            'User-Agent': USER_AGENT
        }
        
        logger.debug(f"Fetching TAF for {airport_code}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 204:
            logger.warning(f"No TAF data available for {airport_code}")
            return None
        
        response.raise_for_status()
        data = response.json()
        
        if data and len(data) > 0:
            taf = data[0]
            logger.debug(f"TAF data keys for {airport_code}: {list(taf.keys())}")
            if 'fcsts' in taf:
                logger.debug(f"TAF has {len(taf.get('fcsts', []))} forecast periods")
            elif 'forecast' in taf:
                logger.debug(f"TAF has {len(taf.get('forecast', []))} forecast periods")
            else:
                logger.warning(f"TAF data missing 'fcsts' or 'forecast' key for {airport_code}")
            # Add decoded forecast periods
            taf['decodedForecasts'] = decode_taf_forecast(taf)
            # Convert issue time to local
            if 'issueTime' in taf:
                taf['issueTimeLocal'] = convert_to_local_time(taf['issueTime'])
            if 'validTimeFrom' in taf:
                taf['validTimeFromLocal'] = convert_to_local_time(taf['validTimeFrom'])
            if 'validTimeTo' in taf:
                taf['validTimeToLocal'] = convert_to_local_time(taf['validTimeTo'])
            return taf
        
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching TAF for {airport_code}: {e}")
        return None


def update_weather_data():
    """Update weather data for all configured airports"""
    global weather_cache
    
    try:
        options = read_options()
        airport_codes = options.get('airport_codes', [])
        include_taf = options.get('include_taf', True)
        create_sensors = options.get('create_sensors', False)
        sensor_airport_option = options.get('sensor_airport', 'auto')
        
        if not airport_codes:
            logger.info("No airport codes configured")
            return
        
        logger.info(f"Updating weather data for: {', '.join(airport_codes)}")
        
        # Determine sensor airport
        sensor_airport = None
        if create_sensors:
            if sensor_airport_option == 'auto':
                # Find nearest airport to HA location
                ha_location = get_ha_location()
                if ha_location:
                    sensor_airport = find_nearest_airport(ha_location, airport_codes)
                    logger.info(f"Auto-selected sensor airport: {sensor_airport}")
                else:
                    logger.warning("Could not get HA location for auto-select, using first airport")
                    sensor_airport = airport_codes[0] if airport_codes else None
            elif sensor_airport_option.upper() in [a.upper() for a in airport_codes]:
                sensor_airport = sensor_airport_option.upper()
                logger.info(f"Using configured sensor airport: {sensor_airport}")
            else:
                logger.warning(f"Configured sensor airport {sensor_airport_option} not in airport list")
                sensor_airport = airport_codes[0] if airport_codes else None
        
        for airport in airport_codes:
            try:
                # Fetch METAR
                metar_data = fetch_metar(airport)
                if metar_data:
                    weather_cache['metar'][airport.upper()] = metar_data
                    logger.info(f"Updated METAR for {airport}")
                    
                    # Fetch TAF if enabled (need it for weather entity forecast)
                    taf_data = None
                    if include_taf:
                        taf_data = fetch_taf(airport)
                        if taf_data:
                            weather_cache['taf'][airport.upper()] = taf_data
                            logger.info(f"Updated TAF for {airport}")
                    
                    # Create HA sensors and weather entity if this is the sensor airport
                    if create_sensors and airport.upper() == sensor_airport:
                        # Create individual sensors
                        if create_ha_sensors(metar_data, airport.upper()):
                            logger.info(f"Updated HA sensors for {airport}")
                        
                        # Create weather entity with forecast
                        if create_ha_weather_entity(metar_data, taf_data, airport.upper()):
                            logger.info(f"Updated HA weather entity for {airport}")
                
            except Exception as e:
                logger.error(f"Error updating weather for {airport}: {e}")
                continue
            
            # Respect rate limiting (max 100 requests/min)
            time.sleep(0.7)
        
        weather_cache['last_update'] = datetime.now().isoformat()
        save_cache()
        logger.info("Weather data update completed")
    except Exception as e:
        logger.error(f"Error in update_weather_data: {e}")
        raise


@app.route('/')
def index():
    """Main dashboard page"""
    options = read_options()
    airport_codes = options.get('airport_codes', [])
    
    weather_data = []
    for airport in airport_codes:
        airport_upper = airport.upper()
        metar = weather_cache['metar'].get(airport_upper)
        taf = weather_cache['taf'].get(airport_upper)
        
        weather_data.append({
            'airport': airport_upper,
            'metar': metar,
            'taf': taf
        })
    
    return render_template('index.html', 
                         weather_data=weather_data,
                         last_update=weather_cache.get('last_update'))


@app.route('/api/update', methods=['GET', 'POST', 'OPTIONS'])
def api_update():
    """Trigger weather data update"""
    # Handle OPTIONS preflight request for CORS
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Content-Type'] = 'application/json'
        return response
    
    logger.info(f"API update endpoint called via {request.method}")
    
    try:
        # Run update in background thread so request returns immediately
        def background_update():
            try:
                logger.info("Starting background weather update")
                update_weather_data()
                logger.info("Background weather update completed")
            except Exception as e:
                logger.error(f"Background update failed: {e}", exc_info=True)
        
        logger.info("Creating background thread")
        thread = threading.Thread(target=background_update, daemon=True)
        thread.start()
        logger.info("Background thread started")
        
        response = jsonify({'status': 'success', 'message': 'Weather data update started'})
        response.headers['Content-Type'] = 'application/json'
        logger.info("Returning success response")
        return response
    except Exception as e:
        logger.error(f"Error starting weather data update: {e}", exc_info=True)
        response = jsonify({'status': 'error', 'message': f'Failed to start update: {str(e)}'})
        response.headers['Content-Type'] = 'application/json'
        return response, 500


@app.route('/api/weather')
def api_weather():
    """Get all weather data as JSON"""
    return jsonify(weather_cache)


@app.route('/api/weather/<airport_code>')
def api_weather_airport(airport_code):
    """Get weather data for specific airport"""
    airport_upper = airport_code.upper()
    
    return jsonify({
        'airport': airport_upper,
        'metar': weather_cache['metar'].get(airport_upper),
        'taf': weather_cache['taf'].get(airport_upper)
    })


@app.route('/api/metar/<airport_code>')
def api_metar(airport_code):
    """Get METAR data for specific airport"""
    metar = fetch_metar(airport_code)
    if metar:
        return jsonify(metar)
    return jsonify({'error': 'No data available'}), 404


@app.route('/api/taf/<airport_code>')
def api_taf(airport_code):
    """Get TAF data for specific airport"""
    taf = fetch_taf(airport_code)
    if taf:
        return jsonify(taf)
    return jsonify({'error': 'No data available'}), 404


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    try:
        # Load cache on startup
        logger.info("Loading cache...")
        load_cache()
        logger.info("Cache loaded, Flask app ready")
        
        # Log all registered routes for debugging
        logger.info("Registered routes:")
        for rule in app.url_map.iter_rules():
            logger.info(f"  {rule.endpoint}: {rule.methods} {rule.rule}")
        
        # Run Flask app
        logger.info("Starting Flask app...")
        app.run(host='0.0.0.0', port=8099, debug=(LOG_LEVEL == 'DEBUG'))
    except Exception as e:
        logger.error(f"Fatal error starting app: {e}", exc_info=True)
        raise
