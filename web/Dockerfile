FROM nginx:1.27-alpine

COPY index.html /usr/share/nginx/html/index.html.template
COPY style.css /usr/share/nginx/html/style.css
COPY app.js /usr/share/nginx/html/app.js

# nginx's own entrypoint runs every executable script in /docker-entrypoint.d/
# before starting, in filename order.
COPY docker-entrypoint.sh /docker-entrypoint.d/40-substitute-api-base-url.sh
RUN chmod +x /docker-entrypoint.d/40-substitute-api-base-url.sh

EXPOSE 80
