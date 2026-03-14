# frontend/Dockerfile

# ── Stage 1: Build ────────────────────────────────────────────────
# Node runs Vite and produces static files in /app/dist.
FROM node:20-alpine AS build
WORKDIR /app

# Install deps first (cached layer), then copy source.
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Stage 2: Serve ────────────────────────────────────────────────
# Final image contains only Nginx + the built static files.
# No Node.js in production — image is ~25MB instead of ~1GB.
FROM nginx:alpine AS serve
# Create non-root user and set ownership of the html directory
RUN adduser -D -H -u 1001 appuser \
    && chown -R appuser:appuser /usr/share/nginx/html \
    && chown -R appuser:appuser /var/cache/nginx \
    && chown -R appuser:appuser /var/log/nginx

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Nginx needs to write its PID file — point it somewhere the user owns
RUN touch /var/run/nginx.pid && chown appuser:appuser /var/run/nginx.pid
USER appuser
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]