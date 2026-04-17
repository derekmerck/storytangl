# language=yaml
"""
# controller types
acls:
  - public
  - client               # req valid user
  - dev                  # req valid user w privilege flag

response_types:
  # read job responses
  - content              # meta + fragments
  - info
    - story              # flexible record with world-specific content
    - world              # fixed domain record
    - system             # fixed domain record
    - user               # fixed domain record
  - media                # redirect, binary, binary encoded, svg/xml
  # create, update, drop job responses
  - runtime              # job type/domain, status OK, result - often an index or dict of raw values

request_params:
  w: world-name
  n: entity- or choice-name
  s: secret
  f: format profile
  params: kwargs

---
# controller domains


story:
  # client
  - new_story(w)         # alias -> world/new_story
  - get_journal(params, f) # content (read)
  - get_info(params)     # story info (read)
  - get_media(n, f)      # media (read)
  - do(n, params)        # runtime (update)
  - drop                 # runtime

  # dev
  - inspect(n)           # runtime (f read)
  - goto(n)              # runtime (f update)
  - check(expr)          # runtime (f read)
  - exec(expr)           # runtime (f update)
  - ls                   # alias -> system/storage/ls_stories

world:
  # public
  - ls                   # runtime (index)
  - get_info(w)          # world info (read)
  - get_media(w, n, f)   # media (read)

  # client
  - new_story(w)         # runtime (create)

  # dev
  - load(params)         # runtime (create)
  - inspect(w)           # runtime (read)
  - unload(w)            # runtime (drop)

user:
  # public
  - new_user(s)          # runtime (create)

  # client
  - get_info(params)     # user info (read)
  - update_secret(s)     # runtime
  - drop                 # runtime

  # dev
  - ls                   # alias -> system/storage/ls_users

system:
  # public
  - get_info(params)     # system info (read)
  - get_media(n, f)      # media (read)

  # dev
  - storage:
    - inspect            # runtime
    - ls_users           # runtime (index)
    - ls_stories         # runtime (index)
"""