# Destination-owned choice text

Run `run_script worlds/destination_choice_demo/cli_witness.txt` in the CLI.
The retained scheduled offer first reads “the blonde girl is performing in the
square”. Selecting it introduces Rin during actual JOURNAL execution, returns
through the ordinary sandbox call, and shows “Rin is performing in the square”.
The same Action ID survives; display does not introduce her or pay arrival time.

The destination authors `locals.action_text` and binds `host` to Rin. The hub
binds `host` to Beth and overrides naming policy to proper: the explicit event
text always says “Beth invites you”, proving that explicit text keeps its source
scope. The bench has no suggestion and keeps its public event label.

Navigation wording precedence at display is explicit edge/event text, destination
`locals.action_text`, destination `action_name`, destination `locals.menu_text`,
then the static public fallback. MenuBlock fanout follows the same policy.
This is not a universal ownership law for operations: game move projectors keep
their per-move handler wording as explicit source-owned text, so entry suggestions
cannot rename all moves. Navigation into a game still uses its entry suggestion.
Future named source/sponsor-owned operation overrides belong to #553, not this demo.
Destination templates use a fresh derived context, current state, narrator and
destination settings. They never simulate arrival or provision missing bindings.
An unrealized lazy target keeps its fallback; a realized but unbound required
role is an authoring/provisioning error. Standard `introduce()` calls in choice
templates fail before changing knowledge. Explicit semantic labels remain
supported; choice strings are not automatically lexically linked.

The destination's scoped `text_template` chooses its suggestion's dialect;
`fstring` is the default. Opt into `jinja` for `reference(host)` and other helper
calls. This demo inherits `text_template: jinja` from its globals. Explicit
edge/event text instead uses its source scope's dialect, not the destination's.

For explicit capitalization, author a suggestion such as:

```yaml
locals:
  text_template: jinja
  action_text: "{{ reference(host) | upper_first }} is performing in the square"
```

`upper_first` uppercases only the first character of the completed phrase,
preserving everything else without trimming: “the blonde girl” becomes “The
blonde girl”, “Rin and Nanae” stays unchanged, and “the NASA lab” becomes “The
NASA lab”. Jinja's built-in `capitalize` lowercases the remainder, so it would
change “Rin and Nanae” to “Rin and nanae”. This example is optional; the demo's
unfiltered suggestion/CLI output remains lowercase before identification.
The same filter is available in explicit `MuBlock.template` single-pass Jinja;
ordinary text retains its existing recursive rendering semantics.

Commands share menu disclosure: hidden unavailable offers are not evaluated or
exposed as ambiguity candidates. A visible suggestion's missing bindings or
forbidden introduction remain errors, not silently swallowed failures.

`Action.text` retains explicit source; `fallback_text` stores the generated
binding's public label separately from its synthetic identity. Neither stores a
rendered destination suggestion. Both persist through ordinary constructor-form
and JSON restore, with no custom serializer.
