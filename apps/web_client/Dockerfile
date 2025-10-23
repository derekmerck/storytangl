# build stage
FROM node:lts-alpine as app_builder

ARG VITE_DEBUG=true
ARG VITE_DEFAULT_API_URL=http://127.0.0.1:8000/api/v2
ARG VITE_DEFAULT_WORLD=""
ARG VITE_CLIENT_APP_PATH=/
# Going to be served by nginx at /
ARG VITE_CLIENT_APP_VERSION=3.0

CMD echo $VITE_API_ENDPOINT

WORKDIR /app
COPY ./package.json ./
COPY ./yarn.lock ./
# required for lib-gyp _only_ on arm64, crashes on x86-64
RUN if [ "$(uname -m)" = "aarch64" ]; then apk add --no-cache --virtual .gyp python3 make g++; fi
RUN yarn install
COPY . .
RUN yarn build

# production stage
FROM nginx:stable-alpine as runtime
LABEL maintainer="tangldev"

COPY --from=app_builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

HEALTHCHECK --interval=5m --timeout=3s \
  CMD curl -f http://localhost/ || exit 1
