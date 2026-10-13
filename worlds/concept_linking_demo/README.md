# Recasting Rin

This optional exact-linking example builds on Meeting Rin without changing its
raw-text contract. The domain contributes `LinkedProseYamlCodec` and naming
authorities; the manifest selects that codec. Separately, `link_prose: true`
opts world/scene/block narrative into linking. Naming defaults are not consent.

Run `poetry run pytest engine/tests/prose/test_linking.py`, or execute
`run_script worlds/concept_linking_demo/cli_witness.txt` in the normal CLI.

```yaml
roles:
  host: {actor_ref: rin}
blocks:
  introduction:
    prose:
      - text: "Rin approaches."
      - speaker: host
        text: "This is my sister, Nanae."
      - text: "Rin #intro smiles. Rin waves."
      - raw: true
        text: "Rin #intro remains literal."
      - template: "{{ reference(host, 'anonymous') }} waits."
```

The first reference and speaker label are anonymous. Speech remains exactly
authored, without identifying Nanae. The narrative marker introduces the
current provider of `meeting:host`; subsequent references and labels use that
provider's narrator knowledge. Recasting host to Nanae changes future wording
without recompiling and does not inherit Rin's knowledge. Earlier fragments
remain historical output. The tests recast, restore, replay, roll back, and
follow an actual return edge.

Only visible Role/Setting declarations are eligible. Templates supply proper
and anonymous reference spellings, not frozen actor identities. Nearer bindings
shadow outer ones; two roles adopting the same spelling are ambiguous. Use an
exact role symbol or an explicit mapping when spelling differs from the
reference prototype:

```yaml
link_forms:
  host: {proper: Rin, anonymous: the blonde girl}
```

Matching preserves punctuation and whitespace, uses exact word boundaries and
longest spellings, and adopts the entire anonymous nominal with its determiner.
Its initial-capital spelling is supported; arbitrary case/determiner changes
are not. `Rin#intro` and `Rin #intro` are equivalent. `\Rin #intro` escapes
that mention and its marker, producing literal `Rin #intro`. `link_prose: false`
leaves a block's raw content untouched.

This first grammar requires explicit ordered segments for linked dialog and
mixed template/narrative content. Speaker bodies are never scanned, even if
they contain #intro or template-looking text. Explicit template segments are
not scanned. Ordinary Jinja `content` keeps its whole-block late-binding path
and receives no lexical linking. Opted-in dialog callout content is rejected
with a source-attributed instruction to use speaker segments. Put code or other
opaque text in raw segments; there is no general Markdown/Jinja parser, NLP,
pronoun or spoken-name inference. Choice text is raw; explicit choice-label
references from Meeting Rin are still available.

The codec performs a pure declaration-catalog compile before normal world
compilation, not runtime provisioning. Custom short kind aliases must be passed
to its constructor. Custom linked block types must inherit ProseBlock; their
type is preserved. Persistence uses normal graph constructor form; normal
`manager.open_world("concept_linking_demo")` bootstrap precedes cold JSON session
restoration. General failed-traversal recovery and hot reload remain out of scope.
