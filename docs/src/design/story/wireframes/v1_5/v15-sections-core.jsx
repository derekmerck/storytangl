// v15-sections-core.jsx — long-form sections for v1.5 core vocabulary.
// Each top-level export is a React component used in v15-app.jsx.
//
// Reads from window.V15_FIXTURES (assembled from V15_FIXTURES_CORE +
// V15_FIXTURES_GENRES in v15-app.jsx). The genre-extension sections
// (credentials / training / elefant_hunt) live in v15-sections-genres.jsx.

const { useState: useSecState, useMemo: useSecMemo } = React;

// ===========================================================================
// §5 (CLI Floor) — CLI rendering of an envelope, for the parity panes
// ---------------------------------------------------------------------------
// This is the **floor** every richer port must clear: numbered choices,
// readable kv rows, no drag, no animation, no info-pill bar. Each demo
// pairs its rich web rendering with the CLI text the same envelope would
// produce through `cli_reference_port.py`. See uploads/.../cli_reference_port.expected.txt
// for the canonical Smut-Koi and sandbox-ward reference outputs.
// ===========================================================================

function CliPane({ lines, label, width = 44 }) {
  const arr = Array.isArray(lines) ? lines : String(lines || "").split("\n");
  return (
    <div className="cli-pane">
      <div className="cli-pane-hd">
        <span>{label || "cli_reference_port.py"}</span>
        <span className="cli-pane-cols">~{width} cols</span>
      </div>
      <pre className="cli-pane-body">{arr.join("\n")}</pre>
    </div>
  );
}

function cliWrap(s, width = 44) {
  const words = String(s).split(/\s+/);
  const out = []; let line = "";
  for (const w of words) {
    if ((line + " " + w).trim().length > width) { out.push(line); line = w; }
    else line = line ? line + " " + w : w;
  }
  if (line) out.push(line);
  return out.join("\n");
}

function cliRenderCrossroads(fx) {
  const env = fx.envelope;
  const idx = indexEnvelope(env);
  const items = (findScene(env)?.member_ids || []).map(id => idx.byUid[id]).filter(Boolean);
  const out = [];
  for (const f of items) {
    if (f.fragment_type === "content") {
      out.push(cliWrap(String(f.content).replace(/\*\*/g, "").replace(/\*/g, ""), 44));
      out.push("");
    } else if (f.fragment_type === "media") {
      const role = f.media_role || "inline";
      if (f.content_format === "rit") out.push(`[${role}: pending ${f.content}]`);
      else out.push(`[${role}: ${(f.content || "").split("/").pop()}]`);
    } else if (f.fragment_type === "group" && f.group_type === "dialog") {
      for (const id of f.member_ids) {
        const m = idx.byUid[id];
        if (m && m.fragment_type === "attributed") {
          out.push(cliWrap(`${m.who} [${m.how}]> ${m.content}`, 44));
        } else if (m && m.fragment_type === "media" && m.content_format === "rit") {
          out.push(`  [dialog_im: pending ${m.content}]`);
        }
      }
      out.push("");
    } else if (f.fragment_type === "kv") {
      out.push("[status] " + f.content.map(r => `${r.key}=${r.value}${r.unit?r.unit:""}`).join(" "));
      out.push("");
    }
  }
  out.push("-- choices --");
  let i = 1;
  for (const c of items.filter(x => x.fragment_type === "choice")) {
    if (c.edge_id === "interpret_command") continue;
    const cps = (c.ui_hints?.cost_previews || []).filter(p => p.delta !== 0);
    const costStr = cps.length
      ? "  (" + cps.map(p => `${p.delta < 0 ? "−" : "+"}${Math.abs(p.delta)} ${p.unit}`).join(" · ") + ")"
      : "";
    const accepts = c.accepts?.kind && c.accepts.kind !== "pick" ? `  <${c.accepts.kind}>` : "";
    if (c.available) {
      out.push(`${i}) ${c.text}${accepts}${costStr}`);
    } else {
      out.push(`${i}) ${c.text}  (locked)`);
      out.push(`     ${c.unavailable_reason}`);
    }
    i++;
  }
  out.push("> ");
  return out.join("\n");
}

function cliRenderGarage(fx) {
  const env = fx.envelope;
  const idx = indexEnvelope(env);
  const out = [];
  const prose = idx.byUid["c-prose"];
  if (prose) {
    out.push(cliWrap(String(prose.content).replace(/\*\*/g, "").replace(/\*/g, ""), 44));
    out.push("");
  }
  out.push("[Beast — your interceptor]");
  for (const zid of ["z-front", "z-turret", "z-back"]) {
    const z = idx.byUid[zid];
    if (!z) continue;
    const cap = z.constraints?.capacity?.find(c => c.kind === "weight");
    const members = z.member_ids.map(id => idx.byUid[id]).filter(Boolean);
    const occ = members.reduce((s, p) => s + (p.properties?.[cap?.sum_property] || 0), 0);
    const names = members.length ? members.map(m => m.hints?.label_text).join(", ") : "empty";
    const label = (z.hints?.label_text || "").padEnd(12);
    const detail = cap ? `(cap ${cap.max}, ${occ}/${cap.max} ${cap.unit})` : "";
    out.push(`  ${label} ${names.padEnd(18)} ${detail}`);
  }
  out.push("");
  out.push("[parts on hand]");
  const loose = idx.byUid["z-loose"];
  for (const id of loose.member_ids) {
    const p = idx.byUid[id];
    out.push(`  - ${p.hints?.label_text} (${p.properties?.weight} stone)`);
  }
  out.push("");
  out.push("[Murph's wares]");
  const cat = idx.byUid["z-catalog"];
  for (const id of cat.member_ids) {
    const o = idx.byUid[id];
    const cost = o.cost?.[0];
    const meta = [];
    if (o.properties?.weight != null) meta.push(`${o.properties.weight}st`);
    if (o.properties?.ammo != null)   meta.push(`${o.properties.ammo}a`);
    const oos = !o.available ? "  [out]" : "";
    const costStr = cost ? `${Math.abs(cost.delta)} ${cost.unit}` : "—";
    out.push(`  - ${(o.properties?.name || "—").padEnd(22)} ${costStr.padEnd(8)}(${meta.join(", ")})${oos}`);
  }
  out.push("");
  out.push("-- ledger --");
  const proj = fx.projected_state.sections;
  for (const s of proj) {
    for (const r of (s.value.items || [])) {
      const v = r.max != null ? `${r.value}/${r.max} ${r.unit||""}` : `${r.value} ${r.unit||""}`;
      out.push(`  ${(r.key || "").padEnd(10)} ${v.trim()}`);
    }
  }
  out.push("");
  out.push("-- actions --");
  let i = 1;
  for (const c of env.fragments.filter(f => f.fragment_type === "choice" && f.edge_id !== "interpret_command")) {
    const k = c.accepts?.kind;
    const suffix =
      k === "place"  ? " <piece> <slot>" :
      k === "pieces" ? ` <pick ${c.accepts.min}-${c.accepts.max}>` : "";
    if (c.available) out.push(`  ${i}) ${c.text}${suffix}`);
    else             out.push(`  ${i}) ${c.text}  (locked) ${c.unavailable_reason || ""}`);
    i++;
  }
  out.push("> ");
  return out.join("\n");
}

function cliRenderRoll(fx, phase) {
  const env = phase === "pre" ? fx.pre.envelope
            : phase === "crit" ? fx.post_crit.envelope
            : fx.post_fail.envelope;
  const idx = indexEnvelope(env);
  const items = (findScene(env)?.member_ids || []).map(id => idx.byUid[id]).filter(Boolean);
  const out = [];
  for (const f of items) {
    if (f.fragment_type === "content") {
      out.push(cliWrap(String(f.content).replace(/\*\*/g, "").replace(/\*/g, ""), 44));
      out.push("");
    } else if (f.fragment_type === "roll") {
      const c = f.inputs;
      out.push(`  ${f.label} (${c.dice} vs ${c.target}${c.modifier?` mod ${c.modifier>0?"+":""}${c.modifier}`:""}).`);
      out.push(`  rolled: ${(c.rolled || []).join(" + ")} = ${c.total}.`);
      out.push(`  outcome: ${f.outcome.replace("_", " ")}.`);
      if (f.narrative) out.push("  " + cliWrap(f.narrative, 42).split("\n").join("\n  "));
      out.push("");
    }
  }
  const choices = items.filter(f => f.fragment_type === "choice" && f.edge_id !== "interpret_command");
  if (choices.length) {
    out.push("-- actions --");
    let i = 1;
    for (const c of choices) {
      const sc = c.ui_hints?.stat_check;
      const scStr = sc ? `  [${sc.label} ${sc.dice} vs ${sc.target}]` : "";
      out.push(`  ${i}) ${c.text}${scStr}`);
      i++;
    }
    out.push("> ");
  }
  return out.join("\n");
}

function cliRenderCommand() {
  return [
    "> take key",
    "  ambiguous: Which key — brass or iron?",
    "    candidates: e-take#brass_key,",
    "                e-take#iron_key",
    "",
    "> climb to attic",
    "  blocked: The hatch is bolted from above.",
    "    reason: Locked — no obvious key.",
    "    hint:   Find another way up.",
    "",
    "> fly away",
    "  unknown verb: Nothing here takes flight.",
    "",
    "> pay 200 silver",
    "  validation failed: You only have 63 silver.",
    "",
    "(step unchanged · choices intact)",
    "> ",
  ].join("\n");
}

function cliRenderSandbox(fx) {
  // The §5.3 floor: no info pill bar; info channels are reachable through
  // slash commands derived from info_affordances[].shortcuts, plus a ? menu.
  const env = fx.envelope;
  const idx = indexEnvelope(env);
  const prose = idx.byUid["c-prose"];
  const out = [];
  if (prose) {
    out.push(cliWrap(String(prose.content).replace(/\*\*/g, "").replace(/\*/g, ""), 44));
    out.push("");
  }
  out.push("[here] bedroom");
  out.push("  - brass lamp (on the desk)");
  out.push("  - small mailbox (closed)");
  out.push("  - framed painting");
  out.push("  - guard (at his post in the hall)");
  out.push("");
  out.push("[exits] north→hall  down→cellar");
  out.push("");
  out.push("-- choices --");
  const choices = env.fragments.filter(f => f.fragment_type === "choice" && f.edge_id !== "interpret_command");
  let i = 1;
  for (const c of choices) {
    const cps = (c.ui_hints?.cost_previews || []).filter(p => p.delta !== 0);
    const cost = cps.length ? "  (" + cps.map(p => `${p.delta<0?"−":"+"}${Math.abs(p.delta)} ${p.unit}`).join(" · ") + ")" : "";
    out.push(`  ${i}) ${c.text}${cost}`);
    i++;
  }
  out.push("");
  // §5.3 floor: info channels reachable through slash commands
  const infoCommands = (env.metadata?.info_affordances || [])
    .map((affordance) => {
      const shortcut = affordance.shortcuts?.[0];
      if (!shortcut) return null;
      const label = affordance.label || affordance.kind.replace(/_/g, " ");
      return `/${shortcut} ${label}`;
    })
    .filter(Boolean);
  out.push(`(info: ${infoCommands.join(" · ") || "?"})`);
  out.push("> ");
  return out.join("\n");
}

// ===========================================================================
// Tier legend + parity rules (the four-legged stool)
// ===========================================================================

function TierLegend() {
  return (
    <div className="tier-legend" aria-label="tier legend">
      <span><span className="tier tier-s">S</span> stable in engine v3.8+</span>
      <span><span className="tier tier-p1">P1</span> proposed · next epoch · typed</span>
      <span><span className="tier tier-p2">P2</span> proposed · larger</span>
      <span><span className="tier tier-p3">P3</span> genre extensions (e.g. carwars)</span>
    </div>
  );
}

function ParityStool() {
  const legs = [
    { glyph: "CLI",  title: "Capability parity",  body: <>The CLI port is the floor. A widget that requires more than a CLI can do isn't vocabulary — it's a renderer flourish. <b>cli_reference_port.py</b> is the gating artifact.</> },
    { glyph: "see",  title: "Decision legibility", body: <>If an open choice's <code>accepts</code>, <code>blockers[]</code>, or <code>unavailable_reason</code> references a UID, that fragment <b>MUST</b> render so the player can evaluate the choice.</> },
    { glyph: "skip", title: "Time parity",        body: <>Visual ritual is skippable to canonical-instant in one user action. Audio / video must always be advanceable. Pacing belongs in fragment boundaries, not in elapsed time.</> },
    { glyph: "tap",  title: "Input parity",       body: <>Every richer modality (drag, gesture, hotkey) <b>MUST</b> have a click-pick / typed-text equivalent. CLI defines the input floor; richer ports add on top.</> },
  ];
  return (
    <div className="stool">
      {legs.map((l, i) => (
        <div key={i} className="leg">
          <h5><span className="glyph">{l.glyph}</span> {l.title}</h5>
          <p>{l.body}</p>
        </div>
      ))}
    </div>
  );
}

// ===========================================================================
// What changed v1.3 → v1.5
// ===========================================================================

function V15Changes() {
  return (
    <div className="vocab-changes">
      <div className="ch">
        <span className="to">+ §0.8 Journal-as-narrative</span>
        <div className="muted">
          New principles section. v1.5-conforming envelope streams produce
          legible narrative transcripts <i>as a consequence of traversal</i> —
          no separate narration layer. Tested by transcript fixtures; not
          gated by conformance. Proof-of-concept: <code>elefant_hunt</code>.
        </div>
      </div>
      <div className="ch">
        <span className="to">+ §0.9 Genre extensions index</span>
        <div className="muted">
          Short table pointing to <code>bundles/&lt;name&gt;/EXTENSIONS.md</code>.
          Current set: <b>carwars · credentials · training · elefant_hunt</b>.
          One demo per bundle below.
        </div>
      </div>
      <div className="ch">
        <span className="to">+ §1.5 Per-cursor projection of shared state</span>
        <div className="muted">
          Codifies the recipe credentials / training / elefant_hunt all hit:
          one canonical backend object, per-cursor projected envelopes, control
          fragments propagate updates. <code>visibility=[participant_ids]</code>
          accepts a list (teams / asymmetric coop).
        </div>
      </div>
      <div className="ch">
        <span className="to">~ Typed Accepts / UIHints</span>
        <div className="muted">
          Implementation status updated: the engine now emits typed
          <code>Accepts</code> and <code>UIHints</code>. <code>Blocker</code>,
          <code>InterpretationFragment</code>, and full info-channel typing
          remain pending — tracked in <code>WIDGET_CONTRACT_RECONCILIATION.md</code>.
        </div>
      </div>
      <div className="ch">
        <span className="to">~ <code>place</code> payload carries <code>source_zone_ref</code></span>
        <div className="muted">
          When the client selected the placed piece from a visible source zone,
          the commit payload now includes <code>source_zone_ref</code> alongside
          <code>piece_id</code> and <code>target_zone_ref</code> / <code>edge_ref</code>.
        </div>
      </div>
      <div className="ch">
        <span className="to">~ Conformance fixtures aligned</span>
        <div className="muted">
          List in §10.4 of the spec updated to the current repo state:
          <code>compose_payload.json</code> + existing proposal fixtures.
        </div>
      </div>
      <div className="ch" style={{gridColumn:"1 / -1", borderColor:"var(--rule-strong)"}}>
        <span className="to" style={{fontWeight:700}}>Carry-overs from v1.3 (still load-bearing)</span>
        <div className="muted">
          <b>tokens → pieces</b> rename · <b>kv unified</b> across scene / rail ·
          <b>§1.5 + §1.6 Tier P1</b> · <b>three-layer architecture</b> (L1 vocab /
          L2 API / L3 engine) · <code>InfoAffordance.query</code> opaque descriptors ·
          <code>owner</code> · <code>position</code> · <code>edge_ref</code> ·
          audience visibility (proposal fixtures, not gating).
        </div>
      </div>
    </div>
  );
}

// ===========================================================================
// §1 — Fragment / widget matrix (compact)
// ===========================================================================

function FragmentMatrix() {
  const rows = [
    { group: "RuntimeEnvelope.fragments — Tier S" },
    { frag: "content",            widget: "Prose block",       scroll: "inline paragraph",   dossier: "stage prose",       stage: "caption + log row",
      cli: "wrapped stdout, blank line above/below" },
    { frag: "attributed",         widget: "Dialog line",       scroll: "indented + avatar",  dossier: "bracketed",         stage: "active caption",
      cli: "who [how]> said …" },
    { frag: "media · cover_im",   widget: "Banner frame",      scroll: "top banner",         dossier: "persistent header", stage: "fullscreen bg",
      cli: "[cover_im: url]" },
    { frag: "media · narrative_im", widget: "Inline figure",   scroll: "inline + wrap",      dossier: "stage column",      stage: "set dressing",
      cli: "[narrative_im: url]" },
    { frag: "media · avatar/dialog_im", widget: "Avatar / inset", scroll: "attached to line", dossier: "attached to line", stage: "sprite + inset",
      cli: "  [dialog_im: url]" },
    { frag: "media · pending RIT",widget: "Striped placeholder", scroll: "swap via update",  dossier: "swap via update",  stage: "swap via update",
      cli: "[<role>: pending <rit-id>]" },
    { frag: "group · scene",      widget: "(implicit turn)",   scroll: "(boundary)",         dossier: "(boundary)",        stage: "scene change",
      cli: "(blank line)" },
    { frag: "group · dialog",     widget: "Indented rule",     scroll: "border-left rule",   dossier: "bracketed block",   stage: "consecutive captions",
      cli: "rule of lines" },
    { frag: "group · overlay",    widget: "Modal sheet",       scroll: "sticky sheet",       dossier: "right-rail takeover", stage: "dim + center",
      cli: "── overlay ── … ── /overlay ──" },
    { frag: "kv",                 widget: "KV strip",          scroll: "inline strip",       dossier: "merge into rail",   stage: "HUD",
      cli: "[status] k=v k=v …" },
    { frag: "choice",             widget: "Button / input",    scroll: "bottom list",        dossier: "bottom of stage",   stage: "tray below log",
      cli: "1) text … > " },
    { frag: "control · update/delete", widget: "(silent)",     scroll: "replace target",     dossier: "replace target",    stage: "replace target",
      cli: "re-render target in place" },
    { frag: "user_event",         widget: "Toast / stash",     scroll: "toast",              dossier: "toast",             stage: "HUD blip",
      cli: "* <event_type>: <content>" },

    { group: "RuntimeEnvelope.fragments — Tier P1 / P2" },
    { frag: "interpretation",     widget: "Transcript line",   scroll: "inline w/ accent",   dossier: "inline w/ accent",  stage: "log row",
      cli: "> echo \\n  result: message", tier: "P1" },
    { frag: "piece",              widget: "Piece chip",        scroll: "(in zone)",          dossier: "(in zone)",         stage: "(in zone)",
      cli: "  - name (kind, props)", tier: "P2" },
    { frag: "group · zone (slot/hand/field/catalog/pile)", widget: "Zone tile + capacity bar", scroll: "stacked tiles", dossier: "tiles in stage", stage: "HUD strip",
      cli: "[label: contents (cap, used/max unit)]", tier: "P2" },
    { frag: "roll",               widget: "Dice ritual + outcome", scroll: "inline panel", dossier: "inline panel", stage: "log row + skip",
      cli: "  rolled: a+b=T → outcome", tier: "P2" },

    { group: "ProjectedState.sections — Tier S" },
    { frag: "scalar",             widget: "Big number / badge", scroll: "strip cell",        dossier: "rail tile",         stage: "HUD value",
      cli: "[<title>] <value>" },
    { frag: "kv_list (+ KvRow bar/fraction/delta)",  widget: "Key-value table; bars; deltas", scroll: "wrapped strip", dossier: "rail rows", stage: "HUD stack",
      cli: "  key: value [/max] [unit]" },
    { frag: "item_list",          widget: "Item roster",       scroll: "drawer",             dossier: "rail list",         stage: "inventory overlay",
      cli: "  - label (detail) [tags]" },
    { frag: "table",              widget: "Data table",        scroll: "drawer",             dossier: "rail mini-table",   stage: "overlay sheet",
      cli: "col1 | col2 | col3 (aligned)" },
    { frag: "badges",             widget: "Tag strip",         scroll: "inline chips",       dossier: "rail chips",        stage: "HUD chips",
      cli: "[tag1][tag2]" },

    { group: "Sandbox conventions (Tier P1 target; rendered through generic projected state)" },
    { frag: "kind = world_time",  widget: "Watch / period / day", scroll: "top strip",       dossier: "rail · clock",      stage: "HUD top-right",
      cli: "[Time] Day 3 · afternoon" },
    { frag: "kind = location",    widget: "Here · fixtures · exits", scroll: "inline panel", dossier: "rail panel",        stage: "HUD",
      cli: "[here] room — fixtures · exits" },
    { frag: "kind = agenda",      widget: "Disclosed schedule", scroll: "inline panel",      dossier: "rail panel",        stage: "HUD",
      cli: "[schedule] when · what · src" },
    { frag: "info_affordances",   widget: "Info-bar pills (m·i·t·?)", scroll: "rail of pills", dossier: "rail header",     stage: "HUD",
      cli: "(info: /t time · /h look · ?)" },
  ];
  return (
    <div className="matrix-wrap">
      <table className="matrix">
        <thead>
          <tr>
            <th style={{width:"18%"}}>Fragment / value_type</th>
            <th style={{width:"16%"}}>Widget</th>
            <th>Scroll</th>
            <th>Dossier</th>
            <th>Stage + Log</th>
            <th style={{
              width:"22%",
              background:"#15140f",
              color:"#e8dfc6",
              fontFamily:"var(--mono)",
            }}>CLI floor</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => r.group ? (
            <tr key={i} className="section-row"><td colSpan={6}>{r.group}</td></tr>
          ) : (
            <tr key={i}>
              <td className="frag">
                {r.frag}
                {r.tier && <span className={"tier tier-" + r.tier.toLowerCase()} style={{marginLeft:6}}>{r.tier}</span>}
              </td>
              <td className="widget">{r.widget}</td>
              <td>{r.scroll}</td>
              <td>{r.dossier}</td>
              <td>{r.stage}</td>
              <td style={{
                fontFamily:"var(--mono)",
                fontSize:"10.5px",
                background:"#15140f",
                color:"#e8dfc6",
                whiteSpace:"nowrap",
                overflow:"hidden",
                textOverflow:"ellipsis",
                maxWidth:0,
              }}>{r.cli}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ===========================================================================
// §3 — Choice accepts.kind quick reference
// ===========================================================================

function AcceptsKindCheatsheet() {
  const rows = [
    { kind: "pick",     payload: "{}",                                tier: "S",  ex: "Pay the forty silver." },
    { kind: "text",     payload: "{ text }",                          tier: "P1", ex: "Name your sword." },
    { kind: "quantity", payload: "{ quantity }",                      tier: "P1", ex: "Buy n rations." },
    { kind: "pieces",   payload: "{ piece_ids: [...] }",              tier: "P1", ex: "Pick which key to take. (was 'tokens' pre-v1.2.)" },
    { kind: "place",    payload: "{ piece_id, target_zone_ref \u2502 edge_ref }", tier: "P1", ex: "Mount weapon in a slot · lay track on a connection." },
    { kind: "compose",  payload: "{ parts: { role: subpayload } }",   tier: "P1", ex: "Give n coins to actor." },
    { kind: "raw_command", payload: "{ text }",                       tier: "P1", ex: "Reserved interpret_command edge." },
  ];
  return (
    <table className="parity-table">
      <thead><tr>
        <th>accepts.kind</th>
        <th>Wire payload (commit)</th>
        <th>Tier</th>
        <th>Use case</th>
      </tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td className="w">{r.kind}</td>
            <td><code>{r.payload}</code></td>
            <td><span className={"tier tier-" + r.tier.toLowerCase()}>{r.tier}</span></td>
            <td>{r.ex}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ===========================================================================
// §7 — Interactive surface demo (Garage: slots + catalog + drag)
// ===========================================================================

function GarageDemo() {
  const fx = window.V15_FIXTURES.garage;
  const env = fx.envelope;
  const proj = fx.projected_state;
  const idx = useSecMemo(() => indexEnvelope(env), [env]);
  const byUid = idx.byUid;

  // Drag state — driven by clicking a loose piece, then a slot.
  const [dragId, setDragId] = useSecState(null);
  const dragPiece = dragId ? idx.piece(dragId) : null;
  const slotIds = ["z-front", "z-turret", "z-back"];

  const looseZone   = byUid["z-loose"];
  const catalogZone = byUid["z-catalog"];
  const slots = slotIds.map(id => byUid[id]).filter(Boolean);

  // Catalog selection
  const [cartIds, setCartIds] = useSecState([]);
  function toggleCart(id) {
    setCartIds(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);
  }
  const wallet = proj.sections.find(s => s.section_id === "wallet")?.value.items[0]?.value;

  const choices = env.fragments.filter(f => f.fragment_type === "choice");

  return (
    <div className="panel-card">
      <h3>Tier P2 worked example — slots, catalog, place choice
        <span className="right">"the garage turn"</span>
      </h3>
      <div className="cli-grid">
        <div style={{display:"grid", gap:14, minWidth:0}}>
          <div className="demo-grid-2">
            <div style={{display:"grid", gap:10}}>
              {/* Vehicle silhouette: three slot zones */}
              <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>
                vehicle slots
              </div>
              <div style={{display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:8}}>
                {slots.map(s => (
                  <SlotZone key={s.uid} zone={s} env={env} byUid={byUid}
                    dragCandidate={dragPiece}
                    dragTargets={dragPiece ? slotIds : []}
                    onPieceClick={(p) => {/* unmount click — would emit e-unmount */}} />
                ))}
              </div>

              {/* Loose parts — click to pick up as drag candidate */}
              <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:6, display:"flex", alignItems:"center", gap:8}}>
                <span>parts on hand · <code>owner: "player_a"</code> · click one to "pick up", click a slot to place</span>
                <span className="tier tier-p2" style={{marginLeft:"auto", fontSize:8.5}}>owner: proposal fixture</span>
              </div>
              <div className="zone field">
                <div className="zone-hd">
                  <span>{looseZone.hints.label_text}</span>
                  <span className="role">field</span>
                </div>
                <div className="zone-body">
                  {looseZone.member_ids.map(id => {
                    const p = byUid[id];
                    if (!p) return null;
                    const sel = dragId === p.piece_id;
                    return (
                      <PieceChip key={p.uid} piece={p} env={env} selected={sel}
                        onClick={() => setDragId(sel ? null : p.piece_id)} />
                    );
                  })}
                </div>
              </div>
              {dragId && (
                <div className="margin-note" style={{marginTop:2}}>
                  picking up <b>{dragPiece?.hints?.label_text}</b>. Slot tiles preview projected weight. Wrong kind / over capacity show in red.
                </div>
              )}

              {/* Catalog */}
              <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:8}}>
                Murph's wares — catalog zone (offers, <code>realized=false</code>, no owner)
              </div>
              <CatalogGrid zone={catalogZone} env={env} byUid={byUid}
                selectedIds={cartIds} onToggle={toggleCart}
                walletValue={wallet} />
              <div style={{display:"flex", gap:10, alignItems:"center", fontFamily:"var(--mono)", fontSize:11}}>
                <span className="muted">cart:</span>
                <span><b>{cartIds.length}</b> selected</span>
                <span className="muted">·</span>
                <span>total: {cartIds.reduce((s, id) => s + (idx.piece(id)?.cost?.[0]?.delta || 0), 0)} cr</span>
                <button type="button" className="choice-v12" style={{padding:"4px 10px", marginLeft:"auto", display:"inline-flex"}} disabled={cartIds.length === 0}>
                  <span className="key">↵</span><span className="label">buy {cartIds.length || ""}</span>
                </button>
              </div>
            </div>

            {/* Right column — choices + ledger + payload */}
            <div style={{display:"grid", gap:10}}>
              <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>open choices</div>
              <ChoiceList choices={choices} env={env} onCommit={() => {}} />

              <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:6}}>projected · annotated kv_list</div>
              {proj.sections.map(s => <RailSection key={s.section_id} section={s} />)}

              <div className="callout" style={{fontSize:11, padding:"8px 10px"}}>
                <b>Drag is a presentation enhancement.</b> Every <code>place</code> choice with <code>ui_hints.drag</code> still works as a two-step click-pick. The CLI port ignores <code>drag</code>; the commit payload is identical.
              </div>

              <pre style={{fontFamily:"var(--mono)", fontSize:10.5, background:"var(--paper)", border:"1px solid var(--rule)", padding:"8px", margin:0, overflow:"auto", lineHeight:1.4}}>
{`POST /story/do
{
  "edge_id": "e-mount",
  "payload": {
    "piece_id": "${dragId || "<pick a loose part>"}",
    "target_zone_ref": "<click a slot>"
  }
}`}
              </pre>
            </div>
          </div>

          {/* Route-building sub-section — Patch E (edge_ref) */}
          <RouteBuildingDemo />
        </div>

        <CliPane lines={cliRenderGarage(fx)} label="garage · cli reference port" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Route-building (PlaceAccepts.edge_ref) — §6.1.1 / §7.2 sketch
// ---------------------------------------------------------------------------

function RouteBuildingDemo() {
  // A tiny self-contained fixture demonstrating that GraphLayout.edges have
  // uids and that PlaceAccepts can address them via edge_ref. This is the
  // load-bearing demonstration of the edge_ref **proposal fixture** (§7.2 in
  // the v1.5 spec — proposal fixture, not gating).
  const cities = [
    { uid: "pc-toledo",   name: "Toledo",   x: 1, y: 1 },
    { uid: "pc-chicago",  name: "Chicago",  x: 0, y: 0 },
    { uid: "pc-pittsburg",name: "Pittsburg",x: 2, y: 1 },
    { uid: "pc-stlouis",  name: "St Louis", x: 1, y: 2 },
  ];
  const edges = [
    { uid: "edge-toledo-chicago",   a: "pc-toledo",   b: "pc-chicago",   label: "3", claimed: false },
    { uid: "edge-toledo-pittsburg", a: "pc-toledo",   b: "pc-pittsburg", label: "2", claimed: true,  by: "player_a" },
    { uid: "edge-toledo-stlouis",   a: "pc-toledo",   b: "pc-stlouis",   label: "4", claimed: false },
  ];
  const [chosen, setChosen] = useSecState("edge-toledo-chicago");

  const W = 320, H = 140;
  const xs = cities.map(c => c.x), ys = cities.map(c => c.y);
  const sx = (W - 80) / (Math.max(...xs) - Math.min(...xs));
  const sy = (H - 60) / (Math.max(...ys) - Math.min(...ys));
  const pos = c => ({ x: 40 + (c.x - Math.min(...xs)) * sx, y: 30 + (c.y - Math.min(...ys)) * sy });
  const byCity = Object.fromEntries(cities.map(c => [c.uid, c]));

  return (
    <div style={{border:"1.25px solid var(--rule-strong)", padding:"10px 12px", background:"#fff", display:"grid", gap:8}}>
      <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", display:"flex", alignItems:"center", gap:8}}>
        <span>§6.1.1 / §7.2 · place on a connection — <code>PlaceAccepts.edge_ref</code></span>
        <span className="tier tier-p2" style={{marginLeft:"auto", fontSize:8.5}}>proposal fixture</span>
      </div>
      <div className="demo-grid-2" style={{alignItems:"start"}}>
        <div className="sandbox-map" style={{height: H, position:"relative"}}>
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            {edges.map(e => {
              const p1 = pos(byCity[e.a]), p2 = pos(byCity[e.b]);
              const isChosen = chosen === e.uid;
              return (
                <g key={e.uid}>
                  <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                    stroke={e.claimed ? "var(--bad)" : (isChosen ? "var(--accent)" : "var(--ink-3)")}
                    strokeWidth={isChosen ? 3 : 2}
                    strokeDasharray={e.claimed ? "0" : (isChosen ? "0" : "3 4")}
                    onClick={() => !e.claimed && setChosen(e.uid)}
                    style={{cursor: e.claimed ? "not-allowed" : "pointer"}} />
                  <text x={(p1.x+p2.x)/2} y={(p1.y+p2.y)/2 - 4}
                    fontSize="10" fontFamily="var(--mono)" textAnchor="middle"
                    fill={e.claimed ? "var(--bad)" : isChosen ? "var(--accent)" : "var(--ink-3)"}>
                    {e.label}{e.claimed ? "✓" : ""}
                  </text>
                </g>
              );
            })}
          </svg>
          {cities.map(c => {
            const p = pos(c);
            return (
              <div key={c.uid} className="map-node visited"
                style={{left:`${(p.x/W)*100}%`, top:`${(p.y/H)*100}%`, fontSize:9}}>
                {c.name}
              </div>
            );
          })}
        </div>

        <div style={{display:"grid", gap:8, fontSize:12}}>
          <div>
            <b>Connections</b> — pieces that live in <code>GraphLayout.edges[]</code>, each carrying its own <code>uid</code>. A <code>place</code> choice with <code>edge_ref</code> points at one. Dashed = open · red = claimed.
          </div>
          <div style={{display:"flex", flexDirection:"column", gap:4}}>
            {edges.map(e => (
              <button key={e.uid} type="button"
                disabled={e.claimed}
                onClick={() => setChosen(e.uid)}
                className={"choice-v12 " + (e.claimed ? "locked" : "")}
                style={{padding:"4px 8px"}}>
                <span className="key">{chosen === e.uid ? "●" : "○"}</span>
                <span className="label">
                  {byCity[e.a].name} — {byCity[e.b].name} <span className="muted">· length {e.label}</span>
                  {e.claimed && <span className="reason"> claimed by {e.by}</span>}
                </span>
                <span className="meta">
                  <span className="cost down">−{e.label} trains</span>
                </span>
              </button>
            ))}
          </div>
          <pre style={{fontFamily:"var(--mono)", fontSize:10, background:"var(--paper)", border:"1px solid var(--rule)", padding:"6px 8px", margin:0, lineHeight:1.45}}>
{`POST /story/do
{
  "edge_id": "e-lay-track",
  "payload": {
    "piece_id": "pc-train-blue",
    "edge_ref": "${chosen}"
  }
}`}
          </pre>
        </div>
      </div>
    </div>
  );
}

// ===========================================================================
// §8 — Roll ritual + StatCheck (Gravel)
// ===========================================================================

function RollDemo() {
  const fx = window.V15_FIXTURES.gravel;
  const [phase, setPhase] = useSecState("pre"); // pre | fail | crit

  const env =
    phase === "pre" ? fx.pre.envelope :
    phase === "crit" ? fx.post_crit.envelope :
    fx.post_fail.envelope;

  const idx = indexEnvelope(env);
  const items = (findScene(env)?.member_ids || []).map(id => idx.byUid[id]).filter(Boolean);

  return (
    <div className="panel-card">
      <h3>Tier P2 · RollFragment + ritual_hints
        <span className="right">"hold the line on the gravel"</span>
      </h3>
      <div className="cli-grid">
        <div style={{display:"grid", gap:10, minWidth:0}}>
          <div className="row-flex" style={{gap:6}}>
            <div className="seg" style={{display:"flex", border:"1.25px solid var(--ink)"}}>
              {[["pre","Pre-roll choice"], ["fail","Post-roll · fail"], ["crit","Post-roll · crit success"]].map(([k, label]) => (
                <button key={k} onClick={() => setPhase(k)}
                  className={phase === k ? "on" : ""}
                  style={{
                    fontFamily:"var(--mono)", fontSize:10,
                    background: phase === k ? "var(--ink)" : "var(--paper)",
                    color: phase === k ? "var(--paper)" : "var(--ink)",
                    border:"none", borderRight:"1px solid var(--ink)",
                    padding:"5px 10px", cursor:"pointer"
                  }}>
                  {label}
                </button>
              ))}
            </div>
            <span className="muted" style={{fontFamily:"var(--mono)", fontSize:10.5, marginLeft:"auto"}}>
              step {env.step}
            </span>
          </div>
          <div className="demo-grid-2">
            <div style={{display:"grid", gap:10}}>
              {items.map(f => {
                if (f.fragment_type === "content") return <ContentBlock key={f.uid} frag={f} />;
                if (f.fragment_type === "roll") return <RollWidget key={f.uid} frag={f} />;
                return null;
              })}
              {phase === "pre" && (
                <ChoiceList choices={items.filter(f => f.fragment_type === "choice")} env={env} onCommit={() => {}} />
              )}
              {phase === "fail" && (
                <ChoiceList choices={items.filter(f => f.fragment_type === "choice")} env={env} onCommit={() => {}} />
              )}
            </div>
            <div style={{display:"grid", gap:10}}>
              <div className="callout" style={{fontSize:11, padding:"8px 10px"}}>
                <b>Pre-roll legibility.</b> <code>ui_hints.stat_check</code> surfaces difficulty + dice + advisory odds BEFORE commit so the player understands the wager. Backend re-evaluates; the preview is informational, never authority.
              </div>
              <div className="callout" style={{fontSize:11, padding:"8px 10px"}}>
                <b>Skippable ritual.</b> The skip affordance in the top-right of the roll panel jumps straight to the canonical-instant rendering (the CLI floor). <code>ritual_hints.auto_skip_after_seen</code> lets bundles play full ritual on the first damage roll but instant on subsequent ones — the player can override either way.
              </div>
              <pre style={{fontFamily:"var(--mono)", fontSize:10.5, background:"var(--paper)", border:"1px solid var(--rule)", padding:"8px", margin:0, overflow:"auto", lineHeight:1.4}}>
{`{
  "fragment_type": "roll",
  "kind": "dice",
  "label": "Driving check",
  "inputs": { "dice":"2d6","rolled":[4,5],"modifier":0,
              "total":9,"target":12 },
  "outcome": "fail",
  "against": { "piece_id":"you","property":"driving" },
  "narrative": "The wheel jerks under you...",
  "ritual_hints": {
    "skip_label":"Skip","duration_ms":1800,
    "auto_skip_after_seen": false,
    "allow_replay": true
  }
}`}
              </pre>
            </div>
          </div>
        </div>

        <CliPane lines={cliRenderRoll(fx, phase)} label={`roll · ${phase} · cli`} />
      </div>
    </div>
  );
}

// ===========================================================================
// §9 — Command bar + InterpretationFragment
// ===========================================================================

function CommandDemo() {
  const env = window.V15_FIXTURES.crossroads.envelope;
  const samples = window.V15_FIXTURES.gravel.interp_samples;
  return (
    <div className="panel-card">
      <h3>Tier P1 · raw_command, grammar hint, InterpretationFragment
        <span className="right">"parser fallback as transcript"</span>
      </h3>
      <div className="cli-grid">
        <div className="demo-grid-2" style={{minWidth:0}}>
        <div style={{display:"grid", gap:10}}>
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>
            command bar — wraps the reserved <code>interpret_command</code> choice
          </div>
          <CommandBar env={env} onSubmit={() => {}} />
          <div className="callout" style={{fontSize:11, padding:"8px 10px", marginTop:0}}>
            Ports that don't implement a command bar simply render <code>interpret_command</code> as a normal button labeled "Try a command." with a text input. <code>metadata.grammar</code> is the denormalized visible-action surface — it never grants the player a verb that no visible choice covers.
          </div>

          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:6}}>
            interpretation transcript — engine feedback, cursor does NOT advance
          </div>
          {samples.map(s => <Interpretation key={s.uid} frag={s} />)}
        </div>

        <div style={{display:"grid", gap:10}}>
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>InterpretResult values</div>
          <table className="parity-table">
            <tbody>
              <tr><td className="w">ambiguous</td><td>multiple edges matched; <code>candidates[]</code> populated</td></tr>
              <tr><td className="w">unknown_verb</td><td>no verb matched the grammar</td></tr>
              <tr><td className="w">unknown_noun</td><td>verb matched, noun did not</td></tr>
              <tr><td className="w">blocked</td><td>fully resolved but predicate refused; <code>blocked_reason</code> populated</td></tr>
              <tr><td className="w">impossible</td><td>no edge covers the requested action shape</td></tr>
              <tr><td className="w">validation_failed</td><td>typed validator rejected the payload</td></tr>
            </tbody>
          </table>
          <pre style={{fontFamily:"var(--mono)", fontSize:10.5, background:"var(--paper)", border:"1px solid var(--rule)", padding:"8px", margin:0, overflow:"auto", lineHeight:1.4}}>
{`POST /story/do
{ "edge_id": "interpret_command",
  "payload": { "text": "take key" } }

200 OK — RuntimeEnvelope
  step:    47   ← unchanged (no advance)
  cursor:  same
  fragments: [
    InterpretationFragment{
      result: "ambiguous",
      text: "take key",
      message: "Which key?",
      candidates: ["e-take#brass_key","e-take#iron_key"]
    },
    ...the open choices, intact
  ]`}
          </pre>
        </div>
        </div>

        <CliPane lines={cliRenderCommand()} label="cmd · cli reference port" />
      </div>
    </div>
  );
}

// ===========================================================================
// §10 — SANDBOX demo (info-channel conventions; primary integration)
// ===========================================================================

function SandboxDemo() {
  const fx = window.V15_FIXTURES.manor;
  const env = fx.envelope;
  const proj = fx.projected_state;
  const idx = indexEnvelope(env);
  const byUid = idx.byUid;

  const wt   = proj.sections.find(s => s.section_id === "world_time");
  const loc  = proj.sections.find(s => s.section_id === "location");
  const ag   = proj.sections.find(s => s.section_id === "agenda");
  const obj  = proj.sections.find(s => s.section_id === "objectives");
  const periods = proj.sections.find(s => s.section_id === "periods");
  const purse = proj.sections.find(s => s.section_id === "purse");
  const weight = proj.sections.find(s => s.section_id === "weight");

  const mapZone = byUid["z-map"];
  const roomZone = byUid["z-inv"];

  const meta = env.metadata;
  const info = meta.info_state || {};
  const [activeInfo, setActiveInfo] = useSecState(null);
  const dirty = new Set(info.dirty_kinds || []);

  const choices = env.fragments.filter(f => f.fragment_type === "choice");
  const sceneItems = (findScene(env)?.member_ids || []).map(id => byUid[id]).filter(Boolean);

  return (
    <div className="panel-card">
      <h3>Tier P1 target — sandbox info-channel
        <span className="right">"the bedroom"</span>
      </h3>

      {/* World time + info-affordance bar (top) */}
      <div style={{display:"grid", gap:10}}>
        <div className="world-time">
          <div className="clock">
            <div className="hand-h" />
            <div className="hand-m" />
          </div>
          <div className="wt-text">
            {wt.value.items.find(i => i.key === "period")?.value} ·
            day {wt.value.items.find(i => i.key === "day")?.value}
            <span className="sub">turn {wt.value.items.find(i => i.key === "turn")?.value} · {wt.value.items.find(i => i.key === "phase")?.value}</span>
          </div>
          <div className="wt-side">
            <span><b>{periods.value.items[0].value}/{periods.value.items[0].max}</b> periods left</span>
            <span className="muted">section: kv_list · kind=&quot;world_time&quot;</span>
          </div>
        </div>

        <div className="info-bar" aria-label="info affordances">
          {(meta.info_affordances || []).map(ia => (
            <button key={ia.kind} type="button"
              className={"info-aff" +
                (dirty.has(ia.kind) ? " dirty" : "") +
                (activeInfo === ia.kind ? " active" : "")}
              onClick={() => setActiveInfo(activeInfo === ia.kind ? null : ia.kind)}>
              <span className="k">{ia.shortcuts[0]}</span>
              <span>{ia.label}</span>
            </button>
          ))}
          <span className="muted" style={{marginLeft:"auto", fontFamily:"var(--mono)", fontSize:10.5}}>
            info_state.version: <b>{info.version}</b>
            {" · "}dirty: [{(info.dirty_kinds || []).join(", ")}]
          </span>
        </div>

        <div className="callout" style={{fontSize:11, padding:"8px 10px"}}>
          <b>Info affordances</b> are not choices — each carries an opaque{" "}
          <code>query</code> descriptor (or <code>null</code>) the backend interprets.
          Hand-it-back semantics: the client never inspects <code>query</code>; it just routes
          the descriptor to the info endpoint. <code>metadata.info_state.dirty_kinds</code> tells
          the client which channels to refresh; <code>info_state.version</code> is monotonic per
          cursor for cache invalidation. Hidden state never crosses the wire.
        </div>
      </div>

      {/* Sandbox layout — two columns: scene/choices left, projected info right */}
      <div className="sandbox-grid" style={{marginTop:8}}>
        <div style={{display:"grid", gap:10}}>
          {/* Recent transcript (echo + prior interpretation) */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>recent transcript</div>
          {sceneItems
            .filter(f => f.hints?.style_tags?.includes("echo") || f.uid === "echo-2" || f.uid === "i-prev")
            .concat(env.fragments.filter(f => f.uid === "i-prev" && !sceneItems.includes(f)))
            .filter((f, i, arr) => arr.indexOf(f) === i)
            .map(f => {
              if (f.fragment_type === "interpretation") return <Interpretation key={f.uid} frag={f} />;
              if (f.fragment_type === "content") return <ContentBlock key={f.uid} frag={f} />;
              return null;
            })}
          {/* The scene prose for this turn */}
          {sceneItems.filter(f => f.uid === "c-prose").map(f => <ContentBlock key={f.uid} frag={f} />)}

          {/* Room zone (pieces) + inventory zone */}
          <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:8}}>
            <ZoneTile zone={byUid["z-room"]} env={env} byUid={byUid} />
            <ZoneTile zone={byUid["z-inv"]} env={env} byUid={byUid} />
          </div>

          {/* Choices — show provenance tag */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:6}}>
            open choices · <code>ui_hints.source_kind</code> in the badge
          </div>
          <ChoiceList choices={choices} env={env} onCommit={() => {}} options={{showSource: true}} />
          <CommandBar env={env} onSubmit={() => {}} />
        </div>

        <div style={{display:"grid", gap:10}}>
          {/* Map */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", display:"flex", alignItems:"center", gap:8}}>
            <span>map zone — <code>kind=&quot;location&quot;</code> pieces, edges in <code>layout_hints.graph.edges[]</code></span>
            <span className="tier tier-p2" style={{marginLeft:"auto", fontSize:8.5}}>position + edges: proposal</span>
          </div>
          <SandboxMap zone={mapZone} env={env} byUid={byUid} />

          {/* Presence (location) */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:6}}>
            Here — <code>kind=&quot;location&quot;</code> item_list
          </div>
          <PresenceList section={loc} />

          {/* Agenda */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:6}}>
            Schedule — <code>kind=&quot;agenda&quot;</code> item_list (disclosed only)
          </div>
          <AgendaList section={ag} />

          {/* Objectives */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:6}}>Objectives</div>
          <PresenceList section={obj} />

          {/* Resources strip */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:6}}>Resources</div>
          <RailSection section={purse} />
          <RailSection section={weight} />
        </div>
      </div>

      {/* Patch C — info-affordance Input Parity fallback (§5.3). The pill
          bar above is one way to expose info channels; a port without it
          surfaces the same channels through some CLI-floor mode (typically
          slash commands derived from info_affordances[].shortcuts, plus a
          ? menu). This pane shows the SAME envelope rendered with the
          floor affordance. */}
      <div style={{marginTop:14}}>
        <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:6}}>
          §5.3 input parity — same envelope, CLI floor (no info-pill bar)
        </div>
        <div className="cli-grid">
          <div className="callout" style={{fontSize:11, padding:"8px 10px", margin:0}}>
            <b>Input parity is the load-bearing rule for info channels.</b> The pill
            bar above is a presentation enhancement. A port without room for it
            (CLI, narrow viewport, accessibility mode) MUST expose the same channels
            through some CLI-floor mode. The canonical fallback is slash commands
            derived from <code>info_affordances[].shortcuts</code> plus a single
            <code>?</code> menu. Same envelope, same channels, no pills:
            <ul style={{margin:"6px 0 0 18px", padding:0}}>
              <li><code>/t</code> or <code>time</code> → world_time</li>
              <li><code>/h</code> or <code>look</code> → presence</li>
              <li><code>/i</code> or <code>inv</code> → inventory</li>
              <li><code>/m</code> or <code>map</code> → map (graph projection)</li>
              <li><code>?</code> → full menu of available channels</li>
            </ul>
          </div>
          <CliPane lines={cliRenderSandbox(fx)} label="sandbox · cli reference port" />
        </div>
      </div>
    </div>
  );
}

function PresenceList({ section }) {
  if (!section) return null;
  return (
    <div className="presence">
      {section.value.items.map((it, i) => {
        const tags = it.tags || [];
        const role =
          tags.includes("exit") ? "exit" :
          tags.includes("place") ? "place" :
          tags.includes("fixture") ? "fixture" :
          tags.includes("mob") || tags.includes("actor") ? "actor" :
          "item";
        return (
          <div key={i} className={"row " + role}>
            <span className="role">{role}</span>
            <span>
              <b className="label">{it.label}</b>
              {it.detail && <span className="detail"> · {it.detail}</span>}
            </span>
            <span>
              {tags.filter(t => t !== "place" && t !== "exit").map((t, j) => (
                <span key={j} className="tag">{t}</span>
              ))}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function AgendaList({ section }) {
  if (!section) return null;
  return (
    <div className="agenda">
      {section.value.items.map((it, i) => {
        const tags = it.tags || [];
        const tentative = tags.includes("tentative");
        return (
          <div key={i} className={"ag" + (tentative ? " tentative" : "")}>
            <span className="when">{(it.detail || "").split(",")[0]}</span>
            <span className="what">{it.label}</span>
            <span className="src">{tags.join(" · ")}</span>
          </div>
        );
      })}
    </div>
  );
}

function SandboxMap({ zone, env, byUid }) {
  // §7.2 — GraphLayout.edges carry uids; PlaceAccepts.edge_ref points at them.
  // We accept either the new edges[] form or the legacy adjacency[][a,b] form.
  const graph = zone.layout_hints?.graph || {};
  const edges = graph.edges
    || (graph.adjacency || []).map(([a, b], i) => ({ uid: `edge-${i}`, a, b }));
  const idx = indexEnvelope(env);
  const piece = idx.piece;
  const nodes = (zone.member_ids || [])
    .map(id => byUid[id])
    .filter(p => p && p.fragment_type === "piece");

  // size for our svg viewbox
  const W = 320, H = 200, padX = 50, padY = 36;
  // §7.1: free-form spatial pieces carry {x, y} on `position`.
  const xy = (n) => n.position || { x: n.properties?.x ?? 1, y: n.properties?.y ?? 1 };
  const xs = nodes.map(n => xy(n).x);
  const ys = nodes.map(n => xy(n).y);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const sx = (xMax === xMin ? 0.5 : (W - 2*padX) / (xMax - xMin));
  const sy = (yMax === yMin ? 0.5 : (H - 2*padY) / (yMax - yMin));
  const pos = (n) => {
    const { x, y } = xy(n);
    return { x: padX + (x - xMin) * sx, y: padY + (y - yMin) * sy };
  };

  return (
    <div className="sandbox-map" style={{height: H}}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        {edges.map((e, i) => {
          const pa = piece(e.a), pb = piece(e.b);
          if (!pa || !pb) return null;
          const p1 = pos(pa), p2 = pos(pb);
          const locked = e.properties?.locked
                      || pa.properties.state === "locked"
                      || pb.properties.state === "locked";
          const known  = pa.properties.state !== "unexplored" && pb.properties.state !== "unexplored";
          return (
            <line key={e.uid || i} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              className={"map-edge" + (locked ? " locked" : known ? " known" : "")} />
          );
        })}
      </svg>
      {nodes.map(n => {
        const p = pos(n);
        return (
          <div key={n.uid}
            className={"map-node " + (n.properties.state || "")}
            style={{left: `${(p.x/W)*100}%`, top: `${(p.y/H)*100}%`}}>
            {n.properties.name}
            {n.properties.state === "here" && <span className="muted" style={{display:"block", fontSize:8, color:"var(--paper-2)"}}>(you)</span>}
          </div>
        );
      })}
    </div>
  );
}

// ===========================================================================
// §11 — Port parity (final compact table)
// ===========================================================================

function ParityTable12() {
  const rows = [
    { w: "Prose / dialog",          web: "<article>, avatar+bubble", cli: "wrapped stdout, who [how]> text", tk: "Text segment, image+label", renpy: "narrator / character say" },
    { w: "Cover / narrative media", web: "<img>/<video>",            cli: "[img: url]",                       tk: "Label(image=…)",            renpy: "scene bg / TextureRect" },
    { w: "Pending RIT media",       web: "striped placeholder swapped via update",    cli: "[pending: rit-id]", tk: "placeholder Frame",       renpy: "placeholder until update" },
    { w: "Choice (pick)",           web: "button list",              cli: "1) text",                          tk: "Button",                    renpy: "menu:" },
    { w: "Choice (text / quantity)", web: "inline <input>",          cli: "'>' prompt",                       tk: "Entry + submit",            renpy: "renpy.input" },
    { w: "Choice (pieces / place)", web: "click-pick or drag",       cli: "two-step numbered pick",            tk: "Listbox + button",          renpy: "menu of constrained pieces" },
    { w: "Choice (compose)",        web: "stacked sub-widgets",      cli: "prompt per part in order",         tk: "Frame of sub-widgets",      renpy: "sequence of inputs" },
    { w: "raw_command",             web: "command bar w/ grammar",   cli: "'>' prompt at all times",          tk: "Entry · Enter",             renpy: "renpy.input fallback" },
    { w: "interpretation",          web: "transcript line w/ accent", cli: "echo + result line",              tk: "Text segment",              renpy: "narrator + hint" },
    { w: "piece chip",              web: "chip / card",              cli: "name (kind, props)",               tk: "Label + meta",              renpy: "ListItem" },
    { w: "zone · slot (capacity)",  web: "tile + capacity bar",      cli: "[label: contents (cap, used/max)]", tk: "Labelframe + Progressbar", renpy: "panel + bar" },
    { w: "zone · catalog (offers)", web: "card grid w/ cost stripe", cli: "numbered list with cost column",   tk: "Listbox + per-row button",  renpy: "menu of offers" },
    { w: "zone · packet (credentials)", web: "row of document tiles", cli: "[packet] - <doc> holder=… …",     tk: "Frame of doc cards",        renpy: "RPG-style party menu" },
    { w: "zone · board (graph)",    web: "node-edge map with current marker", cli: "[here] location-name [<kind>] · exits → …", tk: "Canvas of nodes",   renpy: "screen of imagebuttons" },
    { w: "roll (dice ritual)",      web: "tumble + outcome chip",    cli: "rolled: a+b=T → outcome",          tk: "Text segment + label",      renpy: "tumble + outcome" },
    { w: "roll (custom · hunt)",    web: "structured panel (drawn / assignments / captures)", cli: "[<label>] captures: … escapes: …", tk: "tabbed Frame", renpy: "cinematic sequence" },
    { w: "kv_list bars/fractions",  web: "bar / fraction / delta row", cli: "key: value [/max] [unit]",       tk: "ttk.Progressbar / Label",   renpy: "VBox of rows" },
    { w: "kv (findings, severity)", web: "color-coded chip row (ok/warn/danger)", cli: "  ✓/!/!! key = value", tk: "color-tagged Labels",       renpy: "screen of action chips" },
    { w: "world_time section",      web: "watch tile (clock face)",  cli: "Time: Day 3, evening",             tk: "Frame w/ Label",            renpy: "clock widget" },
    { w: "location / presence",     web: "presence panel",           cli: "Here: bedroom — lamp, mailbox, exits north / down",      tk: "Listbox",   renpy: "VBox of rows" },
    { w: "agenda / schedule",       web: "when · what · src",        cli: "Schedule: barn dance (evening, barn) — known",          tk: "Listbox",   renpy: "VBox" },
    { w: "info-affordance bar",     web: "pill row · dirty marks",   cli: "(info: /m map · /i inv · ?)",      tk: "Frame of Buttons",          renpy: "stats screen affordances" },
    { w: "stat_check / validity_check / encounter_check preview", web: "small badge on choice", cli: "[<label> <dice> vs <prop>, <p>]", tk: "Label tooltip", renpy: "menu hint" },
    { w: "user_event",              web: "bottom toast",             cli: "* type: content",                  tk: "Toplevel transient",        renpy: "notify()" },
    { w: "control update/delete",   web: "re-render target in place", cli: "re-print with marker",            tk: "re-render cell",            renpy: "re-run statement" },
  ];
  return (
    <table className="parity-table">
      <thead><tr>
        <th>Widget</th>
        <th>Web (reference)</th>
        <th>CLI (line-oriented · floor)</th>
        <th>tkinter (block-oriented)</th>
        <th>Ren'Py / Godot</th>
      </tr></thead>
      <tbody>{rows.map((r, i) => (
        <tr key={i}>
          <td className="w">{r.w}</td>
          <td>{r.web}</td>
          <td>{r.cli}</td>
          <td>{r.tk}</td>
          <td>{r.renpy}</td>
        </tr>
      ))}</tbody>
    </table>
  );
}

Object.assign(window, {
  TierLegend, ParityStool, V15Changes,
  FragmentMatrix, AcceptsKindCheatsheet,
  GarageDemo, RollDemo, CommandDemo,
  SandboxDemo, PresenceList, AgendaList, SandboxMap,
  ParityTable12,
  // CLI helpers reused by genre sections:
  CliPane, cliWrap, cliRenderCrossroads, cliRenderGarage,
  cliRenderRoll, cliRenderCommand, cliRenderSandbox,
});
