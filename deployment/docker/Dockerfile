# Stage 1: Setup python build env
FROM python:slim as python_builder
# StoryTangl game engine builder image

# Some build systems don't include the lfs files
RUN apt update && apt install -y git-lfs

# Install Poetry
RUN pip install --upgrade pip

# Install package with poetry
RUN pip install poetry --with docs

# Copy the repo contents into the container at /build
COPY . /build

# Set the working directory to /build
WORKDIR /build
RUN git lfs pull

# Stage 2: Build the wheel to use in the runtime image
FROM python_builder as pkg_builder

# RUN poetry add toml
RUN poetry build -f wheel -n

# Stage 3: Build the docs to use in the runtime image
FROM python_builder as doc_builder

RUN poetry run python -m sphinx.cmd.build -b html docs docs/html

## Stage 4: Build the web app
#FROM node:lts-alpine as app_builder
##
#CMD echo $VITE_API_ENDPOINT
#
#WORKDIR /app
#COPY ./client/package.json ./
#COPY ./client/yarn.lock ./
## required for lib-gyp _only_ on arm64, crashes on x86-64
#RUN if [ "$(uname -m)" = "aarch64" ]; then apk add --no-cache --virtual .gyp python3 make g++; fi
#RUN yarn install
#COPY ./client .
#RUN yarn build

# Stage 5: Create the runtime image, image is much smaller than builder
FROM python:slim as runtime
LABEL maintainer="story-tangl"
LABEL version="3.2"

# StoryTangl game engine runtime image
# $ docker run -p 8000:8000 story-tangl:3.2 server      # default entry point
# $ docker run -it story-tangl:3.2 cli              # interactive CLI entry point

# Set the working directory to /app
WORKDIR /app

# Collect the wheel built in the first stage
COPY --from=pkg_builder /build/dist/*.whl /app

# Collect the worlds from the first stage (with lfs files)
#COPY --from=pkg_builder /build/worlds /app/worlds
## todo: worlds are now included in the package as modules, consider the auto-finder behavior

# Collect the docs built in the first stage
ENV TANGL_SERVICE__PATHS__DOCS='@path /app/docs/'
COPY --from=doc_builder /build/docs/html /app/docs

## Collect the client build from the fourth stage
#ENV TANGL_SERVICE__PATHS__CLIENT_DIST='@path /app/client/'
#COPY --from=app_builder /app/dist /app/client

# Install the application
RUN pip install --upgrade pip && pip install *.whl && rm *.whl

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run rest server script when the container launches
CMD ["serve"]

HEALTHCHECK --interval=5m --timeout=1s \
  CMD curl -f http://localhost:8000/api/v2/system/info || exit 1

# todo: write a docker-compose with nginx and redis for storage