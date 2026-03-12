# ast-grep Command Cheatsheet

## Tool choice

- Use `rg` when the user wants exact text, filenames, comments, or prose.
- Use `rg` first when you are still learning the repository's vocabulary, architecture, or documentation trail.
- Use `ast-grep` when the user wants syntax-aware matches such as imports, calls, declarations, JSX elements, or argument shapes.

## Recommended sequence for concept discovery

1. Use `rg --files` to find likely docs, design notes, config files, and module entry points.
2. Use `rg` on concept words to discover the local names and symbols the repo uses.
3. Use `ast-grep` only after the question has been translated into a syntax shape.

This avoids using `ast-grep` too early for questions that are really about terminology or architecture, not code structure yet.

## Core commands

### One-off search

```bash
ast-grep run --lang ts -p 'useEffect($A, $B)' engine/src
```

### Search with JSON output

```bash
ast-grep run --lang py -p 'print($$$ARGS)' --json=stream engine/src
```

Use `--json=stream` when another tool or script will consume the results.

### Rewrite

```bash
ast-grep run --lang js -p 'var $A = $B' -r 'let $A = $B' src
```

Only add `-U` after reviewing the pattern carefully. In agent workflows, prefer inspection and targeted application over interactive editing.

### Debug a pattern

```bash
ast-grep run --lang go -p 'fmt.Println($A)' --debug-query=ast .
```

Useful debug formats:

- `pattern`: parsed pattern form
- `ast`: named-node AST
- `cst`: full concrete syntax tree
- `sexp`: s-expression output

### Rule-based scan

```bash
ast-grep scan -c sgconfig.yml .
```

Use `scan` for reusable YAML rules, multi-rule projects, and policy checks.

### Rule tests

```bash
ast-grep test -c sgconfig.yml
```

Run this whenever you add or change a reusable rule.

## Project scaffolding

### New ast-grep project

```bash
ast-grep new project
```

This creates `sgconfig.yml`, rule directories, test directories, and utils directories.

### New rule

```bash
ast-grep new rule no-console --lang ts -c sgconfig.yml -y
```

### New test

```bash
ast-grep new test no-console -c sgconfig.yml -y
```

## Practical guidance

- Start with the smallest syntax-valid pattern that could possibly match.
- Use explicit `--lang` whenever there is any ambiguity.
- Use `--globs` when the search should be narrower than the whole repo.
- Use `--stdin` for small experiments against inline snippets.
- Use `scan` and `test` rather than piling more complexity into a single `run` command.
