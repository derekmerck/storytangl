# Web Client Documentation Strategy

## Overview

Unlike Python which has Sphinx + autodoc, the JavaScript/Vue ecosystem uses different tools. Here's your documentation stack for the web client.

## 📚 Recommended Tools

### 1. JSDoc for Code Documentation (Python docstring equivalent)

```typescript
/**
 * Remaps relative URLs to absolute URLs using the API base URL
 * 
 * @param url - The URL to remap (relative or absolute)
 * @returns The remapped absolute URL
 * @example
 * ```ts
 * remapURL('/media/image.png')
 * // returns 'http://localhost:8000/media/image.png'
 * ```
 */
export function remapURL(url: string): string {
  // implementation
}
```

### 2. VitePress (Sphinx equivalent)

```bash
yarn add -D vitepress
npx vitepress init
```

Supports Markdown + Vue components + MyST-style syntax

### 3. Storybook (Component showcase)

```bash
yarn add -D @storybook/vue3
npx storybook@latest init
```

Interactive component playground with auto-generated prop tables.

### 4. TypeDoc (autodoc equivalent)

```bash
yarn add -D typedoc
npx typedoc --out docs/api src
```

## 🎯 Recommended for StoryTangl

**Now (MVP):** JSDoc + README files + your current `/notes` directory

**Later:** Add VitePress when you have 10+ components

## 📝 Documentation Pattern

**Each component gets:**
1. JSDoc for props/emits
2. README.md with usage examples  
3. Tests demonstrating usage

**Example:**
```
src/components/story/StoryBlock/
├── StoryBlock.vue        # Component with JSDoc
├── StoryBlock.test.ts    # Usage examples
└── README.md             # High-level docs
```

## 🔗 Integrating with Sphinx

Keep them separate but link between:

**In Sphinx `docs/source/web_client.rst`:**
```rst
Web Client
==========

See `apps/web/notes/ARCHITECTURE.md` for web client architecture.
```

## 💡 My Recommendation

For now, your current approach is perfect:
- ✅ Markdown files in `/notes` (ARCHITECTURE.md, QUICK_REFERENCE.md, etc.)
- ✅ JSDoc comments in TypeScript files
- ✅ README files for components

Later, when you have 20+ components, add VitePress.

**Tools comparison:**

| Tool | Like | Use For | Time |
|------|------|---------|------|
| JSDoc | docstring | Inline docs | Now |
| Markdown + notes/ | Manual docs | Architecture | Now |
| VitePress | Sphinx | Full site | Later |
| Storybook | N/A | Component showcase | Optional |
