# Changelog

All notable changes to this project will be documented in this file.

## [2.5.0] - 2026-02-05

### Fixed
- Weather entities now created via Home Assistant Supervisor API instead of MQTT
- Home Assistant does not support weather entities via MQTT discovery
- MQTT continues to be used for sensors (Temperature, Dewpoint, Wind, Pressure, Visibility, Flight Category)
- Weather entities will now properly appear in Weather Forecast Card entity picker

### Changed
- Removed MQTT weather entity discovery configuration
- Removed MQTT weather state publishing (not needed)
- Weather entities always created via API regardless of MQTT status

## [2.4.6] - 2026-02-05

### Changed
- Simplified weather entity MQTT discovery config to use standard topic naming
- Changed from `temperature_state_topic` to `temperature_topic` format
- Removed unit specifications to let Home Assistant handle conversions

## [2.4.5] - 2026-02-05

### Fixed
- Removed object_id from weather entity config (potential conflict)
- Added QoS 1 to weather entity discovery for reliable delivery
- Added error logging for failed MQTT publishes
- Updated device software version tracking

## [2.4.4] - 2026-02-05

### Fixed
- Corrected weather entity unit fields to match actual data format (°C, hPa, km/h)
- Weather entities now properly match published state values

## [2.4.3] - 2026-02-05

### Fixed
- Added required `temperature_unit`, `pressure_unit`, and `wind_speed_unit` fields to weather entity MQTT discovery config
- Weather entities now properly register with Home Assistant

## [2.4.2] - 2026-02-05

### Fixed
- CSS syntax error in dark mode styles (invalid media query grouping)
- Separated @media query from html.dark-mode class selector for proper CSS validation

## [2.4.1] - 2026-02-05

### Fixed
- MQTT weather entity discovery now includes required state topics
- Weather entities now properly appear in Home Assistant entity picker
- Added individual state topics for temperature, humidity, pressure, wind speed, and wind bearing
- Weather entities now fully compatible with Home Assistant's weather card selector

## [2.4.0] - 2026-02-05

### Added
- **Full weather card support for all configured airports**
- TAF forecast data now included in weather entity attributes
- Each airport's weather entity displays up to 12 forecast periods
- Forecast includes: datetime, condition, temperature, wind speed/bearing, pressure

### Changed
- MQTT weather entities now include forecast attribute (previously only API fallback had this)
- Weather cards can now display TAF forecasts for all airports

## [2.3.1] - 2026-02-05

### Fixed
- Pressure conversion now uses normalized altimInHg and altimHpa fields
- Pressure values correctly displayed in inHg instead of raw API values
- Weather entity pressure attribute correctly uses hPa from normalized data

## [2.3.0] - 2026-02-05

### Changed
- **Pressure sensor now displays in inHg** (inches of mercury) instead of hPa
- **Visibility sensor now displays in SM** (statute miles) instead of km
- **Sensors created for ALL configured airports** instead of just one
- Each airport gets its own device with all 8 entities (weather + 7 sensors)
- Removed sensor_airport configuration option (no longer needed)

### Technical
- MQTT Discovery configs updated with correct units
- API fallback method updated with correct units
- Removed auto-selection logic for single sensor airport

## [2.2.3] - 2026-02-05

### Added
- Custom flight category calculation based on FAA definitions as fallback
- VFR: Visibility > 5 SM AND Ceiling > 3000 ft
- MVFR: Visibility 3-5 SM OR Ceiling 1000-3000 ft  
- IFR: Visibility 1-3 SM OR Ceiling 500-1000 ft
- LIFR: Visibility < 1 SM OR Ceiling < 500 ft
- Ceiling extraction from cloud layers (lowest BKN/OVC layer)

### Changed
- Flight category uses API value if present, calculates locally as fallback
- More accurate VFR determination when API doesn't provide category

### Documentation
- Added MQTT authentication requirements to README
- Documented Mosquitto broker setup with username/password

## [2.2.2] - 2026-02-05

### Added
- Automatic weather data refresh on startup
- Initial weather data fetched and published immediately when add-on starts

## [2.2.1] - 2026-02-05

### Fixed
- Fixed initialization code to run under gunicorn WSGI server
- Moved cache loading and MQTT initialization to module level
- Ensures MQTT discovery works when add-on starts

## [2.2.0] - 2026-02-05

### Added
- **MQTT Discovery support** - Entities now properly linked to an "Aviation Weather" device
- Device shows up in Settings → Devices & Services → Devices tab
- All sensors and weather entity grouped under single device
- MQTT configuration options (host, port, username, password)
- Automatic fallback to API method if MQTT unavailable

### Changed
- Entities created via MQTT discovery by default (requires MQTT broker)
- Device name format: "Aviation Weather {AIRPORT}"
- Added paho-mqtt dependency

## [2.1.3] - 2026-02-05

### Fixed
- CSS file now loads properly in ingress by using relative path instead of url_for()
- Fixed 404 error for static files in Home Assistant ingress panel

## [2.1.2] - 2026-02-05

### Fixed
- Improved dark mode detection for Home Assistant ingress iframe
- Added JavaScript-based dark mode switcher that works in embedded contexts
- CSS now supports both media query and class-based dark mode activation

## [2.1.1] - 2026-02-05

### Fixed
- Visibility parsing now handles string values like "10+" from the API
- Added parse_visibility() helper function to properly convert visibility values to float
- Fixed TypeError when visibility comes back as a string instead of numeric value

## [2.1.0] - 2026-02-04

### Added
- Dark mode support for web interface - automatically detects browser/system preference
- Native Home Assistant weather entity compatible with the standard weather card
- Individual sensors for all METAR attributes (temperature, wind, pressure, visibility, etc.)
- Humidity calculation from temperature and dewpoint using Magnus formula
- Auto-selection of nearest airport for sensor creation based on HA location

### Changed
- **Breaking**: `create_sensors` now defaults to `true` - weather entities created automatically
- Weather entity now includes all standard attributes for HA weather card compatibility
- Improved forecast integration with up to 12 TAF periods
- Enhanced cloud coverage calculation from multiple layers
- Rounded all numeric values for cleaner display

### Fixed
- Weather entity now properly displays in Home Assistant weather card
- Removed deprecated `*_unit` attributes (HA uses implicit units)
- Fixed pressure conversion from inHg to hPa for weather entities

## [2.0.1] - 2026-02-03

### Fixed
- Dashboard panel visibility when accessing via HTTPS ingress
- Removed X-Frame-Options header to allow proper iframe embedding in Home Assistant
- Updated panel icon to mdi:weather-cloudy for better compatibility

## [1.3.2] - 2025-10-28

### Fixed
- TAF: skip visibility when empty/null (e.g., TEMPO periods with no vis value)
- TAF: guard cloud base formatting when base is null (e.g., SKC) so all periods render

## [1.3.1] - 2025-10-28

### Fixed
- TAF forecast periods now decode correctly (API uses 'fcsts' field not 'forecast')
- TAF time fields corrected (timeFrom/timeTo instead of validTimeFrom/validTimeTo)
- TAF change type field corrected (fcstChange instead of fcstType)
- Duplicate cloud layer display eliminated (prioritize detailed cloud array over general cover field)

## [1.3.0] - 2025-10-28

### Added
- Enhanced TAF decoding with human-readable summaries for each forecast period
- Wind cardinal direction display (e.g., "220° (SW)")
- Comprehensive AI coding assistant documentation (`.github/copilot-instructions.md`)

### Fixed
- Ingress 404 error: JavaScript fetch now uses relative paths for proper proxy routing
- Temperature and dewpoint now display in Fahrenheit only (removed Celsius)
- Observation time correctly labeled and formatted as local time
- Unix timestamp handling for observation times (API returns integers)
- Altimeter pressure conversion: properly converts hPa to inHg when needed

### Changed
- Removed cloud coverage detail percentages (e.g., "3-4/8 (37-50%)") for cleaner display
- TAF forecast periods now show complete decoded summaries with time, wind, visibility, weather, and clouds

## [1.0.0] - 2025-10-28

### Added
- Initial release
- METAR data fetching from aviationweather.gov API
- TAF data fetching (optional)
- Web-based dashboard with Ingress support
- Configurable update intervals
- Support for multiple airports
- RESTful API endpoints
- Data caching system
- Flight category display (VFR, MVFR, IFR, LIFR)
- Responsive web interface
- Manual refresh capability
- Health check endpoint
- Comprehensive logging
- Rate limiting compliance

### Features
- Beautiful gradient UI design
- Real-time weather updates
- Decoded METAR values
- Raw METAR/TAF text display
- Configurable log levels
- Auto-save/load cache on restart
