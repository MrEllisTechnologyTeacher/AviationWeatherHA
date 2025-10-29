# Aviation Weather API Add-on for Home Assistant

This add-on provides real-time aviation weather data (METAR and TAF) from the [aviationweather.gov API](https://aviationweather.gov/data/api/).

## Features

- 📊 Real-time METAR (Meteorological Aerodrome Report) data
- 🔮 TAF (Terminal Aerodrome Forecast) data
- 🌐 Web-based dashboard with Ingress support
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
```

### Options

- **airport_codes** (required): List of ICAO airport codes (e.g., KJFK, EGLL, YSSY)
- **update_interval**: Minutes between updates (5-120, default: 30)
- **include_taf**: Include Terminal Aerodrome Forecast data (default: true)
- **log_level**: Logging level - debug, info, warning, or error (default: info)

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

You can use the RESTful sensor to integrate weather data into Home Assistant:

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
