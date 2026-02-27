# Scope Matching & Structural Provisioning Design

**Status:** Design reference (v2)
**Scope:** vm38/provision, core38/template, story38 prereq handlers
**Date:** 2026-02-26

---

## Problem Statement

Template `scope` was overloaded to mean three things: where a template is
admitted (template-side), what a dependency is looking for (caller-side),
and where a provisioned node should be placed. This created a bootstrapping
paradox for structural provisioning — you can't walk a path through graph
structure that doesn't exist yet — and ambiguous behavior when concepts and
episodes used the same scope field with different intended semantics.

## Core Insight

Scope is a **predicate on the target placement context** of a provisioning
request.

- For **qualified** requirements (author wrote `castle.guard` or
  `morning.gatehouse`), the requirement path determines the target context.
- For **unqualified** requirements (author wrote `guard` or `gatehouse`),
  the caller's current position supplies the target context.

Scope answers one question: "Is this target context a valid home for an
instance of this template?" The matching algorithm is the same for concepts
and episodes. What differs is the **policy** applied after a match — whether
containers get built, and how the instance binds into the caller's namespace.

## Two Contexts

Every provisioning request has two contexts that must be named separately:

- **Request context** (`request_ctx`): Where the cursor currently is. The
  caller's position in the graph hierarchy, expressed as a dotted path
  (e.g. `village.tavern`).

- **Target context** (`target_ctx`): Where the provisioned instance would
  live. Derived from the requirement path if qualified, or from the request
  context if unqualified.

Scope is always evaluated against `target_ctx`, never directly against
`request_ctx`. The caller influences the target context only when the
requirement doesn't specify one.

## Path Resolution

Requirements may be fully qualified (`castle.gatehouse`), relative
(`morning.gatehouse` from a caller in `castle`), or bare (`guard`).
Before matching, the requirement is resolved to determine the target
context:

```
resolve(req_path, request_ctx):
    qualifier, name = split_last(req_path)
    if qualifier is not None:
        if is_relative(qualifier):
            return request_ctx + "." + req_path   # relative
        return req_path                            # absolute
    return request_ctx + "." + name                # bare → caller-anchored
```

**Bare names always resolve under the caller.** Resolution is fully
deterministic from the authored expression and the cursor position —
no graph or registry lookups at runtime. If a bare `scene2` should
mean `world.scene2`, the script compiler expands it to a qualified
path at compile time. This keeps runtime resolution stateless and
pushes convenience inference into the codec where it belongs.

The original authored form is preserved alongside the resolved form.
A requirement is **qualified** when the original authored path contains
at least one explicit segment beyond the bare name. This distinction
drives the episode policy fork (below).

## Three Separate Computations

Scope matching involves three independent computations. Earlier iterations
of this design conflated them; they must remain separate.

### 1. Admission (boolean)

Does the template's scope pattern accept the resolved target context?

Admission is **component-wise prefix matching**: the scope's non-wildcard
prefix segments must match the leading segments of the target context
positionally. The trailing `*` means "any depth below this prefix."

- `castle.*` admits `castle.X`, `castle.X.Y`, `castle.X.Y.Z`, etc.
- `castle.morning.*` admits `castle.morning.X`, `castle.morning.X.Y`, etc.
- `*` admits anything (universal).

```python
def admitted(template_scope: str, target_ctx: str) -> bool:
    if template_scope is None or template_scope == "*":
        return True
    scope_parts = template_scope.split(".")
    if scope_parts[-1] == "*":
        prefix = scope_parts[:-1]
    else:
        prefix = scope_parts  # exact prefix, no wildcard
    ctx_parts = target_ctx.split(".")
    # Target must have more segments than prefix (at least a leaf)
    if len(ctx_parts) <= len(prefix):
        return False
    # Prefix segments must match positionally
    return all(fnmatch(cp, sp) for sp, cp in zip(prefix, ctx_parts))
```

If admission fails, the template is not offered. Full stop.

**Note on depth:** In v1, `*` always means "any depth below the prefix."
There is no single-level-only wildcard. `castle.*` admits both
`castle.gatehouse` (depth 1) and `castle.morning.gatehouse` (depth 2).
If single-level restriction is needed later, a distinct syntax (e.g.
`castle.?`) can be added without changing existing scope strings.

### 2. Build Plan (episodes with qualified reqs only)

Which segments of the resolved target path are missing from the graph?
Computed by **prefix alignment** — walking the target path from root
and collecting missing segments:

```python
def build_plan(target_ctx: str, graph) -> list[str]:
    segments = target_ctx.split(".")
    plan = []
    current = graph.root
    for seg in segments[:-1]:  # walk prefix, not the leaf
        child = current.find_member(seg) if current else None
        if child is None:
            plan.append(seg)
            current = None  # subsequent segments are also missing
        else:
            current = child
    return plan
```

For MVP, the anchor is always root. LCA-relative anchoring (walking
only the suffix below the LCA of source and target) is a deferred
optimization that avoids redundant existence checks on shared
ancestor segments.

Build plans are **never derived from edit distance**. Levenshtein
substitutions do not correspond to "build a container" — a substitution
means "these are different things," not "this thing is missing." The
build plan comes from walking the path and noting gaps.

### 3. Distance (ranking among admitted candidates)

Component-wise Levenshtein on the path prefix segments, used to rank
admitted offers by affinity. A guard template scoped to `castle.*`
and a guard template scoped to `*` are both admitted when the target
context is `castle.guard`, but the castle-scoped one should rank higher.

```python
def scope_distance(template_scope: str, target_ctx: str) -> int:
    scope_parts = scope_prefix(template_scope)
    context_parts = context_prefix(target_ctx)
    return levenshtein(scope_parts, context_parts)
```

The Levenshtein cost function uses `fnmatch` per component so that `*`
segments in the scope match any context segment at cost 0:

```python
def levenshtein(a: list[str], b: list[str]) -> int:
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if fnmatch(b[j-1], a[i-1]) else 1
            dp[i][j] = min(
                dp[i-1][j] + 1,        # delete from scope
                dp[i][j-1] + 1,        # insert into scope
                dp[i-1][j-1] + cost,   # substitute
            )
    return dp[n][m]
```

### Prefix Extraction

```python
def scope_prefix(scope: str) -> list[str]:
    """Strip trailing wildcards to get the required context prefix."""
    parts = scope.split(".")
    while parts and parts[-1] in ("*", "**"):
        parts.pop()
    return parts

def context_prefix(resolved_path: str) -> list[str]:
    """Strip the leaf to get the positional context."""
    parts = resolved_path.split(".")
    return parts[:-1] if len(parts) > 1 else []
```

## Identity Check

The leaf/name match is a **binary gate**, not a distance component.
If the template doesn't satisfy the requirement's selector criteria
(name, kind, tags), the match fails immediately. No admission check
or distance is computed.

The prefix segments are homogeneous — all container-level, all
navigational, and edits between them are meaningful as distance. The
leaf is categorical identity. A leaf mismatch is "wrong thing," not
"nearby thing." These concerns must not be mixed into a single metric.

Future extension: fuzzy identity via tags, synonyms, or kind matching
can be added as a secondary identity score without changing the distance
metric. The sort key becomes `(identity_score, scope_distance, ...)`.

## Policy Fork: Concepts vs Episodes

The admission check and distance metric are identical for both. The
**policy** applied to the result differs:

| Distance | Concept | Episode (qualified req) | Episode (unqualified req) |
|----------|---------|------------------------|--------------------------|
| 0        | ✓ offer | ✓ offer, no build      | ✓ offer, no build        |
| 1+       | ✓ offer, penalized | ✓ offer if chain buildable | ✗ no offer |
| not admitted | ✗ no offer | ✗ no offer | ✗ no offer |

**Concepts:** Scope is a relevance filter. An admitted concept at any
distance is offered with a cost penalty proportional to distance. The
instance binds into the caller's current namespace regardless of where
the target context points — the target context determined *which*
template to use, not where the instance lives structurally.

**Episodes, qualified:** The requirement path determines the full
structural chain. Each missing segment in the chain is a container to
build. The build plan is derived from prefix alignment, not from the
distance metric. The offer carries the plan; the callback executes it.

**Episodes, unqualified:** The requirement doesn't specify enough path
to determine what to build. The caller's position supplies the target
context for admission, but if that doesn't produce a distance-0 match,
the template is not offered. The system does not infer containers from
the template's scope — that would be the engine guessing structural
intent the author didn't express.

### Qualified vs Unqualified

A requirement is "qualified" when the original authored path contains
at least one explicit segment beyond the bare name:

- `castle.gatehouse` → qualified (author specified `castle`)
- `morning.gatehouse` from caller `castle` → qualified (author specified
  `morning`; resolves to `castle.morning.gatehouse`)
- `gatehouse` from caller `castle` → **unqualified** (author gave only
  the name; context came from caller position)

Only qualified episode requirements can trigger structural chain building.

## Reference Case Table

Target context is shown as the resolved absolute path. "Qualified" refers
to whether the original authored requirement (before resolution) contained
explicit path segments.

| # | Kind | Req (authored) | Scope on tmpl | Caller | Qualified? | Target ctx | Match? | Reason |
|---|------|---------------|--------------|--------|------------|-----------|--------|--------|
| 1 | concept | `guard` | `castle.*` on **aristocrat** | any | no | — | ✗ | Identity gate: name mismatch |
| 2 | concept | `guard` | `castle.*` on **guard** | `castle` | no | `castle.guard` | ✓ d=0 | Caller supplies target ctx |
| 3 | concept | `guard` | `castle.*` on **guard** | `village` | no | `village.guard` | ✗ | `village.guard` not admitted by `castle.*` |
| 4 | concept | `guard` | `castle.morning.*` on **guard** | `castle` | no | `castle.guard` | ✗ | `castle.guard` not admitted by `castle.morning.*` |
| 5 | concept | `castle.guard` | `castle.*` on **guard** | `castle` | yes | `castle.guard` | ✓ d=0 | Req supplies target ctx |
| 6 | concept | `castle.guard` | `castle.*` on **guard** | `village` | yes | `castle.guard` | ✓ d=0 | Req supplies target ctx; caller irrelevant |
| 7 | concept | `castle.guard` | `castle.morning.*` on **guard** | `castle` | yes | `castle.guard` | ✗ | `castle.guard` not admitted by `castle.morning.*` |
| 8 | concept | `village.guard` | `castle.*` on **guard** | any | yes | `village.guard` | ✗ | `village.guard` not admitted by `castle.*` |
| 9 | episode | `gatehouse` | `castle.*` on **throne_room** | any | no | — | ✗ | Identity gate: name mismatch |
| 10 | episode | `gatehouse` | `castle.*` on **gatehouse** | `castle` | no | `castle.gatehouse` | ✓ d=0 | Caller supplies target ctx |
| 11 | episode | `gatehouse` | `castle.*` on **gatehouse** | `village` | no | `village.gatehouse` | ✗ | Not admitted; unqualified so no chain building |
| 12 | episode | `gatehouse` | `castle.morning.*` on **gatehouse** | `castle` | no | `castle.gatehouse` | ✗ | Not admitted; unqualified so no chain building |
| 13 | episode | `castle.gatehouse` | `castle.*` on **gatehouse** | `castle` | yes | `castle.gatehouse` | ✓ d=0 | Req supplies target ctx; no build needed |
| 14 | episode | `castle.gatehouse` | `castle.*` on **gatehouse** | `village` | yes | `castle.gatehouse` | ✓ d=0 + build | Req supplies target ctx; build `castle` |
| 15 | episode | `castle.gatehouse` | `castle.morning.*` on **gatehouse** | `castle` | yes | `castle.gatehouse` | ✗ | `castle.gatehouse` not admitted by `castle.morning.*` |
| 16 | episode | `village.gatehouse` | `castle.*` on **gatehouse** | any | yes | `village.gatehouse` | ✗ | `village.gatehouse` not admitted by `castle.*` |
| 17 | episode | `castle.morning.gatehouse` | `castle.*` on **gatehouse** | any | yes | `castle.morning.gatehouse` | ✓ d=1 + build | Admitted (`castle.*` permissive); build `morning` |

## Implementation: Selector Integration

`Requirement` extends `Selector` in v38. Scope matching integrates as
additional dimensions on the offer, not new types:

```python
class ProvisionOffer(Record):
    # existing
    policy: ProvisionPolicy
    callback: Callable
    priority: int
    distance_from_caller: int
    specificity: int
    candidate: Any

    # new
    scope_distance: int = 0
    build_plan: list[str] | None = None   # segment labels to create, in order
```

The offer sort key incorporates scope distance:

```python
def offer_sort_key(offer):
    return (
        policy_tier(offer.policy),
        offer.scope_distance,           # prefer closer scope matches
        offer.distance_from_caller,     # then closer graph proximity
        -offer.specificity,
        offer.priority,
        offer.seq,
    )
```

`TemplateProvisioner` computes admission + distance during offer
generation. Offers that fail admission are not emitted. Offers for
unqualified episode requirements at distance > 0 are not emitted.
Qualified episode offers populate `build_plan` via prefix alignment.

## Implementation: Build Plan Execution

For MVP, the build plan is a list of segment labels representing
containers to create, outermost first. The offer callback executes
them serially:

```python
def make_chain_callback(build_plan, leaf_template, root):
    def callback(*_, _ctx=None, **__):
        parent = root
        for segment in build_plan:
            existing = parent.find_member(segment)
            if existing is not None:
                parent = existing
                continue
            tmpl = find_structural_template(segment, parent, _ctx)
            node = tmpl.materialize(uid=_next_provision_uid(_ctx=_ctx))
            _ctx.graph.add(node)
            parent.add_member(node)
            parent = node
        # Create the leaf
        leaf = leaf_template.materialize(uid=_next_provision_uid(_ctx=_ctx))
        _ctx.graph.add(leaf)
        parent.add_member(leaf)
        return leaf
    return callback
```

**Deferred improvement:** Rather than building the full chain in the
offer callback, create only the target node and let the traversal
entry-chain machinery (prereq redirect / `enter()` descent) provision
each container on the fly as the cursor descends. This leverages the
existing LCA → target traversal walk and means each container is
provisioned with its own full pipeline pass (requirements, namespace,
journal, etc.). The serial callback is correct for MVP; the
traversal-driven approach is the eventual design target.

### Materialization Tiers

Intermediate containers (e.g. `castle`, `morning`) need structure only —
member slots and entry point convention. Bare `materialize()` is
sufficient. The leaf node (e.g. `gatehouse`) needs outbound edges wired
because they define the next frontier that will be planned when the
player arrives. The leaf must be routed through a story-aware
instantiator (`story_materialize` or equivalent) that wires actions,
destination edges, and role/setting dependencies.

Whether those outbound edges eventually lead somewhere coherent is not
this system's concern. That's content validation (soft-lock detection,
reachability analysis) — a compiler or authoring-time lint problem, not
a runtime provisioning problem. Provisioning guarantees one horizon
ahead: when the player can see a choice, the target is structurally
reachable.

### Executor Add/Bind Sequence

The offer callback is pure — it returns a detached node without
mutating the graph. The executor handles side effects in a fixed
linear sequence:

1. `node = callback()` — create detached node
2. `graph.add(node)` — insert into graph
3. `dependency.set_provider(node)` — bind to the requesting edge

No staging, no rollback, no transactional semantics. If `set_provider`
fails after a successful `graph.add`, the offer should not have been
selected — `provider_rejected` is a bug/failure sentinel, not a
recovery path.

### Container Entry Discovery

Freshly provisioned containers may not have `source_id` set. The runtime
instantiator should set `source_id` explicitly when the entry node is
known. For cases where it isn't, `TraversableNode.enter()` falls back to
convention-based discovery:

1. Member with tag `is_entry`
2. Member with identifier `start`
3. First member by registration order

## Implementation: Preview (Non-Mutating Viability Check)

Planning needs to answer "is this choice viable?" without modifying the
graph. The resolver exposes a preview method that runs admission +
build-plan derivation but returns a result object instead of executing:

```python
@dataclass
class ViabilityResult:
    viable: bool
    chain: list[str]             # labels to build (empty = nothing needed)
    scope_distance: int
    blockers: list[Blocker]      # why not viable, if not

@dataclass
class Blocker:
    reason: str    # no_template, scope_rejected, chain_unresolvable, name_mismatch
    context: dict  # segment, scope, target_ctx, etc.
```

The preview recursion carries a `max_depth` (default 8) and a visited
set to guard against scope cycles.

## Concept Provenance (MVP)

Provisioned instances carry a `templ_hash` field stamped at
materialization — the content hash of the source template:

```python
class Entity:
    # existing fields...
    templ_hash: str | None = None
```

For MVP, cross-context concept reuse relies on FindProvisioner's
existing spatial proximity ranking (entity group distance from caller).
This handles the common case: a guard created while in the castle is
found by the castle-scoped FindProvisioner when the player returns.

When disambiguation between multiple candidates is needed (e.g., two
guards at similar distances, one castle-origin and one village-origin),
the `templ_hash` allows runtime lookup of the source template's scope
and label from the current registry. This is an offer-sorting
refinement layered onto the existing FindProvisioner, not a structural
change. Deferred until the need arises.

## Scope Syntax (v1)

Path scope: component-wise prefix matching with trailing wildcard.

- `*` — valid anywhere (universal)
- `castle.*` — valid anywhere under castle (any depth)
- `scene{2,10}.*` — valid under scene2 or scene10 (brace expansion)
- `castle.morning.*` — valid anywhere under castle.morning

In v1, `*` always means "any depth below the prefix." There is no
single-level-only wildcard. Brace expansion is applied before matching
to produce multiple candidate prefixes.

Selector scope (deferred to v2): `has_location=bar`, `@bar`. Not
needed for MVP structural provisioning. When added, the parser
distinguishes by syntax: contains `=` or starts with `@` → selector;
otherwise → path.

## Affordance Integration (Deferred, Design Note)

Affordances are standing offers (persistent available actions, role
bindings, namespace entries) that are conditionally active based on
game state. They are **not** a separate resolution system. They
integrate into the existing resolver as an early-running provisioner
that yields offers at cost ≤ 0:

- An `AffordanceProvisioner` runs before Find/Template provisioners.
- Active affordances yield EXISTING offers at effective cost -1 (or
  similar below-floor value).
- The resolver's normal sort-and-select picks them up first.
- If the affordance satisfies the dependency as-is, no other offers
  are evaluated.
- If the dependency requires a refinement (e.g. UPDATE to change an
  outfit), the affordance provides the EXISTING half and the
  `UpdateCloneProvisioner` synthesizes the composite — still cheaper
  than a fresh CREATE.
- If the affordance doesn't satisfy the dependency (wrong identity,
  scope forces a specific match), normal resolution proceeds.

This means affordances and dependencies share the same resolver
pipeline, the same scope matching, and the same offer ranking. The
only special behavior is priority: affordances run first and win by
default.

Script-level shorthand for declaring affordances (e.g. inferring
type and scope from template section placement) is a codec/compiler
concern, not a provisioning concern.

## What This Design Does NOT Cover

- **Link policy** (bind / clone / reference) — deferred.
- **Placement policy** (here / at_target / global) — for MVP, concepts
  always bind locally and episodes always build at the target path.
  A configurable placement field is warranted when a second behavior
  is needed for either kind.
- **Lifetime / GC** of provisioned nodes — deferred.
- **Content-string reference extraction** (`{bar.name}` → requirements) — deferred.
- **Affinity-based disambiguation** via template provenance — deferred;
  `templ_hash` field is present for when it's needed.
- **Selector-based scope predicates** (`has_location=bar`) — v2 syntax.
- **Full subtree provisioning** — deferred; entry-path only for MVP.
- **Affordance activation system** — deferred; the provisioner
  integration point is documented above, but the activation logic
  (condition evaluation, role indirection, standing offer lifecycle)
  is a separate design.
