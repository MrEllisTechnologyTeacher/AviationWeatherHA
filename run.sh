#!/usr/bin/with-contenv bashio

bashio::log.info "Starting Aviation Weather API add-on..."

# Read configuration options
AIRPORT_CODES=$(bashio::config 'airport_codes')
UPDATE_INTERVAL=$(bashio::config 'update_interval')
INCLUDE_TAF=$(bashio::config 'include_taf')
LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "Airport codes: ${AIRPORT_CODES}"
bashio::log.info "Update interval: ${UPDATE_INTERVAL} minutes"
bashio::log.info "Include TAF: ${INCLUDE_TAF}"
bashio::log.info "Log level: ${LOG_LEVEL}"

# Export configuration as environment variables
export AIRPORT_CODES
export UPDATE_INTERVAL
export INCLUDE_TAF
export LOG_LEVEL

# Start the Flask application
cd /app
exec gunicorn --bind 0.0.0.0:8099 --workers 1 --timeout 600 --graceful-timeout 30 --keep-alive 5 --log-level debug app:app
