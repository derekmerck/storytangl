"""Project metadata.

In-repo project metadata generally uses major.minor only, with patch releases
reserved for git tags and other semver-only surfaces. Patch bumps introduce
features, minor bumps mark breaking changes or significant rewrites, and major
bumps mark architectural reorganization. Compact labels such as `v38` are
informal no-period shorthands for filenames, branches, and notes; they are not
numeric encodings and should be chosen for readability in context.

When bumping the major or minor StoryTangl version, update this module and then
search the repo for explicit release-version strings. Known places that may
intentionally carry the project version include `pyproject.toml`, Docker labels
and example image tags under `deployment/docker/`, `docs/src/conf.py`, web app
package/footer defaults under `apps/web/`, app/server tests, and generated
OpenAPI notes. Historical design and migration docs may also mention older
versions on purpose, so review matches rather than replacing blindly.
"""

# tangl/info.py
__name__ = "tangl"
__desc__ = "The abstract narrative graph lib for interactive stories"
__title__ = "StoryTangl"
__author__ = "TanglDev"
__author_email__ = "tangldev@storytan.gl"
__url__ = "https://github.com/derekmerck/storytangl"
__version__ = "3.8"
