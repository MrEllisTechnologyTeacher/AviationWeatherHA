# Aviation Weather API Add-on for Home Assistant

This add-on provides real-time aviation weather data (METAR and TAF) from the [aviationweather.gov API](https://aviationweather.gov/data/api/).

## Features

- 📊 Real-time METAR (Meteorological Aerodrome Report) data
- 🔮 TAF (Terminal Aerodrome Forecast) data
- 🌐 Web-based dashboard with Ingress support (now with dark mode!)
- 🏠 **Native Home Assistant Weather Entity** - Works with the standard weather card
- 📈 **Individual Sensors** - Temperature, humidity, wind, pressure, visibility, and more
- 🔄 Configurable update intervals
- 💾 Data caching to reduce API calls
- 📡 RESTful API endpoints for integration
- ✈️ Support for multiple airports

## Installation (HAOS)

There are two ways to install on Home Assistant OS. Using prebuilt images is easiest; you can also build locally on your HA host if GHCR access is blocked.

Repository URL: https://github.com/MrEllisTechnologyTeacher/AviationWeatherHA

### Option A — Prebuilt images (recommended)

1. Open Home Assistant and go to Settings → Add-ons → Add-on Store
2. Click the top-right menu (⋮) → Repositories
3. Paste the repository URL above and click Add, then Close
4. Back in the Add-on Store, you should see "Aviation Weather API" under this repository
5. Click the add-on → Install → Configure → Start

Notes:
- Images are published to GitHub Container Registry (GHCR) for `amd64` and `aarch64`. HAOS will pull the correct one automatically.
- If you hit a 403/denied error during install, the GHCR image may still be Private. See Troubleshooting below.

Optional quick links:
- Open Add-on Store: https://my.home-assistant.io/redirect/supervisor_store/

### Option B — Build locally on the HAOS device

If your HA host cannot pull from GHCR or you prefer local builds:

1. Add this repository as above OR copy this folder into your HA host at `/addons/aviation_weather`.
2. Edit `aviation_weather/config.yaml` in your copy and remove the `image:` line entirely.
3. Back in Add-on Store, open the add-on and click Install — the Supervisor will build locally using the correct HA base image.

Details:
- A `build.yaml` is included mapping architectures to official Home Assistant base images to ensure correct on-device builds.
- Local builds take several minutes but avoid external registry pulls entirely.

## Configuration

```yaml
airport_codes:
  - KJFK
  - KLAX
  - KORD
update_interval: 30
include_taf: true
log_level: info
create_sensors: true
```

### Options

- **airport_codes** (required): List of ICAO airport codes (e.g., KJFK, EGLL, YSSY)
- **update_interval**: Minutes between updates (5-120, default: 30)
- **include_taf**: Include Terminal Aerodrome Forecast data (default: true)
- **log_level**: Logging level - debug, info, warning, or error (default: info)
- **create_sensors**: Create Home Assistant entities for all configured airports (default: true)
- **mqtt_enabled**: Enable MQTT Discovery for device grouping (default: true)
- **mqtt_host**: MQTT broker hostname (default: core-mosquitto)
- **mqtt_port**: MQTT broker port (default: 1883)
- **mqtt_username**: MQTT username - **REQUIRED** if your broker uses authentication
- **mqtt_password**: MQTT password - **REQUIRED** if your broker uses authentication

**Note**: Each configured airport will get its own device with 8 entities (1 weather entity + 7 sensors).

### MQTT Configuration (Recommended)

This add-on uses MQTT Discovery to create sensor entities grouped under proper devices in Home Assistant. **Weather entities are created via the Home Assistant Supervisor API** (MQTT weather entities are not supported by Home Assistant). **MQTT authentication is required** if your Mosquitto broker has authentication enabled (which is the default for Home Assistant's Mosquitto add-on).

1. Create a user for the add-on in your Mosquitto broker:
   - Go to **Settings → Add-ons → Mosquitto broker → Configuration**
   - Add a login entry:
   ```yaml
   logins:
     - username: aviation_weather
       password: your_secure_password
   ```
   - Save and restart the Mosquitto broker

2. Configure the Aviation Weather add-on with the same credentials:
   ```yaml
   mqtt_enabled: true
   mqtt_host: core-mosquitto
   mqtt_port: 1883
   mqtt_username: aviation_weather
   mqtt_password: your_secure_password
   ```

3. Restart the Aviation Weather add-on

After configuration:
- **Sensor entities** (Temperature, Dewpoint, Wind Speed, Wind Direction, Pressure, Visibility, Flight Category) will be grouped under an "Aviation Weather {AIRPORT}" device via MQTT Discovery
- **Weather entities** (`weather.aviation_weather_{airport}`) will be created via the Supervisor API and appear in the Weather Forecast Card entity picker

**Note**: If MQTT is unavailable or misconfigured, the add-on will automatically fall back to the Supervisor API method for sensors (entities without device grouping).

## Usage

### Web Dashboard

Access the add-on dashboard through the Home Assistant sidebar. The dashboard displays:
- Current METAR data with decoded values
- TAF forecasts (if enabled)
- Flight category (VFR, MVFR, IFR, LIFR)
- Temperature, dewpoint, wind, visibility, and altimeter settings

### API Endpoints

The add-on provides several API endpoints:

- `GET /api/weather` - Get all cached weather data
- `GET /api/weather/<airport_code>` - Get data for specific airport
- `GET /api/metar/<airport_code>` - Get fresh METAR data
- `GET /api/taf/<airport_code>` - Get fresh TAF data
- `POST /api/update` - Trigger manual update
- `GET /health` - Health check

### Rate Limiting

The add-on respects the aviationweather.gov API rate limits:
- Maximum 100 requests per minute
- 0.7 second delay between consecutive requests
- Data is cached to minimize API calls

## Integration with Home Assistant

### Using the Weather Entity (Recommended)

The add-on automatically creates a weather entity for **each configured airport**, compatible with Home Assistant's standard weather card with forecast support. Simply add them to your dashboard:

```yaml
type: weather-forecast
entity: weather.aviation_weather_kpwa  # Replace with your airport code
```

**Multiple Airports:** If you configure multiple airports (e.g., KPWA, KOKC, KTIK), each gets its own weather entity:
- `weather.aviation_weather_kpwa`
- `weather.aviation_weather_kokc`
- `weather.aviation_weather_ktik`

Each weather entity provides:
- Current conditions (temperature, humidity, pressure, wind, visibility)
- **TAF forecast periods** (up to 12 periods) - displayed in weather card
- Flight category (VFR/MVFR/IFR/LIFR)
- Aviation-specific attributes (cloud layers, raw METAR, decoded weather)

### Using Individual Sensors

Individual sensors are created for each airport's weather parameters:
- `sensor.aviation_weather_kjfk_temperature` (°C)
- `sensor.aviation_weather_kjfk_dewpoint` (°C)
- `sensor.aviation_weather_kjfk_wind_speed` (knots)
- `sensor.aviation_weather_kjfk_wind_bearing` (°)
- `sensor.aviation_weather_kjfk_pressure` (inHg)
- `sensor.aviation_weather_kjfk_visibility` (SM)
- `sensor.aviation_weather_kjfk_flight_category` (VFR/MVFR/IFR/LIFR)
- `sensor.aviation_weather_kjfk_condition` (decoded weather)
- `sensor.aviation_weather_kjfk_raw_metar` (raw METAR text)

### Legacy REST API Integration

You can also use the RESTful sensor to integrate weather data into Home Assistant:

```yaml
sensor:
  - platform: rest
    name: "KJFK METAR"
    # Use your HA host IP or DNS here (not localhost from HA Core)
    resource: http://homeassistant.local:8099/api/metar/KJFK
    value_template: "{{ value_json.temp }}"
    unit_of_measurement: "°C"
    json_attributes:
      - rawOb
      - flightCategory
      - wspd
      - wdir
      - visib
```

## Support

For issues and feature requests, please visit the [GitHub repository](https://github.com/MrEllisTechnologyTeacher/AviationWeatherHA).

## Credits

- Weather data provided by [NOAA Aviation Weather Center](https://aviationweather.gov/)
- Built for [Home Assistant](https://www.home-assistant.io/)

## License

MIT License - See LICENSE file for details

## Known issues / Troubleshooting

### 403 when installing from GHCR

Error example:

Can't install ghcr.io/mrellistechnologyteacher/aviationweatherha-aarch64:1.0.0: 403 Client Error (denied)

Cause: GitHub Container Registry packages are private by default. Home Assistant can't pull private images.

Fix:
- Wait for the GitHub Actions build to complete for your architecture (amd64/aarch64) and then set the package visibility to Public in GitHub:
  - Repo → Packages (right sidebar) → Click the container (e.g., aviationweatherha-aarch64) → Package settings → Change visibility to Public.
- Re-try installing the add-on (Add-on Store → ⋮ → Check for updates, then install).

Note: The CI workflow attempts to set packages public automatically, but some accounts require changing it once in the GitHub UI.
