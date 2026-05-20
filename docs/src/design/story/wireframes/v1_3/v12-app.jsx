// v12-app.jsx — composes the StoryTangl UI 1.3 wireframe document.
//
// v1.3 spec sync (May 2026). The published v1.3 vocab makes targeted edits
// against the v1.2 draft this artifact was built against, none of which
// require redesigning the visual treatment — only relabelling and rewiring:
//
//   1. Reverted accepts.kind "select" → "pieces" (the v1.2 draft's rename
//      proposal was rejected in v1.2.1 review; repo convention `pieces` is
//      preserved, mirrors piece_ids payload + PieceFragment). All four
//      garage/manor accepts choices, the §3 cheatsheet, §8 parity table,
//      garage section header, and the CLI dispatch suffix were updated.
//   2. Demoted §1.5 (cursors/channels) and §1.6 (info channels) from S to P1.
//      The framings remain; only the tier tags moved. §7 header + per-cursor
//      callout now display tier-p1 badges.
//   3. Replaced the proposed `GET /story/info/{kind}` endpoint with the
//      hand-it-back InfoAffordance.query: dict | None descriptor model. The
//      manor fixture's info_affordances now carry `query` payloads (or null
//      for help). The SandboxDemo callout describes the descriptor semantic.
//   4. §0 changelog now leads with §0.7 three-layer architecture (L1 vocab
//      / L2 API / L3 engine), the §1.5+§1.6 tier demotion, the
//      `query`-descriptor replacement, and a clarifying note that owner /
//      position / edge_ref / audience visibility are **proposal fixtures**
//      awaiting bundle MVP authors — not gating fixtures for current
//      conformance.
//   5. The Patch E carry-overs (owner, position, edges-with-uids,
//      RouteBuildingDemo) all stay — they are the proposal fixtures the
//      spec references, now correctly labelled as such.
//
// Sections by spec ordering:
//   §0  Tier overview + 4-rule conformance stool + v1.3 changelog
//   §1  Fragment × widget × shell matrix
//   §2  Triptych: same envelope rendered in Scroll / Dossier / Stage+Log
//   §3  Choice accepts.kind cheatsheet
//   §4  Tier P2 worked example: pieces, zones, slots, catalog (garage)
//   §5  Tier P2: RollFragment + ritual + stat_check (gravel)
//   §6  Tier P1: raw_command + InterpretationFragment (command bar)
//   §7  Sandbox conventions (manor): info bar, world_time, agenda, map, provenance
//   §8  Port parity table
//   §9  Author / debug notes + next steps

const { useState: useAppState, useEffect: useAppEffect } = React;

// ---------- TWEAKS panel ----------
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "tript_fixture": "crossroads",
  "show_print_link": true,
  "show_source_badges": true,
  "compact_dossier_rail": false
}/*EDITMODE-END*/;

function TweaksPanel({ tweaks, setTweak, onClose }) {
  return (
    <div className="tweaks on">
      <div className="tw-hd">
        Tweaks
        <button className="ghost-btn" onClick={onClose}>×</button>
      </div>
      <div className="tw-bd">
        <label>Triptych fixture</label>
        <div className="seg">
          {[["crossroads","Crossroads"], ["garage","Garage"], ["manor","Manor"]].map(([k, label]) => (
            <button key={k} className={tweaks.tript_fixture === k ? "on" : ""}
              onClick={() => setTweak("tript_fixture", k)}>{label}</button>
          ))}
        </div>

        <div className="toggle-row">
          <span>Show <code>source_kind</code> badge on choices</span>
          <button className="ghost-btn"
            onClick={() => setTweak("show_source_badges", !tweaks.show_source_badges)}>
            {tweaks.show_source_badges ? "ON" : "off"}
          </button>
        </div>

        <div className="toggle-row">
          <span>Compact dossier rail</span>
          <button className="ghost-btn"
            onClick={() => setTweak("compact_dossier_rail", !tweaks.compact_dossier_rail)}>
            {tweaks.compact_dossier_rail ? "ON" : "off"}
          </button>
        </div>

        <div style={{fontSize:9.5, color:"var(--ink-3)", marginTop:6, lineHeight:1.4}}>
          v1.3 prototype · all tweaks persist via the host's edit-mode bridge.
        </div>
      </div>
    </div>
  );
}

function useTweaks(defaults) {
  const [t, setT] = useAppState(defaults);
  const setTweak = (k, v) => {
    setT(prev => {
      const next = typeof k === "object" ? {...prev, ...k} : {...prev, [k]: v};
      try {
        window.parent.postMessage({type: "__edit_mode_set_keys", edits: next}, "*");
      } catch (e) {}
      return next;
    });
  };
  return [t, setTweak];
}

// ---------- App ----------
function App() {
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tweaksOpen, setTweaksOpen] = useAppState(false);

  useAppEffect(() => {
    function handle(e) {
      const m = e.data;
      if (!m || typeof m !== "object") return;
      if (m.type === "__activate_edit_mode") setTweaksOpen(true);
      if (m.type === "__deactivate_edit_mode") setTweaksOpen(false);
    }
    window.addEventListener("message", handle);
    try { window.parent.postMessage({type: "__edit_mode_available"}, "*"); } catch (e) {}
    return () => window.removeEventListener("message", handle);
  }, []);

  // pick the fixture used by the triptych
  const tript =
    tweaks.tript_fixture === "garage" ? window.V12_FIXTURES.garage :
    tweaks.tript_fixture === "manor"  ? window.V12_FIXTURES.manor  :
    window.V12_FIXTURES.crossroads;

  return (
    <div className="paper">

      {/* Top rail */}
      <div className="rail">
        <div className="brand"><b>StoryTangl</b> · wireframes v1.3</div>
        <div className="sep"></div>
        <div className="doc-meta">vocab integration · {new Date().toISOString().slice(0,10)}</div>
        <div className="spacer"></div>
        <div className="tabs">
          <a className="tab" href="StoryTangl Wireframes v2.html" style={{textDecoration:"none", color:"inherit"}}>← v2</a>
          <a className="tab" href="StoryTangl Themes.html" style={{textDecoration:"none", color:"inherit"}}>themes →</a>
        </div>
      </div>

      <div style={{maxWidth:1320, margin:"0 auto", padding:"24px 28px 80px"}}>

        {/* ===== Header banner ===== */}
        <div className="v12-banner">
          <span className="v12-ver">v1.3</span>
          <h1>Vocabulary, integrated.</h1>
          <span className="v12-bnote">tracks the v1.3 published spec</span>
        </div>

        <p className="v12-intro">
          Reconciles the <b>published v1.3 spec</b>, the carwars Tier P3 extensions, and the v1.3 sandbox
          info-channel conventions into a single document. v1.3 against v1.2: the
          <code>tokens → pieces</code> rename (the v1.2 draft's <code>"select"</code> proposal was
          reverted to repo convention), <code>§1.5</code>/<code>§1.6</code> demoted from Tier S to Tier P1,
          the <code>InfoAffordance.query</code> opaque descriptor replacing the proposed
          <code>/story/info/&#123;kind&#125;</code> endpoint, and §0.7 three-layer architecture
          (UI vocab · API transport · engine) added — per-surface implementation status now lives in
          <code>WIDGET_CONTRACT_RECONCILIATION.md</code>, not this spec. Wireframes below all consume one of
          three canonical fixtures (<code>crossroads</code>, <code>garage</code>, <code>manor</code>)
          and one ritual fixture (<code>gravel</code>); each demo ships a CLI-port pane alongside the rich
          web rendering so the §5 parity contracts are legible inside the artifact itself.
        </p>

        <TierLegend />
        <ParityStool />

        <h2 className="section-h2 has-tier">
          <span className="num">§0</span> v1.3 spec sync — what changed
          <span className="tier tier-s">S</span>
          <small>name reverts · tier demotions · §0.7 layers</small>
        </h2>
        <V12Changes />

        {/* ===== §1 — Matrix ===== */}
        <h2 className="section-h2 has-tier">
          <span className="num">§1</span> Fragment × widget × shell
          <span className="tier tier-s">S</span><span className="tier tier-p1">P1</span><span className="tier tier-p2">P2</span>
          <small>one row per fragment_type / value_type</small>
        </h2>
        <FragmentMatrix />
        <div className="callout">
          <b>Rule of thumb.</b> The shell chooses <i>where</i> a widget lives, not <i>whether</i> it renders.
          A client that doesn't recognize a fragment type MUST render the parity-table text fallback —
          never silently drop. <code>control</code> fragments cite UIDs and later turns assume those UIDs still resolve.
        </div>
        <div className="callout" style={{borderStyle:"dashed"}}>
          <b>One cursor, one channel.</b> §1.5 <span className="tier tier-p1">P1</span> — committed target contract,
          single-cursor today at the engine layer. Envelopes are per-cursor: <code>cursor_id</code> identifies the
          journal channel and <code>step</code> is monotonic within it. Every demo in this document shows a
          single channel for solo play. Multi-cursor sessions (Discord-style shared reading, head-to-head
          gamebooks, asymmetric coop) render N channels independently; the contract makes no commitment
          about turn ordering or simultaneous input — those are bundle concerns. <code>visibility="owner_only"</code>
          and <code>visibility=[participant_ids]</code> are interpreted against each channel's owner.
        </div>

        {/* ===== §2 — Triptych ===== */}
        <h2 className="section-h2 has-tier">
          <span className="num">§2</span> Same envelope, three shells
          <span className="tier tier-s">S</span>
          <small>switch the fixture via the Tweaks panel</small>
        </h2>
        <p style={{maxWidth:900, color:"var(--ink-2)", fontSize:13, lineHeight:1.55, marginTop:0}}>
          All three panels below read the <i>same</i> <code>window.V12_FIXTURES.{tweaks.tript_fixture}</code>.
          The only thing that differs is how each shell maps the fragment stream onto screen geometry.
        </p>
        <div className="triptych">
          <div className="shell-frame">
            <div className="shell-head"><span className="name">Scroll</span><span className="kind">journal · linear</span></div>
            <div className="shell-body"><ScrollShell envelope={tript.envelope} onPick={() => {}} onCommand={() => {}} /></div>
          </div>
          <div className="shell-frame">
            <div className="shell-head"><span className="name">Dossier</span><span className="kind">stage + projected rail</span></div>
            <div className="shell-body"><DossierShell envelope={tript.envelope} projected={tript.projected_state} onPick={() => {}} onCommand={() => {}} /></div>
          </div>
          <div className="shell-frame">
            <div className="shell-head"><span className="name">Stage + Log</span><span className="kind">VN-ish + fragment tape</span></div>
            <div className="shell-body"><StageLogShell envelope={tript.envelope} onPick={() => {}} /></div>
          </div>
        </div>
        <div className="callout">
          <b>What each shell decides.</b> <i>Scroll</i> treats the scene group as a chapter and the kv fragment as
          inline chrome. <i>Dossier</i> routes all projected sections to the right rail and keeps in-stream kv inline
          with the prose. <i>Stage+Log</i> elevates the most recent attributed fragment to a caption and renders
          every fragment as a row on the tape — useful for replay and debugging.
        </div>

        {/* ===== §3 — accepts.kind cheatsheet ===== */}
        <h2 className="section-h2 has-tier">
          <span className="num">§3</span> Choice <code>accepts.kind</code> cheatsheet
          <span className="tier tier-s">S</span><span className="tier tier-p1">P1</span>
          <small>the seven typed payload shapes</small>
        </h2>
        <AcceptsKindCheatsheet />
        <div className="callout">
          The wire payload is <b>shape-keyed by the choice's <code>accepts.kind</code></b>, not by a
          discriminator on the payload itself. Backend looks up the open choice by <code>edge_id</code>
          and validates accordingly. Non-backend validators (length, regex, enum) are advisory; the
          backend re-evaluates and surfaces failures as
          <code>InterpretationFragment</code> with <code>result="validation_failed"</code>.
        </div>

        {/* ===== §4 — Pieces / zones / slots / catalog ===== */}
        <h2 className="section-h2 has-tier">
          <span className="num">§4</span> Interactive surfaces — pieces, zones, slots, catalogs
          <span className="tier tier-p2">P2</span><span className="tier tier-p3">P3 conventions</span>
          <small>place / pieces / drag with click-pick floor</small>
        </h2>
        <GarageDemo />

        {/* ===== §5 — RollFragment ===== */}
        <h2 className="section-h2 has-tier">
          <span className="num">§5</span> RollFragment + ritual
          <span className="tier tier-p2">P2</span>
          <small>structured outcome, skippable ritual</small>
        </h2>
        <RollDemo />

        {/* ===== §6 — Command bar + interpretation ===== */}
        <h2 className="section-h2 has-tier">
          <span className="num">§6</span> Command bar + InterpretationFragment
          <span className="tier tier-p1">P1</span>
          <small>raw_command, grammar hint, parser fallback</small>
        </h2>
        <CommandDemo />

        {/* ===== §7 — Sandbox conventions ===== */}
        <h2 className="section-h2 has-tier">
          <span className="num">§7</span> Sandbox conventions — info channel
          <span className="tier tier-p1">P1</span><span className="tier tier-p2">P2</span>
          <small>v1.3: §1.6 is target-truth at L1; engine/transport catching up</small>
        </h2>
        <p style={{maxWidth:900, color:"var(--ink-2)", fontSize:13, lineHeight:1.55, marginTop:0, marginBottom:10}}>
          The sandbox handoff is realized entirely through existing surfaces:{" "}
          <code>ProjectedState.sections</code> tagged with conventional <code>kind</code>s
          (<code>world_time</code>, <code>location</code>, <code>agenda</code>, <code>objectives</code>),{" "}
          <code>metadata.info_affordances</code> for non-story commands like <i>map / inventory / time</i>,
          and <code>ui_hints.source / contribution / time_delta</code> for choice provenance.
          No new <code>value_type</code>s, no second story runtime. Per v1.3, each affordance carries an
          opaque <code>query</code> descriptor (or <code>null</code>) the backend interprets — transport
          routing is a backend concern, not vocabulary.
        </p>
        <SandboxDemo />

        {/* ===== §8 — Port parity ===== */}
        <h2 className="section-h2 has-tier">
          <span className="num">§8</span> Port parity — same vocabulary, four media
          <span className="tier tier-s">S</span>
          <small>CLI is the floor, not the ceiling</small>
        </h2>
        <ParityTable12 />
        <div className="callout">
          <b>Bespoke per-world clients.</b> The vocabulary contract means a custom client can <i>add</i> widgets
          (battle-map, dice tray, faction tracker) without breaking the core stream — it opts in to render
          specific <code>zone_role</code> or <code>ui_hints.widget</code> values, and falls through to the
          parity row for everything else. Bundles MAY declare a <code>profiles[]</code> set; clients implementing
          a strict subset are still conforming for any bundle whose profiles are a subset of theirs.
        </div>

        {/* ===== §9 — Author notes + next steps ===== */}
        <h2 className="section-h2 has-tier">
          <span className="num">§9</span> Author / debug · what's next
          <span className="tier tier-p2">P2</span>
        </h2>
        <div className="spec-grid">
          <div className="spec-card">
            <h4>This envelope, in numbers <span className="frag-tag">debug</span></h4>
            <div className="spec-body">
              <pre style={{fontFamily:"var(--mono)", fontSize:10.5, margin:0, color:"var(--ink-2)", lineHeight:1.55}}>
{`fixture: ${tweaks.tript_fixture}
step:    ${tript.envelope.step}
cursor:  ${(tript.envelope.cursor_id || "—").slice(0, 18)}…
frags:   ${tript.envelope.fragments.length}
choices: ${tript.envelope.fragments.filter(f => f.fragment_type === "choice").length}
pieces:  ${tript.envelope.fragments.filter(f => f.fragment_type === "piece").length}
zones:   ${tript.envelope.fragments.filter(f => f.fragment_type === "group" && f.group_type === "zone").length}
sections:${tript.projected_state?.sections?.length || 0}`}
              </pre>
            </div>
          </div>
          <div className="spec-card">
            <h4>v1.3 conformance gates <span className="frag-tag">policy</span></h4>
            <div className="spec-body" style={{fontSize:12, lineHeight:1.5}}>
              <ol style={{paddingLeft:18, margin:0}}>
                <li>CLI Floor — every Tier S widget renders in <code>cli_reference_port.py</code>.</li>
                <li>Decision Legibility — open-choice referenced UIDs are on-screen.</li>
                <li>Time Parity — visual ritual skippable to canonical-instant.</li>
                <li>Input Parity — every richer modality has a click-pick / typed-text fallback.</li>
              </ol>
              <p style={{margin:"8px 0 0", color:"var(--ink-3)", fontSize:11}}>
                v1.3: §1.5 + §1.6 are Tier P1 — they don't graduate to S until they ship a CLI reference port.
              </p>
            </div>
          </div>
          <div className="spec-card">
            <h4>Deferred to v1.3+ <span className="frag-tag">P3+</span></h4>
            <div className="spec-body" style={{fontSize:12, lineHeight:1.5}}>
              <ul style={{paddingLeft:18, margin:0}}>
                <li>Multi-actor <code>CombatReport</code> fragment (round summary). Tier P3.</li>
                <li>Predicate-registration protocol so <code>predicate_ref</code> becomes typed. Pending.</li>
                <li><code>layered_media</code> — filmstrip / svg-layer / mask. Mentioned in handoff; gated on CLI floor (each layer must degrade to a single image).</li>
                <li>Bidding / area-control mechanisms — depend on registered predicates.</li>
              </ul>
            </div>
          </div>
          <div className="spec-card">
            <h4>Where to read more <span className="frag-tag">docs</span></h4>
            <div className="spec-body" style={{fontSize:12, lineHeight:1.5}}>
              <ul style={{paddingLeft:18, margin:0}}>
                <li><code>docs/STORYTANGL_WIDGET_VOCAB.md</code> · v1.1 main spec.</li>
                <li><code>docs/EXTENSIONS.md</code> · carwars Tier P3 extensions.</li>
                <li><code>docs/SANDBOX_NAV_HANDOFF.md</code> · sandbox info-channel handoff.</li>
              </ul>
            </div>
          </div>
        </div>

        {/* End mark */}
        <div style={{marginTop:48, fontFamily:"var(--mono)", fontSize:10.5, color:"var(--ink-3)"}}>
          ── end · v1.3 wireframes · all examples consume real envelope+projected_state shapes from{" "}
          <code>v12-fixtures.js</code>. Widgets in <code>v12-widgets.jsx</code>; shells in{" "}
          <code>v12-shells.jsx</code>; sections in <code>v12-sections.jsx</code>.
        </div>
      </div>

      {tweaksOpen && <TweaksPanel tweaks={tweaks} setTweak={setTweak} onClose={() => {
        setTweaksOpen(false);
        try { window.parent.postMessage({type:"__edit_mode_dismissed"}, "*"); } catch(e){}
      }} />}
    </div>
  );
}

const rootEl = document.getElementById("root");
ReactDOM.createRoot(rootEl).render(<App />);
