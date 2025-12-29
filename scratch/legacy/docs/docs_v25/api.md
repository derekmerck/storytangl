# API

## Public

Public calls are stateless and do not require a context.

```{eval-rst}
.. automodule:: tangl.api.public_api
```

## Story

Story calls are stateful, they interrogate or advance a game context.

```{eval-rst}
.. automodule:: tangl.api.story_api
```

## Account

Account calls can be used to manage the player's account.

```{eval-rst}
.. automodule:: tangl.api.account_api
```

## Restricted

The restricted API methods can be used for testing and direct access to a game context.

```{eval-rst}
.. automodule:: tangl.api.restricted_api
```

## RESTful API

The `tangl.rest` module provides a [fastapi] RESTful backend server.  

[fastapi]: https://https://fastapi.tiangolo.com/

```bash
$ python -m tangl.rest
```

or 

```bash
$ tangl-serve
```

Current api documentation can also be referenced from the `/docs` endpoint of the server.

```{eval-rst}
.. openapi:: ../tangl/rest/openapi.json
```

An older [Flask][]/[Connexion][] server is also archived in the `legacy` directory.  However, the endpoints are _slightly_ different.

[flask]: https://flask.palletsprojects.com/en/2.2.x/
[connexion]: https://github.com/spec-first/connexion
