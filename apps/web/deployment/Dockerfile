# StoryTangl Web Client Dockerfile (v3.7)
# Multi-stage build: Node builder → Nginx runtime

# ============================================================================
# Stage 1: Build the Vue/Vite application
# ============================================================================
FROM node:20-alpine as app_builder

# Build-time configuration
# These are baked into the built JavaScript at compile time
ARG VITE_DEBUG=false
ARG VITE_VERBOSE=false
ARG VITE_MOCK_RESPONSES=false
ARG VITE_DEFAULT_API_URL=/api/v2
ARG VITE_DEFAULT_WORLD=tangl_world
ARG VITE_DEFAULT_USER_SECRET=change-me-in-production

# Debug output (visible during docker build)
RUN echo "Building web client with:" && \
    echo "  API URL: $VITE_DEFAULT_API_URL" && \
    echo "  Default World: $VITE_DEFAULT_WORLD" && \
    echo "  Debug: $VITE_DEBUG" && \
    echo "  Mock Responses: $VITE_MOCK_RESPONSES"

WORKDIR /app

# Copy package files first for better layer caching
# Only rebuilds if dependencies change
COPY package.json yarn.lock ./

# Install dependencies
# Includes workaround for native modules on ARM64 (Apple Silicon, etc.)
RUN if [ "$(uname -m)" = "aarch64" ]; then \
      echo "Detected ARM64 - installing build tools for native modules"; \
      apk add --no-cache --virtual .gyp python3 make g++; \
    fi && \
    yarn install --frozen-lockfile && \
    if [ "$(uname -m)" = "aarch64" ]; then \
      apk del .gyp; \
    fi

# Copy application source code
COPY . .

# Build the application
# Output goes to /app/dist
RUN yarn build

# Verify build output exists
RUN ls -lah /app/dist && \
    test -f /app/dist/index.html || (echo "Build failed - no index.html" && exit 1)

# ============================================================================
# Stage 2: Production runtime with nginx
# ============================================================================
FROM nginx:stable-alpine as runtime

# Metadata
LABEL maintainer="tangldev"
LABEL version="3.7.2"
LABEL description="StoryTangl Web Client - Interactive narrative interface"

# Copy built application from builder stage
COPY --from=app_builder /app/dist /usr/share/nginx/html

# Optional: Copy custom nginx configuration for SPA routing
# Uncomment if you need client-side routing support (Vue Router)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 for HTTP
EXPOSE 80

# Health check
# Ensures the container is actually serving content
HEALTHCHECK --interval=5m --timeout=3s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Start nginx in foreground mode
CMD ["nginx", "-g", "daemon off;"]
