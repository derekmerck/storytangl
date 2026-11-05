"""Optional Chromium SVG rasterization with a transparent contain-fit viewport."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path
import subprocess
from typing import Callable, Coroutine, TypeVar

T = TypeVar("T")


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
    result = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False)
    if result.returncode or not result.stdout.strip():
        raise RendererUnavailable("Cannot determine Chromium version")
    return executable, f"chromium:{result.stdout.split()[-1]};playwright:{version('playwright')}"


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
                if f"chromium:{browser.version};playwright:{version('playwright')}" != identity:
                    raise RendererUnavailable("Chromium version changed before rendering")
                page = await browser.new_page(viewport={"width": dims[0], "height": dims[1]},
                                              device_scale_factor=1)
                await page.set_content('<!doctype html><html><head><style>'
                    f'html,body{{margin:0;width:100%;height:100%;background:{background}}}'
                    'svg{display:block;width:100%;height:100%}'
                    '</style></head><body></body></html>')
                await page.evaluate("""svg => {
                    const doc = new DOMParser().parseFromString(svg, 'image/svg+xml');
                    const root = doc.documentElement;
                    if (root.localName !== 'svg') throw new Error('Invalid SVG');
                    root.setAttribute('preserveAspectRatio', 'xMidYMid meet');
                    root.style.setProperty('width', '100%', 'important');
                    root.style.setProperty('height', '100%', 'important');
                    document.body.appendChild(document.importNode(root, true));
                }""", svg)
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
