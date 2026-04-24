// v2-app.jsx — the top-level page that composes matrix, triptych, spec cards, parity, author notes.

const { useState: useStateApp } = React;

function LegendRibbon() {
  return (
    <div className="legend">
      <span><i className="swatch req"></i>required field</span>
      <span><i className="swatch opt"></i>optional field</span>
      <span><i className="swatch hint"></i>hint / staging</span>
      <span>source: <code>tangl.journal.fragments</code> + <code>tangl.service.response</code></span>
      <span>fixture: <code>crossroads_inn · turn 03</code></span>
    </div>
  );
}

function AuthorNotes() {
  return (
    <div className="spec-grid" style={{gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))"}}>
      <div className="spec-card">
        <h4>Phases <span className="frag-tag">bus</span></h4>
        <div className="spec-body">
          <div style={{fontFamily:"var(--mono)",fontSize:10.5,color:"var(--ink-2)"}}>
            resolve → compose → project → dispatch<br/>
            step 47 · cursor b6e0f3a4…<br/>
            last_redirect: null<br/>
            redirect_trace: []
          </div>
        </div>
      </div>
      <div className="spec-card">
        <h4>Emitted fragments <span className="frag-tag">11</span></h4>
        <div className="spec-body">
          <div style={{fontFamily:"var(--mono)",fontSize:10.5,lineHeight:1.6}}>
            1 group·scene<br/>1 content<br/>2 media (cover, narr)<br/>
            1 group·dialog<br/>2 attributed<br/>2 media (avatar, dlg·pending)<br/>
            1 kv · 4 choices · 1 user_event · 1 control·update
          </div>
        </div>
      </div>
      <div className="spec-card">
        <h4>Projected sections <span className="frag-tag">5</span></h4>
        <div className="spec-body">
          <div style={{fontFamily:"var(--mono)",fontSize:10.5,lineHeight:1.6}}>
            scalar · Wounds<br/>
            kv_list · Purse<br/>
            item_list · Satchel<br/>
            table · Party<br/>
            badges · Conditions
          </div>
        </div>
      </div>
      <div className="spec-card">
        <h4>Ledger / graph <span className="frag-tag">ref</span></h4>
        <div className="spec-body">
          <div style={{fontFamily:"var(--mono)",fontSize:10.5,lineHeight:1.6}}>
            current node: crossroads_inn · ch01·03<br/>
            traversed edges: 46<br/>
            open edges: 4 (1 locked, 1 accepts payload)<br/>
            blockers: sleight_of_hand≥2 (have 1), elen_watching
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  const env = window.FIXTURE.envelope;
  const proj = window.FIXTURE.projected_state;

  const handlePick = (c) => console.log("pick", c.edge_id, c);

  return (
    <div className="paper">
      <div className="rail">
        <div className="brand"><b>StoryTangl</b> · wireframes v2</div>
        <div className="sep"></div>
        <div className="doc-meta">engine-aligned · {new Date().toISOString().slice(0,10)}</div>
        <div className="spacer"></div>
        <a className="tab" href="StoryTangl Wireframes.html" style={{textDecoration:"none",color:"inherit"}}>← v1 (shells tour)</a>
      </div>

      <div style={{maxWidth:1280, margin:"0 auto", padding:"24px 28px 80px"}}>
        <div style={{display:"flex",alignItems:"baseline",gap:16,marginBottom:6}}>
          <h1 style={{margin:0,fontFamily:"var(--serif)",fontSize:32,letterSpacing:"-0.01em"}}>Widget vocabulary, against real contracts.</h1>
        </div>
        <p style={{maxWidth:780,color:"var(--ink-2)",fontSize:14,lineHeight:1.55}}>
          V1 sketched shells with a fake block model. V2 is grounded: every shell in this doc consumes a single fixture
          shaped exactly like <code>RuntimeEnvelope.fragments</code> and <code>ProjectedState.sections</code>. The matrix
          below is the rendering contract; the triptych proves it round-trips across three very different UIs; the spec
          cards fix required fields, states, keyboard, and fallbacks per widget; the parity table extends the vocabulary
          to CLI, Ren'Py/Godot, and a terminal client.
        </p>

        <LegendRibbon />

        {/* §1 Matrix */}
        <h2 className="section-h2">
          <span className="num">§1</span> Fragment × Widget × Shell matrix
          <span className="sub">one row per canonical fragment_type / value_type</span>
        </h2>
        <Matrix />
        <div className="callout">
          <b>Rule of thumb.</b> The shell is allowed to choose <i>where</i> a widget lives, not <i>whether</i> it renders.
          If a client can't render a fragment type, it must fall back to a textual rep listed in the parity table —
          never silently drop, because <code>control</code> fragments target UIDs and later turns assume those UIDs
          still resolve.
        </div>

        {/* §2 Triptych */}
        <h2 className="section-h2">
          <span className="num">§2</span> Same payload, three shells
          <span className="sub">crossroads_inn · turn 03</span>
        </h2>
        <p style={{maxWidth:820,color:"var(--ink-2)"}}>
          All three panels below read the <i>same</i> <code>window.FIXTURE</code>. The only thing that differs is how
          each shell maps <code>group</code>, <code>media.staging_hints.media_position</code>, and the projected-state
          sections onto screen geometry.
        </p>
        <div className="triptych">
          <div className="shell-frame">
            <div className="shell-head"><span className="name">Scroll</span><span className="kind">journal-style, linear</span></div>
            <div className="shell-body"><ScrollShell envelope={env} onPick={handlePick} /></div>
          </div>
          <div className="shell-frame">
            <div className="shell-head"><span className="name">Dossier</span><span className="kind">stage + projected rail</span></div>
            <div className="shell-body"><DossierShell envelope={env} projected={proj} /></div>
          </div>
          <div className="shell-frame">
            <div className="shell-head"><span className="name">Stage + Log</span><span className="kind">VN-ish + fragment tape</span></div>
            <div className="shell-body"><StageShell envelope={env} /></div>
          </div>
        </div>
        <div className="callout">
          <b>What each shell decides.</b> <i>Scroll</i> treats the scene group as a chapter and the kv fragment as
          inline chrome; <i>Dossier</i> routes all projected sections to the right rail and keeps the kv inline with the
          prose; <i>Stage+Log</i> elevates the most recent attributed fragment to a caption and renders every fragment
          as a row on the tape — useful for replay and debugging.
        </div>

        {/* §3 Spec cards */}
        <h2 className="section-h2">
          <span className="num">§3</span> Widget specs
          <span className="sub">fields · states · a11y · fallback</span>
        </h2>
        <SpecCards />

        {/* §4 Edge cases */}
        <h2 className="section-h2">
          <span className="num">§4</span> Edge cases worth fixing now
          <span className="sub">before per-world clients fork</span>
        </h2>
        <div className="spec-grid">
          <div className="spec-card"><h4>Locked choices</h4><div className="spec-body" style={{fontSize:12,lineHeight:1.5}}>
            <p style={{margin:0}}><code>available=false</code> + <code>unavailable_reason</code> is the user-visible contract.
            <code>blockers[]</code> is structured — author tools show it, players don't.
            Render as a disabled button with reason as secondary text; keep it in the DOM so screen readers and keyboard
            order are stable.</p>
          </div></div>
          <div className="spec-card"><h4>Freeform input choices</h4><div className="spec-body" style={{fontSize:12,lineHeight:1.5}}>
            <p style={{margin:0}}><code>accepts</code> turns a choice into a form. Widget = labeled input inline
            with the button. Enter commits <code>payload</code>; Esc reverts to a plain button. CLI renders a
            <code>'&gt;'</code> prompt after the numbered list.</p>
          </div></div>
          <div className="spec-card"><h4>Pending generated media</h4><div className="spec-body" style={{fontSize:12,lineHeight:1.5}}>
            <p style={{margin:0}}>When <code>content_format=rit</code> and unresolved, emit the media fragment anyway
            with a stable UID. Client renders the striped placeholder with role + RIT id. A later <code>control·update</code>
            swaps in a <code>url</code> or <code>data</code> payload — same widget, same DOM node, no reflow.</p>
          </div></div>
          <div className="spec-card"><h4>Multiple media roles in one turn</h4><div className="spec-body" style={{fontSize:12,lineHeight:1.5}}>
            <p style={{margin:0}}>Shells route by <code>media_role</code>, not order. cover_im is persistent chrome;
            narrative_im belongs to the active content; avatar_im + dialog_im bind to the nearest preceding attributed
            fragment; audio/video/sfx are timelined against <code>staging_hints.media_timing</code>.</p>
          </div></div>
          <div className="spec-card"><h4>Group semantics</h4><div className="spec-body" style={{fontSize:12,lineHeight:1.5}}>
            <p style={{margin:0}}>Treat <code>group_type</code> as the rendering hint, not <code>fragment_type</code>.
            Required set: <code>scene, dialog, turn, overlay, status_sidecar</code>. Unknown group_type → render
            members flat. Nesting is allowed one level (overlay inside scene).</p>
          </div></div>
          <div className="spec-card"><h4>KV: flow vs rail vs both</h4><div className="spec-body" style={{fontSize:12,lineHeight:1.5}}>
            <p style={{margin:0}}>A <code>KvFragment</code> in the stream is scene-bound (e.g. "time: late, weather: rain").
            A projected <code>kv_list</code> section is durable (purse, stats). Scroll renders both inline; Dossier
            promotes projected to the rail and keeps stream-kv inline; CLI flattens everything to a status line.</p>
          </div></div>
          <div className="spec-card"><h4>"Current", "history", "persistent"</h4><div className="spec-body" style={{fontSize:12,lineHeight:1.5}}>
            <p style={{margin:0}}>Current = fragments with <code>cursor_id</code> == envelope.cursor_id.
            History = prior envelopes, dimmed, choices disabled. Persistent = projected_state, re-projected every turn;
            shell is free to animate deltas.</p>
          </div></div>
          <div className="spec-card"><h4>A11y & reduced motion</h4><div className="spec-body" style={{fontSize:12,lineHeight:1.5}}>
            <p style={{margin:0}}>Choice group is a <code>role=group</code> with <code>aria-label</code>; hotkeys come
            from <code>ui_hints.hotkey</code>; focus returns to the primary choice after an action resolves.
            <code>prefers-reduced-motion</code> disables <code>media_transition</code> and swaps to instant.
            Stage captions obey an <code>aria-live=polite</code> region.</p>
          </div></div>
        </div>

        {/* §5 Author */}
        <h2 className="section-h2">
          <span className="num">§5</span> Author / debug mode
          <span className="sub">grounded in envelope + ledger + phase bus</span>
        </h2>
        <AuthorNotes />

        {/* §6 Parity */}
        <h2 className="section-h2">
          <span className="num">§6</span> Port parity
          <span className="sub">same vocabulary in web / CLI / Ren'Py / terminal</span>
        </h2>
        <ParityTable />
        <div className="callout">
          <b>Bespoke per-world clients.</b> The vocabulary contract means a custom client can <i>add</i> widgets
          (card-table, dice tray, map) without breaking the core stream — it opts in to render specific
          <code>group_type</code>s or <code>ui_hints.widget</code> values, and falls through to the parity row for
          everything else.
        </div>

        <div style={{marginTop:48,fontFamily:"var(--mono)",fontSize:10.5,color:"var(--ink-3)"}}>
          ── end · v2 wireframes · sources: tangl.journal.fragments (ContentFragment, MediaFragment, ChoiceFragment,
          GroupFragment, KvFragment, ControlFragment, UserEventFragment, AttributedFragment, DialogFragment),
          tangl.service.response (RuntimeEnvelope, ProjectedState, ScalarValue, KvListValue, ItemListValue, TableValue,
          BadgeListValue, PresentationHints, StagingHints)
        </div>
      </div>
    </div>
  );
}

const rootEl = document.getElementById("root");
ReactDOM.createRoot(rootEl).render(<App />);
