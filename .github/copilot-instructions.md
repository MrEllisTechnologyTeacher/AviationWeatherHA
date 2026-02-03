# Aviation Weather Add-on - AI Coding Assistant Instructions

## Project Overview

This is a **Home Assistant Add-on** (not a standalone app) that provides aviation weather data from aviationweather.gov. The add-on runs as a Flask web service inside Home Assistant OS (HAOS) using the Supervisor framework.

### Critical Architecture Points

- **Single-file Flask app**: `app.py` (601 lines) handles API fetching, data decoding, caching, web UI, and REST endpoints
- **Add-on lifecycle**: Managed by HAOS Supervisor via `config.yaml`, not run directly
- **Configuration flow**: User sets options in HA UI → `/data/options.json` → read by `read_options()` in `app.py`
- **Data persistence**: Weather cache saved to `/data/weather_cache.json` to survive restarts
- **Ingress-first**: Web UI accessed through HA's Ingress proxy (not direct port access)

## Key Integration Points

### Home Assistant Supervisor Integration

```yaml
# config.yaml defines the add-on contract with HAOS
ingress: true                    # UI accessed via HA Ingress (path rewriting)
homeassistant_api: true          # Can call HA Core API at http://supervisor/core/api
ports: 8099/tcp: 8099           # Container port (Ingress handles routing)
```

**Critical**: Flask app uses `ProxyFix` middleware (lines 21-22) to handle `X-Forwarded-*` headers from Ingress. Never remove this or Ingress routing breaks.

### Ingress Path Handling

**IMPORTANT**: When adding JavaScript fetch calls or HTML forms:
- ✅ **Use relative paths**: `fetch('api/update')` - works with Ingress path rewriting
- ✅ **Use Flask url_for()**: `{{ url_for('api_update') }}` in templates - generates correct Ingress URLs
- ❌ **Never use absolute paths**: `fetch('/api/update')` - bypasses Ingress, causes 404 errors

Example from `templates/index.html` (line 230):
```javascript
// CORRECT - relative path works with Ingress
const response = await fetch('api/update', { method: 'POST' });

// WRONG - absolute path bypasses Ingress prefix
const response = await fetch('/api/update', { method: 'POST' });  // 404!
```

### External API Rate Limiting

`fetch_metar()` and `fetch_taf()` enforce **0.7s delay** between requests (line 464) to respect aviationweather.gov's 100 req/min limit. The `update_weather_data()` loop iterates airports sequentially with `time.sleep(0.7)` - do not parallelize or remove delays.

## Development Workflows

### Local Testing (Outside HAOS)

```bash
# Create test options file
mkdir -p /tmp/data
echo '{"airport_codes": ["KJFK"], "update_interval": 30, "include_taf": true, "log_level": "info"}' > /tmp/data/options.json

# Run Flask directly (bypasses gunicorn/bashio from run.sh)
export LOG_LEVEL=DEBUG
python3 app.py  # Runs on http://localhost:8099
```

### Building for HAOS

**Option A - Local build** (recommended for testing):
```bash
# Remove 'image:' line from config.yaml to force local build
# HAOS Supervisor uses build.yaml to select correct base image
```

**Option B - GHCR image** (for release):
```bash
# Images auto-built via GitHub Actions (not included in repo)
# config.yaml references: ghcr.io/mrellistechnologyteacher/aviationweatherha-{arch}
```

### Debugging in HAOS

```bash
# Access add-on logs via HA UI or CLI
ha addons logs aviation_weather

# Check running container
docker ps | grep aviation_weather
docker exec -it <container> /bin/bash
cat /data/options.json           # Check config
cat /data/weather_cache.json     # Check cache
```

## Project-Specific Patterns

### Data Flow: API → Decode → Cache → Serve

1. **Fetch**: `fetch_metar()` / `fetch_taf()` get raw JSON from aviationweather.gov
2. **Decode**: Add human-readable fields (e.g., `wxDecoded`, `cloudLayers`, `obsTimeLocal`)
3. **Cache**: Store in `weather_cache` dict → persist to `/data/weather_cache.json`
4. **Serve**: Flask routes return cached data (UI via template, API as JSON)

**Example** (lines 370-389):
```python
metar = data[0]
metar['wxDecoded'] = decode_weather_codes(metar['wxString'])  # "RA" → "Rain"
metar['cloudLayers'] = decode_cloud_layers(metar)             # Parse cloud cover
metar['obsTimeLocal'] = convert_to_local_time(metar['obsTime'])  # UTC → local
```

### Decoding Functions (Lines 118-340)

Core domain logic for aviation weather:
- `decode_weather_codes()`: Converts METAR weather phenomena codes (e.g., "+TSRA" → "Heavy Thunderstorm Rain")
- `decode_cloud_layers()`: Parses cloud coverage/altitude (e.g., "BKN015" → "Broken at 1,500 ft AGL")
- `decode_taf_forecast()`: Structures TAF periods with human-readable times/conditions
- `convert_to_local_time()`: Returns UTC, local, and short formats for display

**Never modify** these without cross-referencing official METAR/TAF specs - they implement FAA standards.

### Background Updates

`/api/update` endpoint (lines 496-524) starts weather fetch in a **daemon thread** to return immediately. This prevents Ingress timeouts during multi-airport updates. Pattern:

```python
thread = threading.Thread(target=background_update, daemon=True)
thread.start()
return jsonify({'status': 'success'})  # Returns before update completes
```

## Configuration Schema

`config.yaml` schema validates user input:
```yaml
schema:
  airport_codes: [str]              # List of ICAO codes
  update_interval: "int(5,120)"     # Minutes between auto-updates
  include_taf: bool                 # Fetch forecasts
  log_level: "list(debug|info|warning|error)"
```

**Important**: Schema changes require add-on restart. Users configure via HA UI, not by editing YAML directly.

## Common Tasks

### Adding a New API Endpoint

1. Define route in `app.py` (after line 525)
2. Return `jsonify()` for consistency
3. Add CORS headers via `@app.after_request` (already configured globally)
4. Test with `curl http://localhost:8099/api/your-endpoint`

### Modifying UI Display

- Edit `templates/index.html` (Jinja2 template)
- CSS in `static/style.css`
- Pass data via `render_template()` context (line 492)
- **JavaScript API calls**: Use relative paths (`api/update`) not absolute (`/api/update`) for Ingress compatibility
- **Flask templates**: Use `{{ url_for('route_name') }}` for URL generation

### Changing Update Intervals

The add-on **does not auto-poll** on intervals. Updates happen:
1. On add-on start (cache load)
2. Via manual "Refresh" button (calls `/api/update`)
3. Via Home Assistant automation calling `/api/update`

To add auto-polling, implement a background scheduler (e.g., `threading.Timer` or `APScheduler`).

## Testing Checklist

- [ ] Test with 0, 1, and 5+ airport codes
- [ ] Verify behavior when API returns 204 (no data)
- [ ] Check cache persistence across restarts (`/data/weather_cache.json`)
- [ ] Test Ingress routing (access via HA UI, not direct port)
- [ ] Validate rate limiting (watch for 429 errors with >10 airports)
- [ ] Test with `include_taf: false` to ensure graceful degradation

## External Dependencies

- **aviationweather.gov API**: Public, no auth required, JSON format
- **Home Assistant Supervisor**: Provides `/data` volume, Ingress proxy, config injection
- **Base image**: `ghcr.io/home-assistant/amd64-base:latest` (Alpine Linux with bashio)

## Avoid These Mistakes

- ❌ Don't use `app.run(debug=True)` in production (already handled by `run.sh` + gunicorn)
- ❌ Don't hardcode airport codes in `app.py` (read from `options.json`)
- ❌ Don't remove `time.sleep(0.7)` from update loop (API rate limit enforcement)
- ❌ Don't add async/await without refactoring Flask app to Quart
- ❌ Don't access `/data` before add-on installed (won't exist during local testing)
- ❌ **Don't use absolute paths in JavaScript** (`/api/update`) - use relative paths (`api/update`) for Ingress compatibility
