---
name: ast-grep
description: Structural code search, syntax-aware rewrites, and ast-grep rule authoring for polyglot repositories. Use when Codex should match code by AST shape instead of plain text, inspect or rewrite language constructs safely, debug non-matching ast-grep patterns, scaffold or edit sgconfig.yml projects, or create and test reusable YAML rules.
---

# ast-grep

Use `ast-grep` for syntax-aware code search and transforms. Prefer it over plain-text search when the request is about code structure such as imports, function signatures, JSX trees, method calls, arguments, declarations, or nested language constructs.

When the user is still discovering domain concepts in an unfamiliar codebase, do not jump straight to `ast-grep`. First use fast text and file discovery to learn the local vocabulary, then use `ast-grep` once the relevant syntax shape is clear.

## Choose the Right Tool

- Use `rg` for filenames, docs, comments, or exact text search.
- Use `rg` first when the task is concept discovery: architecture docs, design notes, docstrings, feature names, config keys, and other domain vocabulary.
- Use `ast-grep run` for one-off structural searches and small rewrites.
- Use `ast-grep scan` when the work should be encoded as reusable YAML rules.
- Use `ast-grep test` whenever you add or change reusable rules.

## Discovery Workflow

Use this sequence in unfamiliar or documentation-heavy repositories:

1. Use `rg --files` and `rg` to locate design docs, contributor notes, module docstrings, and obvious symbol names.
2. Read the most authoritative docs and entry-point files first to learn the project's vocabulary and architectural boundaries.
3. Translate the concept into code shapes such as inheritance, decorators, calls, field declarations, or argument patterns.
4. Switch to `ast-grep` only after the syntax shape is clear enough to express.

Example:

- If the user asks "how does this project handle runtime orchestration?", start with docs and text search for names like `Orchestrator`, `Gateway`, or endpoint decorators.
- After you identify the relevant structures, use `ast-grep` to find exact call shapes or class patterns such as orchestrator dispatch calls or subclasses of a base entity.

## One-Off Workflow

1. Identify the language and search path first.
2. Start with the smallest syntax-valid pattern that could match.
3. Run `ast-grep run --lang <lang> -p '<pattern>' <path>`.
4. If the match fails, inspect with `--debug-query=ast` or `--debug-query=cst` and simplify the pattern before adding complexity.
5. Add rewrite logic only after the match is stable.

Prefer non-interactive commands in agent workflows. Avoid `--interactive` unless the user explicitly wants an interactive editing session. For machine-readable output, use `--json=stream`.

## Reusable Rule Workflow

Use reusable rules when the user wants repeatable linting, a migration rule, or a repo-wide policy.

1. If the repo does not already have `sgconfig.yml`, scaffold one with `ast-grep new project`.
2. Add a rule with `ast-grep new rule <name> --lang <lang> -c sgconfig.yml -y`.
3. Add a test case with `ast-grep new test <name> -c sgconfig.yml -y`.
4. Encode the smallest working matcher first, then layer on `inside`, `has`, `all`, `any`, `not`, constraints, transforms, or fixes.
5. Run `ast-grep scan -c sgconfig.yml <paths>` and `ast-grep test -c sgconfig.yml` before handing results back.

## Pattern and Rule Heuristics

- Write patterns as real code in the target language. Invalid syntax will not parse well.
- If a bare expression does not match, provide more surrounding context and narrow the effective node with selectors or relational rules.
- Start from a concrete code sample from the repo, then generalize with meta variables.
- Keep rewrites conservative. Review matches before applying `-U` across a tree.
- Prefer a YAML rule over a giant shell command once the query becomes relational or needs tests.

## References

- Read [command-cheatsheet.md](references/command-cheatsheet.md) for the core CLI commands and decision rules.
- Read [rule-authoring.md](references/rule-authoring.md) when creating or debugging YAML rules, `sgconfig.yml`, tests, fixes, or transforms.
