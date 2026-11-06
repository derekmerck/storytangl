"""Optional Chromium SVG rasterization with a transparent contain-fit viewport."""
from __future__ import annotations

import asyncio
from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path
import subprocess
from typing import Callable, Coroutine, TypeVar
from lxml import etree

T = TypeVar("T")
_RENDERER_REVISION = "svg-image:2"


class RendererUnavailable(ValueError):
    """The optional renderer or its browser is not available."""


def _run(factory: Callable[[], Coroutine[object, object, T]]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(factory())).result()


async def _browser_info() -> tuple[str, str]:
    if find_spec("playwright") is None:
        raise RendererUnavailable("Install the svg-png extra to render PNG figures")
    from playwright.async_api import Error, async_playwright

    try:
        async with async_playwright() as playwright:
            executable = playwright.chromium.executable_path
    except Error as exc:
        raise RendererUnavailable("Playwright is unavailable") from exc
    if not Path(executable).is_file():
        raise RendererUnavailable("Playwright Chromium is not installed")
    try:
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False)
    except OSError as exc:
        raise RendererUnavailable("Cannot determine Chromium version") from exc
    if result.returncode or not result.stdout.strip():
        raise RendererUnavailable("Cannot determine Chromium version")
    return executable, (f"chromium:{result.stdout.split()[-1]};"
                        f"playwright:{version('playwright')};{_RENDERER_REVISION}")


def renderer_identity() -> str:
    return _run(_browser_info)[1]


async def _render(svg: str, dims: tuple[int, int], background: str, identity: str) -> bytes:
    from playwright.async_api import Error, async_playwright

    executable, actual = await _browser_info()
    if actual != identity:
        raise RendererUnavailable("Chromium version changed before rendering")
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(executable_path=executable)
            try:
                if (f"chromium:{browser.version};playwright:{version('playwright')};"
                        f"{_RENDERER_REVISION}") != identity:
                    raise RendererUnavailable("Chromium version changed before rendering")
                page = await browser.new_page(viewport={"width": dims[0], "height": dims[1]},
                                              device_scale_factor=1)
                await page.set_content('<!doctype html><html><head><style>'
                    f'html,body{{margin:0;width:100%;height:100%;background:{background}}}'
                    'img{display:block;width:100%;height:100%;object-fit:contain}'
                    '</style></head><body><img></body></html>')
                data = b64encode(svg.encode("utf-8")).decode("ascii")
                await page.evaluate("""async data => {
                    const image = document.querySelector('img');
                    image.src = 'data:image/svg+xml;base64,' + data;
                    await image.decode();
                }""", data)
                return await page.screenshot(omit_background=background == "transparent")
            finally:
                await browser.close()
    except Error as exc:
        raise RendererUnavailable("Chromium rendering failed") from exc


def render_svg(svg: str, dims: tuple[int, int], *, background: str = "transparent",
               identity: str | None = None) -> bytes:
    if len(dims) != 2 or any(not isinstance(value, int) or value <= 0 for value in dims):
        raise ValueError("PNG dimensions must be positive integers")
    if background not in {"transparent", "white"}:
        raise ValueError("PNG background must be transparent or white")
    root = etree.fromstring(svg.encode("utf-8"), etree.XMLParser(resolve_entities=False, no_network=True))
    view_box = root.get("viewBox", "").replace(",", " ").split()
    if len(view_box) != 4:
        raise ValueError("PNG source requires a valid viewBox")
    root.set("width", view_box[2])
    root.set("height", view_box[3])
    root.set("preserveAspectRatio", "xMidYMid meet")
    svg = etree.tostring(root, encoding="unicode")
    identity = identity or renderer_identity()
    return _run(lambda: _render(svg, dims, background, identity))


def render_svg_file(svg_path: Path, outfile: Path | None = None,
                    dims: tuple[int, int] | None = None) -> bytes:
    if dims is None:
        raise ValueError("PNG dimensions are required")
    result = render_svg(Path(svg_path).read_text(), dims)
    if outfile is not None:
        Path(outfile).write_bytes(result)
    return result
