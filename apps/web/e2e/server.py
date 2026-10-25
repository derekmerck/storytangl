"""Serve the built client and real REST app in one isolated smoke-test process."""

from copy import deepcopy
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory

import uvicorn

from tangl.config import settings


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[3]
    with TemporaryDirectory(prefix="storytangl-browser-") as temporary:
        root = Path(temporary)
        copytree(repo / "worlds/reference", root / "worlds/reference")
        settings.set("service.paths.worlds", [root / "worlds"])
        settings.set("service.paths.client_dist", repo / "apps/web/dist")
        for key in ("user_data", "story_media", "cache_data"):
            directory = root / key
            directory.mkdir()
            settings.set(f"service.paths.{key}", directory)
        settings.set("service.persistence", "native_in_mem")
        settings.set("service.caches.shelved", False)
        settings.set("client.secret", "browser-server-bootstrap")

        from tangl.rest.app import app

        logs = repo / "apps/web/e2e-artifacts"
        logs.mkdir(exist_ok=True)
        config = deepcopy(uvicorn.config.LOGGING_CONFIG)
        config["handlers"]["file"] = {
            "class": "logging.FileHandler",
            "filename": str(logs / "server.log"),
            "mode": "w",
            "formatter": "default",
        }
        for logger in ("uvicorn", "uvicorn.access"):
            config["loggers"][logger]["handlers"].append("file")
        uvicorn.run(app, host="127.0.0.1", port=4173, log_config=config)
