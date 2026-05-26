// v15-app.jsx — composes the StoryTangl UI 1.5 wireframe document.
//
// v1.5 spec sync (May 2026). Changes from v1.3 → v1.5 are additive, all
// captured in V15Changes() and the new sections below. The biggest deltas:
//
//   1. §0.8 "Journal as narrative" — promoted to a load-bearing principle.
//      A v1.5-conforming envelope stream produces a legible narrative
//      transcript as a byproduct of traversal, with no separate narration
//      layer. Worked proof-of-concept: bundle/elefant_hunt. Demonstrated
//      below as §5 (Journal as story).
//
//   2. §0.9 "Genre extensions index" — short pointer table to all
//      bundles/<name>/EXTENSIONS.md docs. The current set is four:
//      carwars / credentials / training / elefant_hunt. Each genre has a
//      worked demo below (§6.1–§6.4), pairing rich rendering with the
//      CLI floor.
//
//   3. §1.5 per-cursor projection of shared world state — codified
//      explicitly. Single-cursor remains the floor; multi-cursor is a
//      parallelizable extension that doesn't reshape §§2–4. Discussed in
//      the Capabilities cards (§4).
//
//   4. Typed Accepts / UIHints implementation status updated — those
//      surfaces are implemented in the engine; Blocker /
//      InterpretationFragment / full info-channel typing remain pending.
//
//   5. Place payloads now carry source_zone_ref when the client selected
//      from a visible source zone (clarification, not a contract break).
//
// Document order:
//   §0  Tier overview + 4-rule conformance stool + v1.5 changelog
//   §1  Fragment × widget × shell × CLI matrix (CLI floor column new)
//   §2  Triptych: same envelope rendered in Scroll / Dossier / Stage+Log
//   §3  Choice accepts.kind cheatsheet
//   §4  Capabilities (cursors, info channels, time parity, input parity)
//   §5  Journal as story (§0.8 demo)
//   §6  Genre extensions:
//        §6.1 carwars      (existing garage demo)
//        §6.2 credentials  (new)
//        §6.3 training     (new)
//        §6.4 elefant_hunt (new)
//   §7  Tier P2 worked examples (RollFragment + ritual; command + interp)
//   §8  Sandbox conventions
//   §9  Port parity table
//   §10 Author / debug notes

const { useState: useAppState, useEffect: useAppEffect } = React;

// Merge V15_FIXTURES_CORE + V15_FIXTURES_GENRES into a single V15_FIXTURES.
window.V15_FIXTURES = Object.assign({},
  window.V15_FIXTURES_CORE || {},
  window.V15_FIXTURES_GENRES || {});

// ---------- TWEAKS panel ----------
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "tript_fixture": "crossroads",
  "show_source_badges": true,
  "compact_dossier_rail": false,
  "show_capability_cards": true
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

        <div className="toggle-row">
          <span>Show §4 capability cards</span>
          <button className="ghost-btn"
            onClick={() => setTweak("show_capability_cards", !tweaks.show_capability_cards)}>
            {tweaks.show_capability_cards ? "ON" : "off"}
          </button>
        </div>

        <div style={{fontSize:9.5, color:"var(--ink-3)", marginTop:6, lineHeight:1.4}}>
          v1.5 wireframes · tweaks persist via the host's edit-mode bridge.
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

  const tript =
    tweaks.tript_fixture === "garage" ? window.V15_FIXTURES.garage :
    tweaks.tript_fixture === "manor"  ? window.V15_FIXTURES.manor  :
    window.V15_FIXTURES.crossroads;

  return (
    <div className="paper">

      {/* Top rail */}
      <div className="rail">
        <div className="brand"><b>StoryTangl</b> · wireframes v1.5</div>
        <div className="sep"></div>
        <div className="doc-meta">vocab integration · {new Date().toISOString().slice(0,10)}</div>
        <div className="spacer"></div>
        <div className="tabs">
          <a className="tab" href="#sec-matrix" style={{textDecoration:"none", color:"inherit"}}>§ matrix</a>
          <a className="tab" href="#sec-genres" style={{textDecoration:"none", color:"inherit"}}>§ genres</a>
        </div>
      </div>

      <div style={{maxWidth:1320, margin:"0 auto", padding:"24px 28px 80px"}}>

        {/* ===== Header banner ===== */}
        <div className="v12-banner">
          <span className="v12-ver">v1.5</span>
          <h1>Vocabulary across shell, genre, and CLI floor.</h1>
          <span className="v12-bnote">supersedes v1.4 · journal-as-story now load-bearing</span>
        </div>

        <p className="v12-intro" data-screen-label="00 Intro">
          Every core fragment, widget, and value_type rendered against three shells
          (<i>Scroll · Dossier · Stage+Log</i>) <b>and</b> the CLI floor that every richer port must
          clear. Tier P3 genre extensions show up downstream as <i>configurations</i> and
          <i> enrichments</i> of the same core — no new fragment types, no new value_types. Each
          of the four published bundles (<code>carwars</code>, <code>credentials</code>,
          <code>training</code>, <code>elefant_hunt</code>) gets a worked demo paired with the
          CLI rendering it would produce. The <code>elefant_hunt</code> bundle doubles as the
          worked proof of v1.5's load-bearing claim: <i>envelope streams produce legible
          narrative transcripts as a byproduct of traversal</i> (§0.8).
        </p>

        <TierLegend />
        <ParityStool />

        {/* ===== §0 — Changelog ===== */}
        <h2 className="section-h2 has-tier" data-screen-label="00 Changelog">
          <span className="num">§0</span> v1.5 spec sync — what changed
          <span className="tier tier-s">S</span>
          <small>journal-as-story · genre index · per-cursor projection</small>
        </h2>
        <V15Changes />

        {/* ===== §1 — Matrix with CLI floor column ===== */}
        <h2 className="section-h2 has-tier" id="sec-matrix" data-screen-label="01 Matrix">
          <span className="num">§1</span> Fragment × widget × shell — and CLI floor
          <span className="tier tier-s">S</span><span className="tier tier-p1">P1</span><span className="tier tier-p2">P2</span>
          <small>one row per fragment_type / value_type · CLI column is the floor</small>
        </h2>
        <FragmentMatrix />
        <div className="callout">
          <b>The CLI column is the load-bearing column.</b> Every richer rendering on the left
          must remain expressible as the column on the right. If a Tier S / P1 / P2 widget can't
          be drawn cleanly in <code>cli_reference_port.py</code>, it isn't vocabulary — it's a
          renderer flourish (§0.2 CLI Floor Rule). Drag, animation, hover preview, watch tile —
          all valid; all sit on top of the floor.
        </div>
        <div className="callout" style={{borderStyle:"dashed"}}>
          <b>One cursor, one channel.</b> §1.5 <span className="tier tier-p1">P1</span> —
          committed target contract, single-cursor today at the engine layer. Envelopes are
          per-cursor (<code>cursor_id</code> identifies the journal channel,{" "}
          <code>step</code> is monotonic within it). Every demo in this document shows one
          channel for solo play; the per-cursor projection recipe in §1.5 governs how shared
          world state propagates when N channels are live.
        </div>

        {/* ===== §2 — Triptych ===== */}
        <h2 className="section-h2 has-tier" id="sec-triptych" data-screen-label="02 Triptych">
          <span className="num">§2</span> Same envelope, three shells, one CLI floor
          <span className="tier tier-s">S</span>
          <small>switch the fixture via the Tweaks panel</small>
        </h2>
        <p style={{maxWidth:900, color:"var(--ink-2)", fontSize:13, lineHeight:1.55, marginTop:0}}>
          All four panels below read the same <code>V15_FIXTURES.{tweaks.tript_fixture}</code>{" "}
          envelope. The three rich shells differ only in how they map the fragment stream onto
          screen geometry. The CLI pane on the right is what <code>cli_reference_port.py</code>{" "}
          emits for the same envelope — the floor every richer port must clear.
        </p>
        <div className="triptych" style={{display:"grid", gridTemplateColumns:"1fr 1fr 1fr 1fr", gap:14}}>
          <div className="shell-frame" data-screen-label="02 Scroll">
            <div className="shell-head"><span className="name">Scroll</span><span className="kind">journal · linear</span></div>
            <div className="shell-body" style={{height:520, overflow:"hidden"}}>
              <ScrollShell envelope={tript.envelope} onPick={() => {}} onCommand={() => {}} />
            </div>
          </div>
          <div className="shell-frame" data-screen-label="02 Dossier">
            <div className="shell-head"><span className="name">Dossier</span><span className="kind">stage + projected rail</span></div>
            <div className="shell-body" style={{height:520, overflow:"hidden"}}>
              <DossierShell envelope={tript.envelope} projected={tript.projected_state} onPick={() => {}} onCommand={() => {}} />
            </div>
          </div>
          <div className="shell-frame" data-screen-label="02 StageLog">
            <div className="shell-head"><span className="name">Stage + Log</span><span className="kind">VN-ish + fragment tape</span></div>
            <div className="shell-body" style={{height:520, overflow:"hidden"}}>
              <StageLogShell envelope={tript.envelope} onPick={() => {}} />
            </div>
          </div>
          <div className="shell-frame" data-screen-label="02 CLI">
            <div className="shell-head"><span className="name">CLI floor</span><span className="kind">cli_reference_port.py</span></div>
            <div className="shell-body" style={{height:520, overflow:"hidden", padding:0}}>
              <CliPane
                lines={
                  tweaks.tript_fixture === "garage"
                    ? cliRenderGarage(window.V15_FIXTURES.garage)
                    : tweaks.tript_fixture === "manor"
                      ? cliRenderSandbox(window.V15_FIXTURES.manor)
                      : cliRenderCrossroads(window.V15_FIXTURES.crossroads)
                }
                label={tweaks.tript_fixture + " · cli"}
                width={44}
              />
            </div>
          </div>
        </div>
        <div className="callout">
          <b>What each shell decides.</b> <i>Scroll</i> treats the scene group as a chapter and
          the kv fragment as inline chrome. <i>Dossier</i> routes all projected sections to the
          right rail and keeps in-stream kv inline with the prose. <i>Stage+Log</i> elevates the
          most recent <code>attributed</code> fragment to a caption and renders every fragment as
          a row on the tape. <i>CLI floor</i> wraps to ~44 columns, numbered choices, no
          animation, no info-pill bar — the parity reference.
        </div>

        {/* ===== §3 — accepts.kind cheatsheet ===== */}
        <h2 className="section-h2 has-tier" data-screen-label="03 Accepts">
          <span className="num">§3</span> Choice <code>accepts.kind</code> cheatsheet
          <span className="tier tier-s">S</span><span className="tier tier-p1">P1</span>
          <small>seven typed payload shapes</small>
        </h2>
        <AcceptsKindCheatsheet />
        <div className="callout">
          The wire payload is <b>shape-keyed by the choice's <code>accepts.kind</code></b>,
          not by a discriminator on the payload itself. Backend looks up the open choice by
          <code> edge_id</code> and validates accordingly. Non-backend validators (length, regex,
          enum) are advisory; the backend re-evaluates and surfaces failures as
          <code> InterpretationFragment</code> with <code>result="validation_failed"</code>.
          v1.5 clarifies that <code>place</code> payloads carry <code>source_zone_ref</code>{" "}
          when the client selected from a visible source zone.
        </div>

        {/* ===== §4 — Capabilities (cursors, info channels, parity) ===== */}
        <h2 className="section-h2 has-tier" id="sec-capabilities" data-screen-label="04 Capabilities">
          <span className="num">§4</span> Capabilities — what richer ports may exceed, never below
          <span className="tier tier-s">S</span><span className="tier tier-p1">P1</span>
          <small>per-cursor projection · info channels · time + input parity</small>
        </h2>
        {tweaks.show_capability_cards && <CapabilityCards />}

        {/* ===== §5 — Journal as story ===== */}
        <h2 className="section-h2 has-tier" id="sec-journal" data-screen-label="05 Journal">
          <span className="num">§5</span> Journal as narrative
          <span className="tier tier-s">S</span>
          <small>v1.5's load-bearing claim · proof-of-concept: elefant_hunt</small>
        </h2>
        <JournalAsStory />

        {/* ===== §6 — Genre extensions ===== */}
        <h2 className="section-h2 has-tier" id="sec-genres" data-screen-label="06 Genres">
          <span className="num">§6</span> Genre extensions — configurations and enrichments
          <span className="tier tier-p3">P3</span>
          <small>each bundle is a configuration of core vocab, not new vocabulary</small>
        </h2>
        <p style={{maxWidth:900, color:"var(--ink-2)", fontSize:13, lineHeight:1.55, marginTop:0, marginBottom:10}}>
          Every Tier P3 bundle reuses the same core fragment types, value_types, and accepts.kinds.
          What it adds is <i>naming convention</i>, <i>emphasis convention</i>, optional <i>ui_hints
          sub-shapes</i> (open-dict extensions on <code>UIHints</code>), and conventional
          <i> zone_role</i>s. A client that ignores the genre layer still conforms: it just
          renders generic pieces, generic findings, generic dispositions.
        </p>
        <GenreIndex />

        {/* §6.1 carwars (the existing garage demo) */}
        <h3 className="section-h2 has-tier" id="sec-carwars" data-screen-label="06.1 Carwars" style={{fontSize:17, marginTop:32}}>
          <span className="num">§6.1</span> carwars — slots, catalog, stat_check, drag
          <span className="tier tier-p3">P3</span>
          <small>vehicle outfitting · the garage turn</small>
        </h3>
        <GarageDemo />

        {/* §6.2 credentials */}
        <h3 className="section-h2 has-tier" id="sec-credentials" data-screen-label="06.2 Credentials" style={{fontSize:17, marginTop:32}}>
          <span className="num">§6.2</span> credentials — packet inspection, severity findings
          <span className="tier tier-p3">P3</span>
          <small>Papers-Please-style verification</small>
        </h3>
        <CredentialsDemo />

        {/* §6.3 training */}
        <h3 className="section-h2 has-tier" id="sec-training" data-screen-label="06.3 Training" style={{fontSize:17, marginTop:32}}>
          <span className="num">§6.3</span> training — mood modulator, scheduled stat_check
          <span className="tier tier-p3">P3</span>
          <small>LLtQ-style scheduled progression</small>
        </h3>
        <TrainingDemo />

        {/* §6.4 elefant_hunt */}
        <h3 className="section-h2 has-tier" id="sec-elefant-hunt" data-screen-label="06.4 ElefantHunt" style={{fontSize:17, marginTop:32}}>
          <span className="num">§6.4</span> elefant_hunt — board graph, composite hunt, journal arc
          <span className="tier tier-p3">P3</span>
          <small>Tom-Wham-inspired sandbox board</small>
        </h3>
        <ElefantHuntDemo />

        {/* ===== §7 — Tier P2 worked examples ===== */}
        <h2 className="section-h2 has-tier" id="sec-roll-cmd" data-screen-label="07 RollCmd" style={{marginTop:48}}>
          <span className="num">§7</span> Tier P2 worked examples
          <span className="tier tier-p2">P2</span><span className="tier tier-p1">P1</span>
          <small>RollFragment + ritual · command bar + interpretation</small>
        </h2>
        <RollDemo />
        <CommandDemo />

        {/* ===== §8 — Sandbox conventions ===== */}
        <h2 className="section-h2 has-tier" id="sec-sandbox" data-screen-label="08 Sandbox" style={{marginTop:32}}>
          <span className="num">§8</span> Sandbox conventions — info channels in practice
          <span className="tier tier-p1">P1</span><span className="tier tier-p2">P2</span>
          <small>world_time · location · agenda · objectives · info affordances</small>
        </h2>
        <SandboxDemo />

        {/* ===== §9 — Port parity ===== */}
        <h2 className="section-h2 has-tier" id="sec-parity" data-screen-label="09 Parity" style={{marginTop:32}}>
          <span className="num">§9</span> Port parity — same vocabulary, four media
          <span className="tier tier-s">S</span>
          <small>CLI is the floor, not the ceiling — across all genres</small>
        </h2>
        <ParityTable12 />
        <div className="callout">
          <b>Bespoke per-world clients.</b> The vocabulary contract means a custom client can{" "}
          <i>add</i> widgets (battle-map, dice tray, faction tracker, packet-grading UI) without
          breaking the core stream — it opts in to render specific <code>zone_role</code> or
          <code> ui_hints</code> sub-shapes, and falls through to the parity row for everything
          else. Bundles MAY declare a <code>profiles[]</code> set; clients implementing a strict
          subset are still conforming for any bundle whose profiles are a subset of theirs.
        </div>

        {/* ===== §10 — Author / debug ===== */}
        <h2 className="section-h2 has-tier" data-screen-label="10 Debug" style={{marginTop:32}}>
          <span className="num">§10</span> Author / debug · what's next
          <span className="tier tier-p2">P2</span>
        </h2>
        <div className="spec-grid" style={{display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(280px, 1fr))", gap:10}}>
          <div className="spec-card" style={{background:"#fff", border:"1.5px solid var(--rule-strong)", padding:"12px 14px"}}>
            <h4 style={{margin:"0 0 6px", fontFamily:"var(--mono)", fontSize:11, letterSpacing:"0.08em", textTransform:"uppercase", color:"var(--ink-2)", display:"flex"}}>
              This envelope, in numbers <span className="frag-tag" style={{marginLeft:"auto", fontSize:9, color:"var(--ink-3)"}}>debug</span>
            </h4>
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
          <div className="spec-card" style={{background:"#fff", border:"1.5px solid var(--rule-strong)", padding:"12px 14px"}}>
            <h4 style={{margin:"0 0 6px", fontFamily:"var(--mono)", fontSize:11, letterSpacing:"0.08em", textTransform:"uppercase", color:"var(--ink-2)", display:"flex"}}>
              v1.5 conformance gates <span className="frag-tag" style={{marginLeft:"auto", fontSize:9, color:"var(--ink-3)"}}>policy</span>
            </h4>
            <div style={{fontSize:12, lineHeight:1.5}}>
              <ol style={{paddingLeft:18, margin:0}}>
                <li>CLI Floor — every Tier S widget renders in <code>cli_reference_port.py</code>.</li>
                <li>Decision Legibility — open-choice referenced UIDs are on-screen.</li>
                <li>Time Parity — visual ritual skippable to canonical-instant.</li>
                <li>Input Parity — every richer modality has a click-pick / typed-text fallback.</li>
              </ol>
              <p style={{margin:"8px 0 0", color:"var(--ink-3)", fontSize:11}}>
                v1.5: §0.8 journal-as-story adds a <i>per-bundle</i> transcript smoke test — not
                gating, but recommended for every Tier P3 genre bundle.
              </p>
            </div>
          </div>
          <div className="spec-card" style={{background:"#fff", border:"1.5px solid var(--rule-strong)", padding:"12px 14px"}}>
            <h4 style={{margin:"0 0 6px", fontFamily:"var(--mono)", fontSize:11, letterSpacing:"0.08em", textTransform:"uppercase", color:"var(--ink-2)", display:"flex"}}>
              Deferred to v1.6+ <span className="frag-tag" style={{marginLeft:"auto", fontSize:9, color:"var(--ink-3)"}}>P3+</span>
            </h4>
            <div style={{fontSize:12, lineHeight:1.5}}>
              <ul style={{paddingLeft:18, margin:0}}>
                <li>Multi-actor <code>CombatReport</code> fragment (round summary).</li>
                <li>Predicate-registration so <code>predicate_ref</code> becomes typed.</li>
                <li><code>hana_smuta</code> bundle EXTENSIONS — card play sketch.</li>
                <li>Multi-cursor reference CLI port to graduate §1.5 to Tier S.</li>
                <li>Bidding / area-control mechanisms (depend on predicates).</li>
              </ul>
            </div>
          </div>
          <div className="spec-card" style={{background:"#fff", border:"1.5px solid var(--rule-strong)", padding:"12px 14px"}}>
            <h4 style={{margin:"0 0 6px", fontFamily:"var(--mono)", fontSize:11, letterSpacing:"0.08em", textTransform:"uppercase", color:"var(--ink-2)", display:"flex"}}>
              Where to read more <span className="frag-tag" style={{marginLeft:"auto", fontSize:9, color:"var(--ink-3)"}}>docs</span>
            </h4>
            <div style={{fontSize:12, lineHeight:1.5}}>
              <ul style={{paddingLeft:18, margin:0}}>
                <li><code>STORYTANGL_WIDGET_VOCAB.md</code> · v1.5 target vocabulary.</li>
                <li><code>WIDGET_CONTRACT_RECONCILIATION.md</code> · per-surface implementation status.</li>
                <li><code>bundles/carwars/EXTENSIONS.md</code> · slot zones · stat_check · drag.</li>
                <li><code>bundles/credentials/EXTENSIONS.md</code> · packet inspection · severity findings.</li>
                <li><code>bundles/training/EXTENSIONS.md</code> · mood modulator · scheduled checks.</li>
                <li><code>bundles/elefant_hunt/EXTENSIONS.md</code> · graph board · journal-as-story.</li>
              </ul>
            </div>
          </div>
        </div>

        {/* End mark */}
        <div style={{marginTop:48, fontFamily:"var(--mono)", fontSize:10.5, color:"var(--ink-3)"}}>
          ── end · v1.5 wireframes · all examples consume real envelope+projected_state shapes from{" "}
          <code>v15-fixtures-core.js</code> and <code>v15-fixtures-genres.js</code>. Widgets in{" "}
          <code>v15-widgets.jsx</code>; shells in <code>v15-shells.jsx</code>; core sections in{" "}
          <code>v15-sections-core.jsx</code>; genre sections in <code>v15-sections-genres.jsx</code>.
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
