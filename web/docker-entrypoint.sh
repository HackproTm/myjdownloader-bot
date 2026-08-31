#!/bin/sh
# Bakes the API_BASE_URL env var into index.html at container startup.
set -e
envsubst '${API_BASE_URL}' < /usr/share/nginx/html/index.html.template > /usr/share/nginx/html/index.html
