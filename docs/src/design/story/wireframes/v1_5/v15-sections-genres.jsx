// v15-sections-genres.jsx — genre extension demos (Tier P3).
//
// One demo per bundle. Each is structured as:
//   - intro paragraph (what this genre adds on top of core vocab)
//   - rich web rendering (using core widgets) + CLI floor pane side-by-side
//   - bundle-specific enrichments highlighted in callouts
//
// Bundles covered:
//   §6.1 carwars      — already in v15-sections-core.jsx as GarageDemo
//   §6.2 credentials  — packet inspection + severity-coded findings + mediation
//   §6.3 training     — mood modulator + scheduled stat_check + inventory unlock
//   §6.4 elefant_hunt — board graph + composite hunt roll + journal-as-story
//
// Also exports JournalAsStory (§5 capability demo).

const { useState: useGenState, useMemo: useGenMemo } = React;

// ===========================================================================
// CLI renderers — one per genre
// ===========================================================================

function cliRenderCredentials(fx) {
  const env = fx.envelope;
  const idx = indexEnvelope(env);
  const out = [];
  const prose = idx.byUid["c-prose"];
  if (prose) {
    out.push(cliWrap(String(prose.content).replace(/\*\*/g, "").replace(/\*/g, ""), 46));
    out.push("");
  }
  const cand = idx.byUid["pc-cand"];
  if (cand) {
    out.push(`Candidate: ${cand.properties.name} ` +
             `(declared ${cand.properties.declared_purpose}, ` +
             `from ${cand.properties.declared_origin})`);
    out.push("");
  }
  out.push("[Credentials packet]");
  const packet = idx.byUid["z-packet"];
  for (const id of packet.member_ids) {
    const p = idx.byUid[id];
    const props = p.properties;
    const parts = [props.name];
    if (props.holder)  parts.push(`holder=${props.holder}`);
    if (props.expiry)  parts.push(`expiry ${props.expiry}`);
    if (props.origin)  parts.push(`origin=${props.origin}`);
    if (props.purpose) parts.push(`purpose=${props.purpose}`);
    if (props.seal)    parts.push(`seal=${props.seal}`);
    out.push(`  - ${parts.join("  ")}`);
  }
  out.push("");
  // findings
  const findings = idx.byUid["f-findings"];
  if (findings) {
    out.push("[findings]");
    for (const r of findings.content) {
      const glyph =
        r.emphasis === "ok"     ? "✓ " :
        r.emphasis === "warn"   ? "! " :
        r.emphasis === "danger" ? "!!" :
        "  ";
      out.push(`  ${glyph} ${(r.key + " = ").padEnd(18)}${r.value}`);
    }
    out.push("");
  }
  // restrictions
  out.push("[shift directives]");
  const restr = fx.projected_state.sections.find(s => s.section_id === "restrictions");
  for (const r of restr.value.items) {
    const glyph =
      r.emphasis === "ok"     ? "✓ " :
      r.emphasis === "warn"   ? "! " :
      r.emphasis === "danger" ? "!!" :
      "  ";
    out.push(`  ${glyph} ${(r.key + " — ").padEnd(28)}${r.value}`);
  }
  out.push("");
  out.push("-- mediation --");
  let i = 1;
  for (const c of env.fragments.filter(f => f.fragment_type === "choice" &&
      (f.ui_hints?.contribution === "interaction"))) {
    const cps = (c.ui_hints?.cost_previews || []).filter(p => p.delta !== 0);
    const cost = cps.length
      ? "  (" + cps.map(p => `${p.delta < 0 ? "−" : "+"}${Math.abs(p.delta)} ${p.unit}`).join(" · ") + ")"
      : "";
    out.push(`  ${i}) ${c.text}${cost}`);
    i++;
  }
  out.push("");
  out.push("-- disposition --");
  const disps = env.fragments.filter(f => f.fragment_type === "choice" &&
      f.ui_hints?.contribution === "disposition");
  for (const c of disps) {
    const hk = c.ui_hints?.hotkey || "?";
    if (c.available) {
      out.push(`  ${hk}) ${c.text}`);
    } else {
      out.push(`  ${hk}) ${c.text}  (locked: ${c.unavailable_reason})`);
    }
  }
  out.push("> ");
  return out.join("\n");
}

function cliRenderTraining(fx, phase) {
  const env = phase === "post" ? fx.post_audience.envelope : fx.envelope;
  const idx = indexEnvelope(env);
  const out = [];
  const items = (findScene(env)?.member_ids || []).map(id => idx.byUid[id]).filter(Boolean);
  for (const f of items) {
    if (f.fragment_type === "content") {
      out.push(cliWrap(String(f.content).replace(/\*\*/g, "").replace(/\*/g, ""), 46));
      out.push("");
    } else if (f.fragment_type === "roll") {
      const c = f.inputs;
      out.push(`  [${f.label}]`);
      out.push(`  rolled: ${(c.rolled || []).join(" + ")}${c.modifier ? ` ${c.modifier > 0 ? "+" : ""}${c.modifier}` : ""} = ${c.total} vs target ${c.target}`);
      out.push(`  outcome: ${f.outcome.replace("_", " ")}`);
      if (f.narrative) out.push("  " + cliWrap(f.narrative, 44).split("\n").join("\n  "));
      out.push("");
    }
  }
  if (phase !== "post") {
    // projected state
    const proj = fx.projected_state.sections;
    const sched = proj.find(s => s.section_id === "schedule");
    const mood  = proj.find(s => s.section_id === "mood");
    const stats = proj.find(s => s.section_id === "stats");
    const wall  = proj.find(s => s.section_id === "wallet");
    if (sched) out.push(`[Schedule] ${sched.value.value}`);
    if (mood)  out.push(`[Mood]     ${mood.value.value}`);
    out.push("[Stats]");
    for (const r of stats.value.items) {
      out.push(`  ${(r.key + "").padEnd(7)} ${r.value}/${r.max} (bar)${r.emphasis ? `  (${r.emphasis})` : ""}`);
    }
    out.push("[Wallet]");
    for (const r of wall.value.items) {
      const v = r.max != null ? `${r.value}/${r.max}` : `${r.value} ${r.unit || ""}`;
      out.push(`  ${(r.key + "").padEnd(8)} ${v}`);
    }
    out.push("");
    out.push("-- weekly choice --");
    let i = 1;
    for (const c of env.fragments.filter(f => f.fragment_type === "choice" && f.edge_id !== "interpret_command")) {
      const sc = c.ui_hints?.stat_check;
      const cps = (c.ui_hints?.cost_previews || []).filter(p => p.delta !== 0);
      const suffix = sc
        ? `  [${sc.label} ${sc.dice} vs ${sc.against?.property || "?"}, ${sc.success_text || "varies"}]`
        : cps.length
          ? "  (" + cps.map(p => `${p.delta < 0 ? "−" : "+"}${Math.abs(p.delta)} ${p.unit || p.ledger_key}`).join(" · ") + ")"
          : "";
      if (c.available) {
        out.push(`  ${i}) ${c.text}${suffix}`);
      } else {
        out.push(`  ${i}) ${c.text}  (locked: ${c.unavailable_reason})`);
      }
      i++;
    }
    out.push("> ");
  } else {
    out.push("  1) Begin Week 3.");
    out.push("> ");
  }
  return out.join("\n");
}

function cliRenderElefantHunt(fx) {
  const env = fx.envelope;
  const idx = indexEnvelope(env);
  const out = [];
  const prose = idx.byUid["c-prose"];
  if (prose) {
    out.push(cliWrap(String(prose.content).replace(/\*\*/g, "").replace(/\*/g, ""), 46));
    out.push("");
  }

  // The board (graph sketch)
  out.push("[map]");
  const board = idx.byUid["z-board"];
  for (const id of board.member_ids) {
    const loc = idx.byUid[id];
    const here = loc.properties.state === "here" ? " (you)" : "";
    const kind = loc.properties.loc_kind;
    const glyph =
      kind === "port"           ? "⚓" :
      kind === "trail"          ? "·" :
      kind === "hazard"         ? "!" :
      kind === "junction"       ? "▲" :
      kind === "hunting_ground" ? "*" :
      kind === "graveyard"      ? "†" : " ";
    out.push(`  ${glyph} ${loc.properties.name}${here}`);
  }
  out.push("");

  // Expedition
  out.push("[expedition]");
  const exp = idx.byUid["z-expedition"];
  for (const id of exp.member_ids) {
    const p = idx.byUid[id];
    if (p.kind === "hunter") {
      out.push(`  - ${p.properties.name} (HV ${p.properties.hunting_value}, ${p.properties.status})`);
    } else if (p.kind === "animal") {
      out.push(`  - ${p.properties.name} (${p.properties.point_value} pts)`);
    } else if (p.kind === "ivory") {
      out.push(`  - ivory marker (to be appraised)`);
    }
  }
  out.push("");

  // Hunt roll
  const hunt = idx.byUid["r-hunt"];
  if (hunt) {
    out.push(`  [${hunt.label}]`);
    out.push(`  drawn:    ${hunt.inputs.drawn.map(d => d.species).join(", ")}`);
    out.push(`  captures: ${hunt.inputs.captures.join(", ") || "—"}`);
    out.push(`  escapes:  ${hunt.inputs.escapes.join(", ") || "—"}`);
    out.push(`  outcome:  ${hunt.outcome.replace("_", " ")}`);
    if (hunt.narrative) {
      out.push("  " + cliWrap(hunt.narrative, 44).split("\n").join("\n  "));
    }
    out.push("");
  }

  // supplies + score
  out.push("-- ledger --");
  for (const s of fx.projected_state.sections) {
    if (s.value.value_type === "scalar") {
      out.push(`  ${s.title.padEnd(10)} ${s.value.value}`);
    } else if (s.value.value_type === "kv_list") {
      for (const r of s.value.items) {
        const v = r.max != null ? `${r.value}/${r.max} ${r.unit || ""}` : `${r.value} ${r.unit || ""}`;
        out.push(`  ${(r.key || "").padEnd(10)} ${v.trim()}`);
      }
    }
  }
  out.push("");

  // movement choices
  out.push("-- exits --");
  let i = 1;
  for (const c of env.fragments.filter(f => f.fragment_type === "choice" && f.edge_id !== "interpret_command")) {
    const ec = c.ui_hints?.encounter_check;
    const cps = (c.ui_hints?.cost_previews || []).filter(p => p.delta !== 0);
    const cost = cps.length ? `  (${cps.map(p => `${p.delta < 0 ? "−" : "+"}${Math.abs(p.delta)} ${p.unit}`).join(" · ")})` : "";
    const ecS = ec ? `  [${ec.label}: ${ec.risk_text || "—"}]` : "";
    out.push(`  ${i}) ${c.text}${cost}`);
    if (ec) out.push(`     ${ec.label.toLowerCase()} · ${ec.risk_text}`);
    i++;
  }
  out.push("> ");
  return out.join("\n");
}

// ===========================================================================
// §6.2 Credentials demo
// ===========================================================================

function CredentialsDemo() {
  const fx = window.V15_FIXTURES.credentials;
  const env = fx.envelope;
  const proj = fx.projected_state;
  const idx  = useGenMemo(() => indexEnvelope(env), [env]);
  const byUid = idx.byUid;

  const cand     = byUid["pc-cand"];
  const packet   = byUid["z-packet"];
  const findings = byUid["f-findings"];
  const choices  = env.fragments.filter(f => f.fragment_type === "choice");
  const mediation   = choices.filter(c => c.ui_hints?.contribution === "interaction");
  const dispositions = choices.filter(c => c.ui_hints?.contribution === "disposition");

  return (
    <div className="panel-card">
      <h3>Tier P3 · credentials — packet inspection, severity findings, mediation
        <span className="right">"the merchant Bek Tarsus"</span>
      </h3>
      <div className="cli-grid">
        <div style={{display:"grid", gap:12, minWidth:0}}>
          {/* prose */}
          {byUid["c-prose"] && <ContentBlock frag={byUid["c-prose"]} />}

          {/* candidate */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>
            candidate — <code>PieceFragment(kind="candidate")</code>
          </div>
          <div style={{display:"flex", gap:10, alignItems:"center", border:"1.25px solid var(--ink)", padding:"8px 10px", background:"var(--paper)"}}>
            <div style={{width:48, height:48, border:"1.25px solid var(--ink)", borderRadius:"50%",
                          background:"repeating-linear-gradient(45deg, var(--paper-2) 0 6px, var(--paper) 6px 12px)",
                          display:"flex", alignItems:"center", justifyContent:"center",
                          fontFamily:"var(--mono)", fontSize:9, color:"var(--ink-3)"}}>PH</div>
            <div style={{display:"grid", gap:2}}>
              <div style={{fontFamily:"var(--serif)", fontSize:16, fontWeight:600}}>{cand.properties.name}</div>
              <div style={{fontFamily:"var(--mono)", fontSize:10.5, color:"var(--ink-3)"}}>
                declared <b style={{color:"var(--ink)"}}>{cand.properties.declared_purpose}</b>{" · "}
                from <b style={{color:"var(--ink)"}}>{cand.properties.declared_origin}</b>
              </div>
            </div>
          </div>

          {/* packet zone */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>
            credentials packet — <code>zone_role="packet"</code>
          </div>
          <div className="zone field" style={{borderColor:"var(--ink)"}}>
            <div className="zone-hd">
              <span>{packet.hints?.label_text || "Packet"}</span>
              <span className="role">packet · {packet.member_ids.length} docs</span>
            </div>
            <div className="zone-body" style={{flexDirection:"column", gap:4}}>
              {packet.member_ids.map(id => {
                const p = byUid[id];
                return (
                  <div key={p.uid} style={{
                    display:"grid", gridTemplateColumns:"110px 1fr",
                    fontFamily:"var(--mono)", fontSize:10.5,
                    border:"1px solid var(--rule)",
                    padding:"5px 8px",
                    background:"var(--paper)",
                    gap:8,
                  }}>
                    <div style={{fontWeight:700}}>{p.hints?.label_text || p.properties?.name}</div>
                    <div style={{color:"var(--ink-3)"}}>
                      {Object.entries(p.properties || {})
                        .filter(([k]) => k !== "name")
                        .map(([k, v]) => `${k}=${v}`).join("  ")}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* findings — KvRow with emphasis */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>
            findings — <code>KvFragment</code> rows with <code>emphasis</code> + author <code>code/target/state</code> via <code>extra="allow"</code>
          </div>
          <div className="panel" style={{borderColor:"var(--ink)"}}>
            <div className="panel-hd">{findings.hints?.label_text || "Findings"}<span>{findings.content.length} rows</span></div>
            <div className="panel-bd" style={{padding:0}}>
              {findings.content.map((r, i) => {
                const glyph =
                  r.emphasis === "ok"     ? "✓" :
                  r.emphasis === "warn"   ? "!" :
                  r.emphasis === "danger" ? "!!" : "·";
                const color =
                  r.emphasis === "ok"     ? "var(--ok)" :
                  r.emphasis === "warn"   ? "var(--warn)" :
                  r.emphasis === "danger" ? "var(--bad)" : "var(--ink-3)";
                return (
                  <div key={i} style={{
                    display:"grid",
                    gridTemplateColumns:"22px 160px 1fr auto",
                    gap:10, padding:"5px 10px",
                    borderBottom:"1px dotted var(--rule)",
                    fontFamily:"var(--mono)", fontSize:11,
                  }}>
                    <span style={{color, fontWeight:700, textAlign:"center"}}>{glyph}</span>
                    <span style={{color:"var(--ink-3)"}}>{r.key}</span>
                    <span style={{color:"var(--ink)", fontWeight:600}}>{String(r.value)}</span>
                    <span style={{fontSize:9, color:"var(--ink-3)", textTransform:"uppercase", letterSpacing:"0.06em"}}>
                      {r.code} · {r.state}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Mediation + Disposition */}
          <div className="demo-grid-2">
            <div style={{display:"grid", gap:6}}>
              <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>
                mediation moves
              </div>
              <ChoiceList choices={mediation} env={env} onCommit={() => {}} />
            </div>
            <div style={{display:"grid", gap:6}}>
              <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>
                disposition — <code>ui_hints.emphasis</code> primary/warning/danger
              </div>
              <DispositionList choices={dispositions} env={env} />
            </div>
          </div>

          {/* Projected — restrictions + summary */}
          <div className="demo-grid-2" style={{marginTop:4}}>
            <RailSection section={proj.sections.find(s => s.section_id === "restrictions")} />
            <RailSection section={proj.sections.find(s => s.section_id === "shift_time")} />
          </div>
          <RailSection section={proj.sections.find(s => s.section_id === "shift_summary")} />

          <div className="callout" style={{fontSize:11, padding:"8px 10px"}}>
            <b>What this bundle enriches.</b> Every surface is core vocab — <code>kind="candidate"</code>
            pieces, <code>zone_role="packet"</code>, severity through <code>KvRow.emphasis</code>,
            <code>ui_hints.emphasis</code> on disposition choices, <code>Blocker[]</code> referencing
            findings UIDs. The genre layer is naming (packet vs slot) and emphasis convention
            (ok/warn/danger ↔ ✓/!/!!). A client that ignores the genre layer still conforms.
          </div>
        </div>

        <CliPane lines={cliRenderCredentials(fx)} label="credentials · cli reference port" width={46} />
      </div>
    </div>
  );
}

// Dispositions render like normal choices but with stronger color cues.
function DispositionList({ choices, env }) {
  return (
    <div className="choices-v12">
      {choices.map((c, i) => {
        const emph = c.ui_hints?.emphasis || "";
        const border =
          emph === "danger"  ? "var(--bad)" :
          emph === "warning" ? "var(--warn)" :
          emph === "primary" ? "var(--ok)" : "var(--ink)";
        return (
          <button
            key={c.uid}
            type="button"
            disabled={!c.available}
            className={"choice-v12" + (c.available ? "" : " locked")}
            style={{ borderColor: border, borderWidth: 2 }}
          >
            <span className="key">{c.ui_hints?.hotkey || (i + 1)}</span>
            <span className="label">
              {c.text}
              {!c.available && c.unavailable_reason && (
                <span className="reason"> {c.unavailable_reason}</span>
              )}
            </span>
            <span className="meta">
              <span style={{
                fontFamily:"var(--mono)", fontSize:9.5,
                color: border, border: `1px solid ${border}`,
                padding:"0 5px",
                textTransform:"uppercase",
                letterSpacing:"0.06em",
              }}>{emph || "—"}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

// ===========================================================================
// §6.3 Training demo (LLtQ-style)
// ===========================================================================

function TrainingDemo() {
  const fx = window.V15_FIXTURES.training;
  const [phase, setPhase] = useGenState("pre"); // pre | post
  const env  = phase === "pre" ? fx.envelope : fx.post_audience.envelope;
  const proj = phase === "pre" ? fx.projected_state : fx.projected_state;
  const idx  = useGenMemo(() => indexEnvelope(env), [env]);
  const byUid = idx.byUid;

  const stats = proj.sections.find(s => s.section_id === "stats");
  const mood  = proj.sections.find(s => s.section_id === "mood");

  return (
    <div className="panel-card">
      <h3>Tier P3 · training — mood as modulator · scheduled stat_check
        <span className="right">"Coronate the Regent · Week 2"</span>
      </h3>
      <div className="row-flex" style={{gap:6, marginBottom:6}}>
        <div className="seg" style={{display:"flex", border:"1.25px solid var(--ink)"}}>
          {[["pre", "Pre-roll · weekly choice"], ["post", "Post-roll · audience succeeded"]].map(([k, label]) => (
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

      <div className="cli-grid">
        <div style={{display:"grid", gap:10, minWidth:0}}>
          {/* prose */}
          {(findScene(env)?.member_ids || []).map(id => byUid[id]).filter(Boolean)
            .map(f => {
              if (f.fragment_type === "content")
                return <ContentBlock key={f.uid} frag={f} />;
              if (f.fragment_type === "roll")
                return <RollWidget key={f.uid} frag={f} />;
              return null;
            })}

          {phase === "pre" && (
            <div className="demo-grid-2">
              <div style={{display:"grid", gap:8}}>
                {/* Inventory zone */}
                <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>
                  inventory · zone_role=&quot;hand&quot;
                </div>
                <ZoneTile zone={byUid["z-inv"]} env={env} byUid={byUid} />

                {/* Catalog */}
                <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:6}}>
                  merchant · realized=false offers
                </div>
                <CatalogGrid zone={byUid["z-merchant"]} env={env} byUid={byUid}
                  selectedIds={[]} onToggle={() => {}}
                  walletValue={proj.sections.find(s => s.section_id === "wallet")?.value.items[0]?.value} />

                <div className="callout" style={{fontSize:11, padding:"8px 10px"}}>
                  <b>Mood modulates skill gains.</b> The "martial" mood applies <code>+0.5×</code> growth
                  to <code>#martial</code>-tagged choices and <code>-0.5×</code> to <code>#courtly</code>
                  ones — surfaced as <i>backend-computed</i> <code>cost_previews</code> deltas (+2 vs +1).
                  The client just renders what the backend told it. §0.3.
                </div>
              </div>

              <div style={{display:"grid", gap:8}}>
                <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>
                  weekly choices · <code>stat_check</code> preview on the gated option
                </div>
                <ChoiceList choices={env.fragments.filter(f => f.fragment_type === "choice")}
                  env={env} onCommit={() => {}} />
                <RailSection section={mood} />
                <RailSection section={stats} />
                <RailSection section={proj.sections.find(s => s.section_id === "wallet")} />
              </div>
            </div>
          )}

          {phase === "post" && (
            <div className="demo-grid-2">
              <div style={{display:"grid", gap:8}}>
                <div className="callout" style={{fontSize:11, padding:"8px 10px", margin:0}}>
                  <b>Scheduled event = next envelope.</b> The roll fires immediately on commit. Result?
                  <b> impressed_prince</b> badge added via <code>update</code> control fragment. The
                  forking lives on the backend; the client just renders the path it was given. §7.3.
                </div>
                <pre style={{fontFamily:"var(--mono)", fontSize:10.5, background:"var(--paper)", border:"1px solid var(--rule)", padding:"8px", margin:0, overflow:"auto", lineHeight:1.4}}>
{`{
  "fragment_type": "control",
  "ref_type": "section",
  "ref_id": "inventory",
  "payload": {
    "value": {
      "value_type": "badges",
      "items": ["impressed_prince"]
    }
  }
}`}
                </pre>
              </div>
              <div style={{display:"grid", gap:8}}>
                <ChoiceList choices={env.fragments.filter(f => f.fragment_type === "choice")}
                  env={env} onCommit={() => {}} />
                <RailSection section={mood} />
                <RailSection section={stats} />
              </div>
            </div>
          )}
        </div>

        <CliPane lines={cliRenderTraining(fx, phase)} label={`training · ${phase} · cli`} width={46} />
      </div>
    </div>
  );
}

// ===========================================================================
// §6.4 Elefant Hunt demo (board + composite hunt + journal arc)
// ===========================================================================

function ElefantHuntDemo() {
  const fx = window.V15_FIXTURES.elefant_hunt;
  const env = fx.envelope;
  const proj = fx.projected_state;
  const idx  = useGenMemo(() => indexEnvelope(env), [env]);
  const byUid = idx.byUid;

  return (
    <div className="panel-card">
      <h3>Tier P3 · elefant_hunt — graph traversal · composite hunt · journal-as-story
        <span className="right">"at the watering hole"</span>
      </h3>
      <div className="cli-grid">
        <div style={{display:"grid", gap:10, minWidth:0}}>
          {/* prose */}
          {byUid["c-prose"] && <ContentBlock frag={byUid["c-prose"]} />}

          {/* Board map + expedition zone side by side */}
          <div className="demo-grid-2">
            <div style={{display:"grid", gap:8}}>
              <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>
                board · <code>zone_role="board"</code> · location sub-zones with <code>loc_kind</code>
              </div>
              <SandboxMap zone={byUid["z-board"]} env={env} byUid={byUid} />
              <div className="margin-note" style={{fontSize:14}}>
                node glyphs: ⚓ port (scoring) · * hunting ground · ! hazard · ▲ junction · † graveyard
              </div>
            </div>
            <div style={{display:"grid", gap:8}}>
              <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em"}}>
                expedition · hunters + animals + ivory all share <code>PieceFragment</code>
              </div>
              <ZoneTile zone={byUid["z-expedition"]} env={env} byUid={byUid} />
              <RailSection section={proj.sections.find(s => s.section_id === "supplies")} />
              <RailSection section={proj.sections.find(s => s.section_id === "score")} />
            </div>
          </div>

          {/* Composite hunt roll */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:4}}>
            hunt resolution · <code>RollFragment(kind="custom")</code> with structured inputs/outputs
          </div>
          <HuntRollPanel frag={byUid["r-hunt"]} />

          {/* Movement choices */}
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10, textTransform:"uppercase", letterSpacing:"0.08em", marginTop:4}}>
            exits · <code>ui_hints.encounter_check</code> previews on hazardous/junction edges
          </div>
          <ChoiceList choices={env.fragments.filter(f => f.fragment_type === "choice")}
            env={env} onCommit={() => {}} />

          <div className="callout" style={{fontSize:11, padding:"8px 10px"}}>
            <b>The backend animal pool is invisible.</b> The client never sees
            <code> TokenPool</code> composition — only <code>RollFragment.inputs.drawn</code>{" "}
            materializes the animals actually drawn this encounter. Canonical example of §0.3
            backend authority working under pressure. The journal-as-story validation below shows
            the same data path producing legible narrative.
          </div>
        </div>

        <CliPane lines={cliRenderElefantHunt(fx)} label="elefant_hunt · cli" width={46} />
      </div>
    </div>
  );
}

// A specialized hunt-roll panel — composite, not just dice.
function HuntRollPanel({ frag }) {
  if (!frag) return null;
  const inp = frag.inputs || {};
  return (
    <div className="roll" style={{borderWidth:1.5}}>
      <div className="roll-head">
        <span>{frag.label}</span>
        <span className="target">kind: custom · outcome:</span>
        <span className={"roll-outcome " + frag.outcome.replace(/_/g, "_")}
          style={{
            background: frag.outcome.startsWith("crit") ? "var(--ok)"
                      : frag.outcome === "fail" || frag.outcome === "crit_fail" ? "var(--bad)"
                      : "var(--warn)",
            color: "var(--paper)",
            borderColor: "transparent",
          }}>
          {frag.outcome.replace("_", " ")}
        </span>
      </div>
      <div className="demo-grid-3" style={{gap:8}}>
        <div style={{border:"1px solid var(--rule)", padding:"6px 8px", background:"var(--paper-2)"}}>
          <div style={{fontFamily:"var(--mono)", fontSize:9.5, color:"var(--ink-3)", textTransform:"uppercase", letterSpacing:"0.08em"}}>Drawn</div>
          {inp.drawn?.map((d, i) => (
            <div key={i} style={{display:"flex", gap:6, fontFamily:"var(--mono)", fontSize:11}}>
              <span>{d.species}</span>
              <span style={{color:"var(--ink-3)"}}>· {d.point_value} pts</span>
              {d.is_killer && <span style={{color:"var(--bad)"}}>· killer</span>}
            </div>
          ))}
        </div>
        <div style={{border:"1px solid var(--rule)", padding:"6px 8px"}}>
          <div style={{fontFamily:"var(--mono)", fontSize:9.5, color:"var(--ink-3)", textTransform:"uppercase", letterSpacing:"0.08em"}}>Assignments</div>
          {inp.assignments?.map((a, i) => {
            const captured = inp.captures.includes(a.target);
            return (
              <div key={i} style={{display:"grid", gridTemplateColumns:"1fr 1fr auto", gap:6, fontFamily:"var(--mono)", fontSize:11, alignItems:"center"}}>
                <span>{a.hunter}</span>
                <span style={{color:"var(--ink-3)"}}>{a.target}</span>
                <span style={{fontWeight:700, color: captured ? "var(--ok)" : "var(--ink-3)"}}>
                  d6={a.d6} ({a.total})
                </span>
              </div>
            );
          })}
        </div>
        <div style={{border:"1px solid var(--rule)", padding:"6px 8px"}}>
          <div style={{fontFamily:"var(--mono)", fontSize:9.5, color:"var(--ink-3)", textTransform:"uppercase", letterSpacing:"0.08em"}}>Result</div>
          <div style={{fontFamily:"var(--mono)", fontSize:11}}>
            <div><span style={{color:"var(--ok)"}}>captures:</span> {inp.captures?.join(", ") || "—"}</div>
            <div><span style={{color:"var(--ink-3)"}}>escapes:</span> {inp.escapes?.join(", ") || "—"}</div>
            <div><span style={{color:"var(--bad)"}}>casualties:</span> {inp.casualties?.join(", ") || "—"}</div>
          </div>
        </div>
      </div>
      {frag.narrative && (
        <div className="roll-narrative">{frag.narrative}</div>
      )}
    </div>
  );
}

// ===========================================================================
// §5 Journal-as-story (§0.8) — full CLI transcript demonstration
// ===========================================================================

function JournalAsStory() {
  const fx = window.V15_FIXTURES.elefant_hunt;
  return (
    <div className="panel-card">
      <h3>§0.8 · Journal as narrative
        <span className="right">"the story falls out"</span>
      </h3>
      <p style={{maxWidth:900, color:"var(--ink-2)", fontSize:13, lineHeight:1.55, margin:0}}>
        v1.5's load-bearing claim: <i>a contract-correct envelope stream produces a legible narrative
        transcript as a byproduct of traversal — without authored prose beyond per-location flavor.</i>
        Below is the canonical transcript fixture from <code>elefant_hunt</code> — every line is what
        the <code>cli_reference_port.py</code> emits replaying a complete expedition. No separate
        narration layer. Proppian arc (departure → trials → boons → return → recognition) emerges
        from graph topology + fragment ordering. The smoke-test assertion: a human reader recognizes
        it as a story.
      </p>
      <div className="cli-grid" style={{gridTemplateColumns: "1fr 1fr"}}>
        <div style={{display:"grid", gap:10}}>
          <div className="callout" style={{fontSize:11.5, padding:"10px 12px", margin:0}}>
            <b>What this proves.</b>
            <ul style={{margin:"6px 0 0 18px", padding:0, lineHeight:1.6}}>
              <li>Each <code>content</code> fragment is specific enough to be re-readable as prose.</li>
              <li>Outcomes carrying story weight get a populated <code>RollFragment.narrative</code>.</li>
              <li>Recurring NPCs keep stable speaker names so the cast reads cleanly.</li>
              <li><code>update</code>/<code>delete</code> with narratively significant state changes
                  ship a <code>content</code> companion.</li>
            </ul>
          </div>
          <div className="callout" style={{fontSize:11.5, padding:"10px 12px", margin:0, borderStyle:"dashed"}}>
            <b>Per-bundle conformance idiom.</b> The conformance suite ships one
            "transcript reads as story" smoke test per genre. Test: render a complete session
            through the CLI port; assert the transcript is non-trivial and contains the bundle's
            key narrative events. v1.5 does not gate envelope conformance on this — it's a
            <i> bundle-authoring discipline</i>, not a contract enforcement rule.
          </div>
          <pre style={{fontFamily:"var(--mono)", fontSize:10.5, background:"var(--paper)", border:"1px solid var(--rule)", padding:"8px 10px", margin:0, lineHeight:1.5}}>
{`// engine/contrib/conformance/transcripts/
//   elefant_hunt_one_expedition.txt
//
// Regenerated on each bundle revision via:
//   python -m engine.contrib.conformance \\
//          --bundle elefant_hunt \\
//          --transcript-out <path>
//
// Reviewers read it as prose. Diffs flag drift.`}
          </pre>
        </div>

        <CliPane lines={fx.journal_transcript} label="elefant_hunt · journal transcript" width={50} />
      </div>
    </div>
  );
}

// ===========================================================================
// §4 Capability deep-dives — cursors, info channels, time/input parity
// ===========================================================================

function CapabilityCards() {
  const cards = [
    {
      h: "Cursors & channels",
      tier: "P1",
      body: (
        <>
          <p>Each cursor has its own journal channel; envelopes are per-channel. <code>cursor_id</code>{" "}
          identifies which; <code>step</code> is monotonic per channel.</p>
          <p>Shared world state is <i>projected per-cursor</i>: one canonical backend object,
          per-cursor envelopes, control fragments propagate updates.</p>
          <p><b>Single-cursor is the floor case.</b> Every demo here uses one channel.
          Multi-cursor sessions render N channels independently; the contract makes no commitment
          about turn ordering or simultaneous input — bundle concerns.</p>
          <div className="margin-note" style={{fontSize:13.5, marginTop:6}}>
            <code>visibility</code> accepts <code>"public"</code> / <code>"owner_only"</code> /
            <code> list[ParticipantId]</code> — interpreted against the channel's owner.
          </div>
        </>
      ),
    },
    {
      h: "Info channels",
      tier: "P1",
      body: (
        <>
          <p>Advisory side-projections of world state — map, inventory, watch, character sheet,
            objectives. Each is queryable on demand via <code>metadata.info_affordances[]</code>{" "}
            with an opaque <code>query</code> descriptor.</p>
          <p><b>Discovery hints, not mandatory UI.</b> Web renders pills; CLI floor uses slash commands
            from <code>shortcuts[]</code> + a <code>?</code> menu. Hidden state never crosses the wire.</p>
          <p><code>info_state.dirty_kinds</code> tells the client what's stale;{" "}
            <code>info_state.version</code> is monotonic per cursor.</p>
        </>
      ),
    },
    {
      h: "Time parity",
      tier: "S",
      body: (
        <>
          <p>Every visual ritual must be skippable to canonical-instant in <b>one</b> user action.
            Audio / video advanceable similarly.</p>
          <p>Pacing belongs in fragment boundaries, not in elapsed time.{" "}
            <code>ritual_hints.duration_ms</code> /{" "}
            <code>auto_skip_after_seen</code> /{" "}
            <code>allow_replay</code> are the only knobs.</p>
        </>
      ),
    },
    {
      h: "Input parity",
      tier: "S",
      body: (
        <>
          <p>Every richer modality (drag, gesture, hotkey) MUST have a click-pick / typed-text
            equivalent reachable in the same turn. CLI defines the input floor.</p>
          <p><code>ui_hints.drag</code> is presentation enhancement of an <code>accepts.kind="place"</code>
            choice; the CLI commit payload is identical to the click-pick path.</p>
        </>
      ),
    },
  ];
  return (
    <div className="demo-grid-2">
      {cards.map((c, i) => (
        <div key={i} className="spec-card" style={{background:"#fff", border:"1.5px solid var(--rule-strong)", padding:"12px 14px", display:"grid", gap:6}}>
          <h4 style={{margin:0, fontFamily:"var(--mono)", fontSize:11, letterSpacing:"0.08em", textTransform:"uppercase", color:"var(--ink-2)", display:"flex", alignItems:"center", gap:8}}>
            {c.h}
            <span className={"tier tier-" + c.tier.toLowerCase()}>{c.tier}</span>
          </h4>
          <div style={{fontSize:12.5, lineHeight:1.5, color:"var(--ink-2)"}}>{c.body}</div>
        </div>
      ))}
    </div>
  );
}

// ===========================================================================
// Genre index card (§0.9 from the spec, rendered)
// ===========================================================================

function GenreIndex() {
  const rows = [
    { id: "carwars",       what: "Vehicle outfitting", stress: "slot zones · capacity · stat_check preview · drag with click-pick parity",
      jumpTo: "#sec-carwars" },
    { id: "credentials",   what: "Inspection / verification", stress: "packet zones · severity-coded findings · disposition emphasis · gated dispositions",
      jumpTo: "#sec-credentials" },
    { id: "training",      what: "Scheduled skill progression", stress: "mood as growth modulator · scheduled stat_check · inventory unlocks · weekly compose",
      jumpTo: "#sec-training" },
    { id: "elefant_hunt",  what: "Graph-traversal sandbox", stress: "board with location sub-zones · backend-private pool mechanic · composite hunt roll · journal-as-story",
      jumpTo: "#sec-elefant-hunt" },
    { id: "hana_smuta",    what: "Card play (sketch)", stress: "pieces constraints · hand/field/pile/score zones · same_property selection",
      jumpTo: null },
  ];
  return (
    <table className="parity-table" style={{marginBottom:6}}>
      <thead><tr>
        <th>Bundle</th><th>Genre</th><th>What it stresses</th><th>Jump</th>
      </tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td className="w"><code>{r.id}</code></td>
            <td>{r.what}</td>
            <td>{r.stress}</td>
            <td>
              {r.jumpTo
                ? <a href={r.jumpTo} style={{fontFamily:"var(--mono)", fontSize:10.5, color:"var(--blue-pencil)"}}>↓ section</a>
                : <span className="muted" style={{fontFamily:"var(--mono)", fontSize:10}}>TBD</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

Object.assign(window, {
  CredentialsDemo, TrainingDemo, ElefantHuntDemo,
  JournalAsStory, CapabilityCards, GenreIndex,
  HuntRollPanel, DispositionList,
  cliRenderCredentials, cliRenderTraining, cliRenderElefantHunt,
});
