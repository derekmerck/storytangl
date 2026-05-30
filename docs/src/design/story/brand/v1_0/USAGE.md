# StoryTan⅁l · brand usage

Read [`StoryTangl-Brand-Sheet.html`](./StoryTangl-Brand-Sheet.html) first.
This file is the rules-of-the-road that the brand sheet implies but doesn't
spell out. Same voice as `AGENTS.md` — opinionated, parsimonious, explicit
about what an agent must never do.

## 1. The mark

The wordmark is **"StoryTangl" in the body font, with the lowercase `g`
rotated 180°.** The rotation *is* the brand. Stripping it produces a
wordmark indistinguishable from any other project; do not do this.

The rotation requires per-font tuning so the lip lands on the baseline and
the new descender matches its neighbors. Three tunings are sanctioned:
Newsreader (canonical), JetBrains Mono (CLI), Inter Tight (web chrome).
Custom tunings for new fonts require updating the brand sheet first.

## 2. Where each asset goes

| Asset | Destination | Format |
|-------|-------------|--------|
| `wordmark.svg` | `assets/brand/wordmark.svg` (or wherever the repo's brand assets live) | SVG with webfont |
| `glyph.svg` / `glyph-round.svg` | `assets/brand/glyph*.svg` | SVG with webfont |
| `favicon.svg` | `apps/web/public/favicon.svg`, `docs/src/_static/favicon.svg` | SVG with webfont (browsers cache it locally; fallback to `favicon.ico` for IE11-era) |
| `README-banner.svg` | `assets/brand/README-banner.svg`; reference in `README.md` as the hero image above the `# StoryTangl` line | SVG with webfont |
| `social-card.svg` | `.github/social-preview.png` (rasterize first; GitHub doesn't accept SVG for social previews) | PNG export at 1280×640 |
| `cli-splash.txt` | `apps/cli/src/tangl/cli/assets/splash.txt`, loaded by the cmd2 app on launch | plain text |
| `palette.css` | `apps/web/src/styles/storytangl-palette.css`; `docs/src/_static/storytangl-palette.css` | CSS |
| `type.css` | same | CSS |

## 3. SVGs are font-dependent — when to convert to paths

The shipped SVGs reference Newsreader and JetBrains Mono via Google Fonts
`@import`. This works wherever webfonts can load (RTD docs, web app, any
HTML page). It does **not** work for:

- GitHub social previews (must be rasterized PNG)
- LaTeX includes, PowerPoint, anywhere the renderer can't fetch URLs
- Offline-first contexts

For those, convert the wordmark and glyph to outlined paths using any of:

```bash
# inkscape
inkscape wordmark.svg --export-type=svg --export-filename=wordmark-paths.svg \
         --export-text-to-path

# fontforge / harfbuzz approaches also work
# online: https://danmarshall.github.io/google-font-to-svg-path/
```

The path version is checked in alongside the font-dependent SVG; downstream
choose by context. Do not regenerate paths without confirming the
typographic tuning matches §1 of the brand sheet (per-font sx/sy/ty values).

## 4. The lockup is the wordmark or the wordmark + glyph — never the glyph alone with text

The glyph stands alone. The wordmark stands alone. A glyph + wordmark
lockup is sanctioned (see §3 of the brand sheet). What is **not** sanctioned:

- **glyph + plain "StoryTangl" text** (defeats the whole mark)
- **glyph + a different word** (the mark is bound to its wordmark)
- **two glyphs as a repeating pattern** (use the dotty knot texture instead)

## 5. The ⅁ character (U+2141) is the ASCII fallback

Where SVG isn't available (terminal, plain text, code comments, commit
messages, this very file's H1), use the Unicode codepoint **U+2141 TURNED
SANS-SERIF CAPITAL G** — `⅁`. It's the project's name in 7-bit-clean
contexts. Acceptable substitutes: none.

Examples:

```
StoryTan⅁l         ← H1 in plain markdown
⅁>                  ← CLI prompt
[ ⅁ v38.3 ]        ← log banner
```

## 6. Type stack rules

Three families, three roles, never mixed.

- **Newsreader** — prose, titles, narrative copy, the wordmark
- **JetBrains Mono** — engine output, CLI, inline code, fragment data
- **Inter Tight** — UI chrome, navbar, buttons, small labels, table headers

If you find yourself reaching for a fourth font, stop. Reach for weight or
size instead. The only sanctioned weight escalation is 400 → 500 → 600 →
700, in order. No 800/900 unless you need a wordmark above 200px.

## 7. Palette rules

The palette is **closed.** Additions require updating this file AND the
brand sheet AND `palette.css`. Specifically:

- **No new surfaces.** Paper / paper-2 / paper-3 cover everything from
  page background to banded table rows. If your design "needs" a fourth,
  it doesn't.
- **No new ink levels.** Ink / ink-2 / ink-3 / ink-4 cover the hierarchy.
- **No new accents.** Blue-pencil and burnt are the two. Burnt is for
  *one* moment per page; never two.
- **Severity is fixed at three.** `ok` / `warn` / `danger`. If a context
  needs four (e.g. distinguishing "criminal" from "failed"), use weight or
  emphasis on the danger color, not a fourth hue.

The dark mode (`[data-st-mode="ink"]`) is a literal photographic negative.
Do not tune it independently; if the light mode changes, the dark mode
changes in lockstep.

## 8. Voice and tone rules

Lineage: README.md, ARCHITECTURE.md, AGENTS.md.

- **The project is a research platform**, not a SaaS product. Copy says
  so without apology.
- **No SaaS verbs.** Revolutionize, unlock, empower, transform — all
  forbidden. The engine *compiles*, *materializes*, *projects*, *traverses*.
- **No emoji in headlines.** Body text rarely; never decorative.
- **Dry humor is in.** "AI agents occasionally suggest things that are
  actually good." That register. Not zany; not corporate-friendly.
- **Caveats live in the prose, not in disclaimers.** "Useful for development,
  not a production MVP" is one of the project's better sentences.

## 9. What an agent must never do

This section exists because agents have done some of these things.

| Never | Why |
|-------|-----|
| Strip the `g` rotation from the README title because it "looks silly in markdown" | The rotation is the brand. The fix is an SVG banner above the title, not removing the rotation. |
| Replace the wordmark with a generic logo because "the project doesn't have a logo" | It does. It's the wordmark. The wordmark *is* the logo. |
| Add a "modern" gradient or "playful" color pop because the palette "feels muted" | Muted is the brand. Reach for the blue-pencil or burnt accent if you need a pop. |
| Substitute Inter or a system font for Newsreader because "fewer requests" | The wordmark is set in Newsreader. The body prose is set in Newsreader. Removing it removes the brand. |
| Auto-update SVG path data without re-tuning per §1 | Path data carries the per-font tuning. Regenerating without confirming the visual tuning will produce a wrong wordmark that looks subtly off. |
| Emoji in the README, the docs, or commit messages | See §8. |

## 10. Provenance

The flipped letterform comes from an earlier currency mark — inverted `Ɐ`
in `Ɐ$`, the "horn" of an imperial coinage from a worldbuilding project
predating StoryTangl. The transformation moved to a different letter when
this engine needed a name. The lineage is recorded in §9 of the brand sheet
because lineage matters for a research platform.

Do not "modernize" the mark away from this lineage.

---

*Brand sheet v1.0 · 2026-05 · ⅁*
