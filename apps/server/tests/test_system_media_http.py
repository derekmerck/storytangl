from __future__ import annotations

from fastapi.testclient import TestClient

from tangl.rest import media_mounts, media_server
from tangl.rest.media_mounts import mount_system_media


def test_sys_media_http_serving(client: TestClient, tmp_path, monkeypatch) -> None:
    sys_media_dir = tmp_path / "sys_media"
    sys_media_dir.mkdir()
    (sys_media_dir / "logo.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
        '<rect width="32" height="32" fill="blue"/></svg>'
    )

    monkeypatch.setenv("TANGL_SERVICE__PATHS__SYSTEM_MEDIA", str(sys_media_dir))

    app = client.app
    monkeypatch.setattr(media_mounts, "get_sys_media_dir", lambda: sys_media_dir)
    mount_system_media(app, force=True)
    mount_system_media(media_server.app, mount_path="/sys", force=True)

    response = client.get("http://test/media/sys/logo.svg")

    assert response.status_code == 200
    assert response.text.startswith("<svg")
