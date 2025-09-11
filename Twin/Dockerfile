# =============================================
# Python & Node.js image for Django + Webpack
# =============================================
FROM python:3.11

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/code/"

# Set build arg
ARG BUILD_MODE=production

# Install system dependencies & Node.js
RUN apt-get update && \
    apt-get install -y curl gnupg build-essential && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /code

# Copy all code to container
COPY . /code/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Move to frontend source
WORKDIR /code/static/assets/src

# Initialize package.json so dependencies are tracked
RUN npm init -y
# Install dev build tooling
RUN npm install --save-dev \
    webpack@5.98.0 \
    webpack-cli@6.0.1 \
    babel-loader \
    @babel/core \
    @babel/preset-env \
    mini-css-extract-plugin \
    css-loader \
    sass \
    sass-loader \
    copy-webpack-plugin

# Install core frontend packages
# NOTE: @popperjs/core is a bootstrap5 dependency
RUN npm install \
    @popperjs/core \  
    bootstrap@5.3.3 \
    bootstrap-icons@1.11.3 \
    dayjs@1.11.13\
    chart.js@4.4.8 \
    apexcharts@4.5.0 \
    typed.js@2.1.0 \
    datatables.net-bs5@2.2.2 \
    select2@4.0.13 \
    sweetalert2@11.17.2 \
    flatpickr@4.6.13 \
    fireworks-js@2.10.8 \
    @fontsource/inter

# Build frontend assets
RUN npx webpack --mode ${BUILD_MODE}  --config webpack.config.js

# Prune dev dependencies for smaller image if in production mode
RUN if [ "$BUILD_MODE" = "production" ]; then npm prune --production; else echo "Skipping prune"; fi

# Clean up caches
RUN rm -rf /root/.npm /root/.cache

# Return to app root for Django/Gunicorn
WORKDIR /code
