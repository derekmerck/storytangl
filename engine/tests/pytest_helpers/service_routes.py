"""Explicit canonical service-to-REST coverage for conformance tests."""

ROUTES = {
    "story.create": {("POST", "/story/create")},
    "story.do": {("POST", "/story/do")},
    "story.update": {("GET", "/story/update")},
    "story.info": {("GET", "/story/info")},
    "story.drop": {("DELETE", "/story/drop")},
    "user.create": {("POST", "/user/create")},
    "user.update": {("PUT", "/user/world"), ("PUT", "/user/secret")},
    "user.info": {("GET", "/user/info")},
    "user.drop": {("DELETE", "/user/drop")},
    "user.key": {("GET", "/system/secret")},
    "world.list": {("GET", "/system/worlds")},
    "world.info": {("GET", "/world/{world_id}/info")},
    "world.preflight": {("GET", "/world/{world_id}/preflight")},
    "system.info": {("GET", "/system/info")},
}

# These canonical operations intentionally have no remote implementation in v1.
REMOTE_UNSUPPORTED = {"world.media", "world.load", "world.unload", "system.reset"}

# The world-update route is mounted but returns 501; remote update accepts a secret only.
REST_STUB_ROUTES = {("PUT", "/user/world")}
