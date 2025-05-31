"""
Playwright is a headless browser renderer

Stand-alone svg renderers (cairosvg, batik) do not support 'mix-blend-mode' compositing.
So a heavy-weight solution is required for server-side rendering.
"""

from pathlib import Path
import re
import asyncio
from playwright.async_api import async_playwright

from .svg_viewbox_size import svg_viewbox_size

def render_svg_file(svg_path, outfile=None, dims=None) -> bytes:

    # Read the SVG content
    with open(svg_path, 'r') as svg_file:
        svg = svg_file.read()
    res = render_svg(svg, dims, outfile)
    return res


async def render_svg(svg, dims, outfile = None):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        if not dims:
            dims = svg_viewbox_size(svg)

        width, height = dims

        # Set the viewport size
        await page.set_viewport_size({"width": width, "height": height})

        # Create a simple HTML content to render the SVG
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>SVG Renderer</title>
            <style>
                body, html {{
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                svg {{
                    width: 100%;
                    height: 100%;
                }}
            </style>
        </head>
        <body>
            {svg}
        </body>
        </html>
        """

        # Set the content of the page
        await page.set_content(html_content)

        # Take a screenshot and save as PNG
        res = await page.screenshot(path=outfile)

        await browser.close()
        return res
