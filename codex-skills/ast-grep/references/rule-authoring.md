# ast-grep Rule Authoring

## Minimal reusable rule

```yaml
id: no-console-log
language: ts
rule:
  pattern: console.log($$$ARGS)
message: Avoid console.log in production code.
severity: warning
```

Add `fix:` only after the matcher is correct.

## Minimal rewrite rule

```yaml
id: prefer-let
language: js
rule:
  pattern: var $NAME = $VALUE
fix: let $NAME = $VALUE
message: Prefer let over var.
severity: warning
```

## Minimal sgconfig.yml

```yaml
ruleDirs:
  - rules
testConfigs:
  - testDir: rule-tests
utilDirs:
  - utils
```

Paths are resolved relative to `sgconfig.yml`.

## Recommended development loop

1. Collect one or two real examples from the codebase.
2. Write the smallest matcher that finds the positive case.
3. Validate the matcher with `ast-grep run` or `ast-grep scan`.
4. Add relational rules like `inside`, `has`, `all`, `any`, or `not` only after the base match works.
5. Add `fix` or `transform` only after the matcher is stable.
6. Add test cases and run `ast-grep test -c sgconfig.yml`.

## Debugging checklist

- Confirm the `language` is correct.
- Confirm the pattern is valid syntax in that language.
- If a tiny expression does not match, provide more surrounding code context.
- Use `--debug-query=ast` or `--debug-query=cst` to see how the pattern parses.
- Generalize from a concrete code sample with meta variables like `$A` or `$$$ARGS`.
- If the query grows complex, move it into YAML and test it there instead of fighting a giant shell command.

## When to reach for transforms

Use transforms when the replacement depends on captured values and simple string substitution is not enough. Keep the initial rule focused on matching first, then add transform logic as a separate step once the test cases pass.
