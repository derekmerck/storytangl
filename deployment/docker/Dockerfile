# Stage 1: Python builder (code, deps, git-lfs)
FROM python:3.13-slim AS python_builder
# StoryTangl game engine builder image

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends git-lfs git \
 && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --upgrade pip \
 && pip install poetry \
 && poetry config virtualenvs.create false

# Copy the repo contents into the container at /build
WORKDIR /build
COPY . .

# Ensure LFS content is present (worlds, etc.)
RUN git lfs pull

# Install project deps including dev/docs extras (pyproject uses a 'dev' group for docs/testing)
RUN poetry install --with dev --no-root

# Stage 2: Build the wheel to use in the runtime image
FROM python_builder AS pkg_builder

RUN poetry build -f wheel -n

# Stage 3: Build the docs to use in the runtime image
FROM python_builder AS doc_builder

RUN poetry run python -m sphinx.cmd.build -b html docs docs/html

# Stage 4: Build the web app
FROM node:lts-alpine AS app_builder

WORKDIR /app
COPY ./web/package.json ./web/yarn.lock ./

# required for node-gyp _only_ on arm64, crashes on x86-64
RUN if [ "$(uname -m)" = "aarch64" ]; then \
      apk add --no-cache --virtual .gyp python3 make g++; \
    fi

RUN yarn install --frozen-lockfile

COPY ./web .
RUN yarn build

# Stage 5: Runtime image
FROM python:3.13-slim AS runtime
LABEL maintainer="tangldev"
LABEL version="3.7"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# StoryTangl game engine runtime image
# $ docker run -p 8000:8000 story-tangl:3.7 tangl-serve    # REST server (default)
# $ docker run -it story-tangl:3.7 tangl-cli               # interactive CLI entry point

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Collect the wheel built in the pkg_builder stage
COPY --from=pkg_builder /build/dist/*.whl /app/

# Collect the worlds (with LFS files)
COPY --from=pkg_builder /build/worlds /app/worlds

# Collect the docs built in the doc_builder stage
ENV TANGL_SERVICE__PATHS__DOCS='@path /app/docs/'
COPY --from=doc_builder /build/docs/html /app/docs

# Collect the client build from the app_builder stage
ENV TANGL_SERVICE__PATHS__CLIENT_DIST='@path /app/client/'
COPY --from=app_builder /app/dist /app/client

# Install the application (cli + server extras)
RUN pip install --upgrade pip \
 && pip install /app/*.whl[cli,server] \
 && rm /app/*.whl

EXPOSE 8000

# Default entry point: REST server
CMD ["tangl-serve"]

HEALTHCHECK --interval=5m --timeout=3s \
  CMD curl -fsS http://localhost:8000/api/v2/system/info || exit 1