# nginx/Dockerfile
FROM nginx:1.25-alpine

# Install envsubst for dynamic template rendering
RUN apk add --no-cache gettext

# Copy the template config file
COPY templates/default.conf /etc/nginx/templates/default.conf

# Render template and start Nginx
CMD ["/bin/sh", "-c", "envsubst '\\$HOST' < /etc/nginx/templates/default.conf > /etc/nginx/conf.d/default.conf && echo '==== Rendered default.conf ====' && cat /etc/nginx/conf.d/default.conf && echo '==== End ====' && exec nginx -g 'daemon off;'"]
