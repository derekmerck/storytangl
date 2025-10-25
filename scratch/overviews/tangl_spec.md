### 1 ·  Guiding design goals  (“what must never break”)
| # | Goal | Consequence |
|---|------|-------------|
| **G-1** | *Deterministic replay* - any run = **snapshot + patch-log** | Time-travel, diff-based saves, authoritative server |
| **G-2** | *Pure core, pluggable edges* | New media, AI pipelines, or rules drop in as behaviours/templates |
| **G-3** | *Language-portable spec* | Re-implement once per language; only data contracts matter |
| **G-4** | *Event-sourced observability* | Every shape/state change, fragment, waiver, overlay = a Patch |
| **G-5** | *No hidden globals* | All look-ups go through the Layer stack; easy to reason & test |

---

### 2 ·  Canonical vocabulary (platform-agnostic)

| Name | Formal sketch | Metaphor |
|------|---------------|----------|
| **Node** | `vertex ∈ G` | package / AST node |
| **Edge** | `(src,dst, predicate, effect*)` | dependency constraint |
| **Shape** | `G = (N,E)` | topology/CFG |
| **State** | `σ : Key→Val` persistent map | lock-file |
| **Patch** | `(tick,target,op,before,after)` | git diff hunk |
| **Scope Layer** | `⟨locals,behaviours,templates⟩` | stack frame |
| **Source / Sink** | dominator / post-dominator of scope | function entry/return |
| **RIT** | recipe fragment placeholder | package.json line |
| **Fragment** | trace node *(channel, mime, meta, payload)* | log record |
| **Phase** | pure func `StoryIR→StoryIR′+Events` | compiler pass |

---

### 3 ·  Execution pipeline

`predicate → provision → effects → render → compose → post`

* Each Phase is a **registry** of behaviours; nearest Layer overrides win.  
* All mutations return **Patch** objects; engine only splices them into the log.

---

### 4 ·  Key algorithms & precedents

| Feature | Algorithm | Precedent |
|---------|-----------|-----------|
| **Forward traversal** | Cursor + Phase list | Smalltalk VM byte-code loop |
| **Reverse reachability** | Backward must-analysis over abstract state lattice | Live-variable analysis |
| **Waiver / prune** | Latent template expansion or edge disable | Package-manager SAT conflict resolution |
| **Layer push/pop** | Pop → LCA, Push → leaf | Call-stack unwinding |
| **Variant composer** | Priority select per `variant_id` | HTTP `Accept` negotiation |
| **RIT federation** | Broker queue + content-addressed store | CI build farm, Docker registry |
| **Snapshots** | zstd + msgpack of StoryIR | git pack-file |

---

### 5 ·  High-level interfaces (language neutral)

```text
POST  /stories          → new story id
GET   /stories/{id}/choices         → [{edge_id, caption}]
POST  /stories/{id}/action          {edge_id}
GET   /stories/{id}/subscribe       (SSE / WS stream of patches)
GET   /fragments/{frag_id}          → bytes | xml | markdown | recipe
POST  /sessions/{id}/capabilities   {"accept":["svg","audio"],"gpu":false}
GET   /stories/{id}/softlocks
```

---

### 6 ·  Python reference implementation – **v35 roadmap**

| Stage | Tasks | Cannibalise from v34 | Libs / tools |
|-------|-------|----------------------|--------------|
| **S-0  Skeleton** | • `StoryIR` dataclasses (immutables / pyrsistent)<br>• Patch class & log writer | existing `Patch` + `Graph` + `Node` trees | `pyrsistent`, `msgspec`, `zstandard` |
| **S-1  Phase runner** | • Generic `Phase` enum<br>• `BehaviourRegistry` (priority tiers, receipts) | **reuse** v34 `HandlerRegistry`, `ServiceCallReceipt` | |
| **S-2  Scope manager** | • SESE detector pass<br>• `LayerStack` push/pop<br>• `LayerOverlayPatch` | Scope stubs can be dropped | `networkx` for dominator calc |
| **S-3  Provision** | • Role recruitment, affordance, RIT emission | v34 `Provisioner`, `MediaProvisioner` | |
| **S-4  Reverse pass** | • Frontier lattice + soft-lock detector<br>• Waiver template handler | new code | `python-z3` optional for predicate SAT |
| **S-5  Trace & composer** | • Fragment model (+variant/prio)<br>• Composer pass | **extend** v34 `ContentFragment` hierarchy | `Jinja2` |
| **S-6  Media mesh** | • RIT class revamp<br>• Broker (Redis Streams) adapter<br>• Worker harness | reuse `MediaResourceRegistry`, `Forges` | `redis-py`, `aiohttp`, `ipfshttpclient` |
| **S-7  API layer** | • Reflective `ServiceManager` routes<br>• SSE/WebSocket patch stream | reuse updated controllers | `FastAPI`, `uvicorn`, `sse-starlette` |
| **S-8  Tests & CI** | • Golden-log replay tests<br>• Property-based fuzz (hypothesis)<br>• Performance budget (ticks/sec) | reuse v34 unit fixtures | `pytest`, `hypothesis`, `pytest-benchmark` |

---

### 7 ·  Testing strategy

1. **Golden scenario**: parse a small Hero’s-Journey script → run predetermined choices → assert final hash of log.  
2. **Soft-lock suite**: mutate initial choices randomly, ensure waiver or prune always fires, never hangs.  
3. **Patch idempotence**: snapshot + log → replay → x==y structural hash.  
4. **Concurrency**: multi-client WebSocket flood → state hashes converge.  
5. **Cross-lang parity** (later): run same script in Python & (say) Rust impl; diff logs byte-wise.

---

### 8 ·  What moves **unchanged** from v34

* `Entity/Registry` base pattern (`matches`, `find_one/all`)  
* `HandlerRegistry` dispatch & timing receipts  
* Media **Forges**, `MediaResourceRegistry`, `MediaSpec`  
* Fragment subclasses (`KvFragment`, etc.) – just extend meta  
* Scene/Block/Role/Setting helpers – now sit comfortably inside scopes  
* Controller reflection (`ApiEndpoint`, `ServiceManager`)

---

### 9 ·  Language–portability checklist

* **Data contracts** = JSON schema for StoryIR, Patch, Fragment.  
* **Phase API** = pure, deterministic functions, no global time, no threads.  
* **Persistent maps** → backed by whatever idiomatic immutable map exists (`pyrsistent`, `immutable.js`, `im` in Rust).  
* **Broker protocol** = plain JSON messages; any language can enqueue/dequeue.

---

## Final one-liner

> **v35** will be a **Python-idiomatic** yet **spec-driven** engine that keeps every
> mutation in a replayable patch log, manages nested scopes like function frames,
> prevents dead-ends with a reverse data-flow pass, and treats all rich media as
> lazily-realised inventory tags—leaving UI choice, heavy generation, and
> federation to outer layers while guaranteeing deterministic, portable core logic.