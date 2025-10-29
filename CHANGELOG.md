# Changelog

All notable changes to this project will be documented in this file.

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
