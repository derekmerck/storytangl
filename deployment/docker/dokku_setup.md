Dokku Setup
====================

Run your own public StoryTangl node on with Dokku.

[Dokku][] is an easy-to-use FOSS PaaS stack.  It has various advantages and drawbacks compared to using docker-compose files.
[DigitalOcean][] has an inexpensive 1-click Dokku node setup that works fine with the $5/month basic droplet.

[Dokku]: https://dokku.com
[DigitalOcean]: https://marketplace.digitalocean.com/apps/dokku

Login to your node and update dokku

```
$ apt update && apt upgrade
# Install or upgrade Dokku using official bootstrap
wget -NP . https://dokku.com/install/v0.37.0/bootstrap.sh
sudo DOKKU_TAG=v0.37.0 bash bootstrap.sh
```
- or follow the online install guide for the latest version.

If not using the DigitalOcean Dokku image, allow HTTP/HTTPS:
```
$ ufw allow 80
$ ufw allow 443  # if using https
```

Add apps for the `tangl-web` client app container and `tangl` backend container.
```
$ dokku apps:create tangl-web
$ dokku apps:create tangl
```

Set global and per-app domains
# Global domain (example)
```
$ dokku domains:set-global storytangl.example.com
```

# Per-app domains
```
$ dokku domains:set tangl api.storytangl.example.com
$ dokku domains:set tangl-web app.storytangl.example.com
```

Add a redis service and link it to `tangl`
```
$ dokku plugin:install https://github.com/dokku/dokku-redis.git redis
$ dokku redis:create tangl-redis
$ dokku redis:link tangl-redis tangl
```
- Dokku will set REDIS_URL automatically; TANGL_REDIS_URL can be set manually if needed.

On your development system.

- Add dokku remotes for your web client and backend api
- Set API_BASE_URL to https://api.storytangl.example.com in your app's production env.
- push `tangl-web:latest`, `tangl:latest`

Connect at https://app.storytangl.example.com

## https
Install the Dokku LetsEncrypt plugin and enable TLS:
```
$ dokku plugin:install https://github.com/dokku/dokku-letsencrypt.git
$ dokku letsencrypt tangl
$ dokku letsencrypt tangl-web
```
- Ensure global email is set: dokku config:set --global DOKKU_LETSENCRYPT_EMAIL=you@example.com
