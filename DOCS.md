# Aviation Weather API Add-on Documentation

## Overview

The Aviation Weather API add-on integrates real-time aviation weather data from the NOAA Aviation Weather Center into your Home Assistant instance. It fetches METAR (current conditions) and TAF (forecasts) for configured airports and presents them in an easy-to-read dashboard.

## Configuration

### Airport Codes

Add the ICAO codes for the airports you want to monitor. You can find ICAO codes at [aviationweather.gov](https://aviationweather.gov/).

**Examples:**
- KJFK - John F. Kennedy International Airport (New York)
- KLAX - Los Angeles International Airport
- EGLL - London Heathrow Airport
- YSSY - Sydney Kingsford Smith Airport

### Update Interval

Controls how often the add-on fetches new weather data. Set between 5 and 120 minutes.

**Recommendations:**
- 15-30 minutes for general monitoring
- 5-10 minutes for flight planning
- 60+ minutes to minimize API usage

### Include TAF

When enabled, the add-on also fetches Terminal Aerodrome Forecasts, which provide weather predictions for the next 24-30 hours.

### Create Sensors

When enabled (default: `true`), the add-on automatically creates Home Assistant entities for the selected airport:

- **Weather Entity** (`weather.aviation_weather_XXXX`): Compatible with the standard Home Assistant weather card, includes current conditions and forecast
- **Individual Sensors**: Temperature, dewpoint, wind speed, wind direction, pressure, visibility, flight category, and raw METAR

### Sensor Airport

Determines which airport's data is used for creating Home Assistant entities:
- **auto** (default): Automatically selects the nearest airport to your Home Assistant location
- **ICAO Code**: Manually specify which airport to use (e.g., "KJFK")

**Note**: Only one airport's data will be exposed as Home Assistant entities, even if you're monitoring multiple airports. All airports remain visible in the web interface.

## Understanding the Data

### METAR Components

- **Temperature/Dewpoint**: In degrees Celsius
- **Wind**: Direction (degrees) and speed (knots)
- **Visibility**: In statute miles
- **Altimeter**: Barometric pressure in inches of mercury
- **Flight Category**:
  - **VFR** (Visual Flight Rules): Good weather
  - **MVFR** (Marginal VFR): Moderate weather
  - **IFR** (Instrument Flight Rules): Poor weather
  - **LIFR** (Low IFR): Very poor weather

### TAF Format

TAF provides forecast information including:
- Valid time period
- Expected wind conditions
- Visibility and cloud coverage
- Temporary and probable changes

## Home Assistant Integration

### Using the Weather Entity

The add-on automatically creates a weather entity that works with Home Assistant's standard weather card. Simply add a weather card to your dashboard:

```yaml
type: weather-forecast
entity: weather.aviation_weather_kjfk
```

The weather entity includes:
- Current temperature, humidity, pressure
- Wind speed and direction
- Visibility and cloud coverage
- Flight category (VFR, MVFR, IFR, LIFR)
- TAF forecast periods (if enabled)

### Using Individual Sensors

Individual sensors are also created for detailed monitoring:

```yaml
# Display temperature
sensor:
  - platform: template
    sensors:
      airport_temp_f:
        friendly_name: "Airport Temperature (F)"
        value_template: "{{ state_attr('sensor.aviation_weather_kjfk_temperature', 'temp_f') }}"
        unit_of_measurement: "°F"
```

### REST API Examples

#### Get All Weather Data

```bash
curl http://homeassistant.local:8099/api/weather
```

#### Get Specific Airport

```bash
curl http://homeassistant.local:8099/api/weather/KJFK
```

#### Trigger Update

```bash
curl -X POST http://homeassistant.local:8099/api/update
```

### Legacy REST Sensor Examples (Alternative Method)

If you prefer not to use the built-in sensors, you can still access data via REST:

### Temperature Sensor

```yaml
sensor:
  - platform: rest
    name: "Airport Temperature"
    resource: http://localhost:8099/api/metar/KJFK
    value_template: "{{ value_json.temp }}"
    unit_of_measurement: "°C"
```

### Flight Category Sensor

```yaml
sensor:
  - platform: rest
    name: "Flight Category"
    resource: http://localhost:8099/api/metar/KJFK
    value_template: "{{ value_json.flightCategory }}"
```

### Automation Example

```yaml
automation:
  - alias: "Notify Poor Weather Conditions"
    trigger:
      - platform: time_pattern
        minutes: "/30"
    condition:
      - condition: template
        value_template: >
          {{ states('sensor.flight_category') in ['IFR', 'LIFR'] }}
    action:
      - service: notify.mobile_app
        data:
          message: "Poor weather conditions at KJFK"
```

## Troubleshooting

### No Data Showing

1. Check that airport codes are valid ICAO codes
2. Verify the add-on is running (check logs)
3. Ensure internet connectivity
4. Check if the API is accessible at aviationweather.gov

### Rate Limiting Issues

If you see rate limit errors:
1. Increase the update interval
2. Reduce the number of airports
3. Wait 1 minute before retrying

### View Logs

Check the add-on logs for detailed error messages:
1. Go to Settings → Add-ons
2. Click on "Aviation Weather API"
3. Click the "Log" tab

## Advanced Usage

### Custom Port Configuration

The add-on uses port 8099 by default. If you need to change it, modify the port mapping in the add-on configuration.

### Data Persistence

Weather data is cached in `/data/weather_cache.json` to survive add-on restarts and minimize API calls.

## Privacy & Data

- The add-on only connects to aviationweather.gov (NOAA)
- No personal data is collected or transmitted
- All weather data is publicly available information
- Data is only stored locally in your Home Assistant instance

## Additional Resources

- [Aviation Weather Center](https://aviationweather.gov/)
- [METAR Decoder](https://www.aviationweather.gov/metar/decoder)
- [TAF Decoder](https://www.aviationweather.gov/taf/decoder)
- [API Documentation](https://aviationweather.gov/data/api/)
