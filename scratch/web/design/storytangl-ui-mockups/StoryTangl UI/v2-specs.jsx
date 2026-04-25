// v2-specs.jsx — fragment-to-widget matrix, spec cards, port parity, author view

const SPEC_CARDS = [
  {
    frag: "content",
    widget: "Prose block",
    required: ["content"],
    optional: ["format", "hints.style_tags", "hints.style_dict", "source_id"],
    fallback: "If format unknown, render content as plain text; ignore hints.",
    empty: "skip",
    loading: "stream text in as chunks arrive",
    error: "render raw string with a red margin-mark",
    mobile: "full width, serif body, 16px min",
    keyboard: "Tab skips; selectable text",
    preview: <div style={{fontFamily:"var(--serif)",fontSize:13}}>Rain drums on the thatch. Inside the inn the air is smoke and peat…</div>,
  },
  {
    frag: "attributed",
    widget: "Dialog line",
    required: ["who", "how", "media", "content"],
    optional: ["hints"],
    fallback: "Render as prose prefixed with who:",
    empty: "hide line entirely",
    loading: "placeholder avatar, ellipsis body",
    error: "show who + raw content; drop how",
    mobile: "avatar 32px, who above body",
    keyboard: "skippable via arrow keys in replay",
    preview: (
      <div style={{display:"flex",gap:6,alignItems:"flex-start"}}>
        <div style={{width:22,height:22,borderRadius:"50%",border:"1px solid var(--ink-3)",background:"var(--paper-2)",fontFamily:"var(--mono)",fontSize:8,display:"flex",alignItems:"center",justifyContent:"center"}}>S</div>
        <div><b style={{color:"var(--accent-ink)",fontSize:11}}>Stranger</b> <i style={{fontSize:10,color:"var(--ink-3)"}}>(low)</i><div style={{fontSize:12}}>Forty silver. No haggle.</div></div>
      </div>
    ),
  },
  {
    frag: "media",
    widget: "Media frame",
    required: ["content", "content_format"],
    optional: ["media_role", "staging_hints.*", "scope"],
    fallback: "If role unknown → inline image; if content_format=rit and unresolved → placeholder card with RIT id.",
    empty: "hide",
    loading: "striped placeholder + role label",
    error: "striped placeholder + error text; keep layout",
    mobile: "full bleed for cover_im; inline for narrative_im",
    keyboard: "focusable for longform media (audio, video); space to toggle",
    preview: <div style={{width:"100%",aspectRatio:"16/9",border:"1px dashed var(--blue-pencil)",background:"repeating-linear-gradient(135deg,rgba(58,93,122,0.14) 0 6px,rgba(58,93,122,0.04) 6px 12px)",fontFamily:"var(--mono)",fontSize:10,color:"var(--blue-pencil)",display:"flex",alignItems:"center",justifyContent:"center"}}>narrative_im</div>,
  },
  {
    frag: "choice",
    widget: "Choice button / input",
    required: ["edge_id", "text"],
    optional: ["available", "unavailable_reason", "blockers[]", "accepts{}", "ui_hints{hotkey,icon,emphasis}", "payload"],
    fallback: "Render disabled if unknown; log a warning; never silently drop.",
    empty: "must have ≥1 available for turn to be actionable — emit blocker notice",
    loading: "disable entire choice group; show spinner near primary",
    error: "mark action as failed; keep choices enabled for retry",
    mobile: "44px hit target; stacked full-width",
    keyboard: "1-9 hotkey from ui_hints; ↑↓ cycles; Enter commits; Esc cancels freeform",
    preview: (
      <div style={{display:"flex",flexDirection:"column",gap:4,width:"100%"}}>
        <div style={{border:"1.5px solid var(--ink)",padding:"4px 8px",fontSize:11,display:"flex",gap:6,alignItems:"center"}}><span style={{fontFamily:"var(--mono)",fontSize:9,border:"1px solid var(--rule)",padding:"0 4px"}}>1</span> Pay the forty silver.</div>
        <div style={{border:"1.5px dashed var(--ink)",padding:"4px 8px",fontSize:11,opacity:0.55,display:"flex",gap:6}}><span style={{fontFamily:"var(--mono)",fontSize:9}}>4</span><span style={{textDecoration:"line-through"}}>Lift the map.</span><span style={{marginLeft:"auto",fontFamily:"var(--mono)",fontSize:9,color:"var(--accent)"}}>SOH ≥ 2</span></div>
      </div>
    ),
  },
  {
    frag: "group",
    widget: "Container (role-switched)",
    required: ["group_type", "member_ids[]"],
    optional: ["hints"],
    fallback: "If group_type unknown → render members in order with no wrapper.",
    empty: "hide",
    loading: "render members in order as they arrive",
    error: "render members flat; warn",
    mobile: "dialog group = indented rule; scene group = implicit; overlay = sheet",
    keyboard: "dialog group is aria-live region; overlay traps focus",
    preview: <div style={{fontFamily:"var(--mono)",fontSize:10,color:"var(--ink-3)"}}>group_type ∈ {"{"}scene, dialog, turn, overlay, status_sidecar{"}"}</div>,
  },
  {
    frag: "kv",
    widget: "KV strip OR side rail",
    required: ["content (OrderedTupleDict)"],
    optional: ["hints.style_tags (e.g. status-inline)"],
    fallback: "Render as 'k: v' plaintext lines.",
    empty: "hide",
    loading: "skeleton rows",
    error: "render known pairs; mark failed ones",
    mobile: "wrap into 2-col; rail collapses into top strip",
    keyboard: "not focusable by default (informational)",
    preview: (
      <div style={{display:"flex",gap:10,fontFamily:"var(--mono)",fontSize:10,background:"var(--paper-2)",padding:"4px 6px"}}>
        <span>time: <b>late</b></span><span>coin: <b>63</b></span><span>weather: <b>rain</b></span>
      </div>
    ),
  },
  {
    frag: "control",
    widget: "(silent) fragment mutation",
    required: ["ref_type", "ref_id", "fragment_type ∈ update|delete"],
    optional: ["payload (required for update)"],
    fallback: "Ignore control if ref_id not found in local registry; log.",
    empty: "n/a",
    loading: "n/a — applied atomically",
    error: "retain original fragment; surface to author view only",
    mobile: "invisible — triggers re-render of target",
    keyboard: "invisible",
    preview: <div style={{fontFamily:"var(--mono)",fontSize:10,color:"var(--ink-3)"}}>update → content#glossary:vellum</div>,
  },
  {
    frag: "user_event",
    widget: "Toast / silent stash",
    required: ["event_type"],
    optional: ["content (any)"],
    fallback: "Unknown event_type → stash on user record, no UI.",
    empty: "skip",
    loading: "n/a",
    error: "silent; log to author view",
    mobile: "bottom toast, auto-dismiss 3s",
    keyboard: "Esc dismisses",
    preview: <div style={{border:"1.5px solid var(--ink)",background:"var(--paper)",padding:"4px 8px",fontSize:11,fontFamily:"var(--mono)"}}>★ met_10_strangers · 7/10</div>,
  },
];

function SpecCards() {
  return (
    <div className="spec-grid">
      {SPEC_CARDS.map((s, i) => (
        <div key={i} className="spec-card">
          <h4>{s.widget}<span className="frag-tag">{s.frag}</span></h4>
          <div className="spec-body">
            <div className="preview">{s.preview}</div>
            <dl>
              <dt>req</dt><dd>{s.required.map((r,j) => <code key={j} style={{marginRight:4}}>{r}</code>)}</dd>
              <dt>opt</dt><dd>{s.optional.map((r,j) => <code key={j} style={{marginRight:4,opacity:0.75}}>{r}</code>)}</dd>
              <dt>fallback</dt><dd>{s.fallback}</dd>
              <dt>mobile</dt><dd>{s.mobile}</dd>
              <dt>keyboard</dt><dd>{s.keyboard}</dd>
            </dl>
            <div className="states-strip">
              <span className="state-chip empty"><b>empty</b><span>{s.empty}</span></span>
              <span className="state-chip loading"><b>loading</b><span>{s.loading}</span></span>
              <span className="state-chip error"><b>error</b><span>{s.error}</span></span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------- Fragment-to-widget matrix ----------
const MATRIX_ROWS = [
  { group: "RuntimeEnvelope.fragments" },
  { frag: "content", widget: "Prose block", scroll: "inline paragraph", dossier: "stage prose column", stage: "caption (if current) + log row" },
  { frag: "attributed", widget: "Dialog line", scroll: "indented line w/ avatar", dossier: "bracketed under prose", stage: "active caption; log row" },
  { frag: "media · cover_im", widget: "Banner frame", scroll: "top banner", dossier: "persistent header", stage: "fullscreen bg" },
  { frag: "media · narrative_im", widget: "Inline figure", scroll: "inline w/ wrap", dossier: "stage column", stage: "set dressing" },
  { frag: "media · avatar_im", widget: "Avatar chip", scroll: "beside dialog line", dossier: "beside dialog line", stage: "character sprite" },
  { frag: "media · dialog_im", widget: "Inline figure", scroll: "attached to line", dossier: "attached to line", stage: "lower-left inset" },
  { frag: "media · audio/video", widget: "Player", scroll: "inline controls", dossier: "footer controls", stage: "overlay HUD" },
  { frag: "choice", widget: "Button / input", scroll: "bottom list", dossier: "bottom of stage column", stage: "tray below log" },
  { frag: "group · scene", widget: "(implicit turn)", scroll: "(boundary)", dossier: "(boundary)", stage: "scene change" },
  { frag: "group · dialog", widget: "Indented rule", scroll: "border-left rule", dossier: "bracketed block", stage: "consecutive captions" },
  { frag: "group · turn", widget: "(implicit)", scroll: "separator", dossier: "separator", stage: "log divider" },
  { frag: "group · overlay", widget: "Modal sheet", scroll: "sticky sheet", dossier: "right-rail takeover", stage: "dim + center" },
  { frag: "group · status_sidecar", widget: "KV rail", scroll: "collapsible strip", dossier: "right rail", stage: "HUD top-left" },
  { frag: "kv", widget: "KV strip", scroll: "inline strip", dossier: "merge into rail", stage: "HUD" },
  { frag: "control · update", widget: "(silent)", scroll: "replace target", dossier: "replace target", stage: "replace target" },
  { frag: "control · delete", widget: "(silent)", scroll: "remove target", dossier: "remove target", stage: "remove target" },
  { frag: "user_event", widget: "Toast / stash", scroll: "toast", dossier: "toast", stage: "HUD blip" },

  { group: "ProjectedState.sections (sidecar)" },
  { frag: "scalar", widget: "Big number / badge", scroll: "strip cell", dossier: "rail tile", stage: "HUD value" },
  { frag: "kv_list", widget: "Key-value table", scroll: "strip (wrapped)", dossier: "rail rows", stage: "HUD stack" },
  { frag: "item_list", widget: "Item roster", scroll: "drawer", dossier: "rail list", stage: "inventory overlay" },
  { frag: "table", widget: "Data table", scroll: "drawer", dossier: "rail mini-table", stage: "overlay sheet" },
  { frag: "badges", widget: "Tag strip", scroll: "inline chips", dossier: "rail chips", stage: "HUD chips" },
];

function Matrix() {
  return (
    <div className="matrix-wrap">
      <table className="matrix">
        <thead>
          <tr>
            <th style={{width:"18%"}}>Fragment / value_type</th>
            <th style={{width:"18%"}}>Widget</th>
            <th>Scroll</th>
            <th>Dossier</th>
            <th>Stage + Log</th>
          </tr>
        </thead>
        <tbody>
          {MATRIX_ROWS.map((r, i) => r.group ? (
            <tr key={i} className="section-row"><td colSpan={5}>{r.group}</td></tr>
          ) : (
            <tr key={i}>
              <td className="frag">{r.frag}</td>
              <td className="widget">{r.widget}</td>
              <td>{r.scroll}</td>
              <td>{r.dossier}</td>
              <td>{r.stage}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------- Port parity ----------
const PARITY = [
  { w: "Prose block",   web: "<article>",                   cli: "wrapped lines",           renpy: "narrator say",           terminal: "reflowed stdout" },
  { w: "Dialog line",   web: "avatar + bubble",             cli: "who: text",               renpy: "character say",          terminal: "'who> text'" },
  { w: "Cover/narr media", web: "<img>/<video>",            cli: "[img: url]",              renpy: "scene bg / show expr",   terminal: "link + ascii box" },
  { w: "Avatar",        web: "round <img>",                 cli: "(elided)",                renpy: "side image",             terminal: "(elided)" },
  { w: "Audio",         web: "<audio>",                     cli: "[♪ url]",                 renpy: "play music / sound",     terminal: "[♪]" },
  { w: "Choice",        web: "button list",                 cli: "1) … 2) …",               renpy: "menu:",                  terminal: "numbered prompt" },
  { w: "Locked choice", web: "disabled + reason",           cli: "(locked) reason",         renpy: "if-gated, grey",         terminal: "greyed" },
  { w: "Freeform choice", web: "inline input",              cli: "prompt '>'",              renpy: "input / pyexpr",         terminal: "readline" },
  { w: "Dialog group",  web: "indented rule region",        cli: "blank lines bracket",     renpy: "contiguous say block",   terminal: "blank-line bracket" },
  { w: "Overlay group", web: "modal sheet",                 cli: "'---' banner",            renpy: "screen call with modal", terminal: "full-screen page" },
  { w: "KV rail",       web: "right rail",                  cli: "[status] line",           renpy: "stats screen",           terminal: "status bar" },
  { w: "Scalar / badge", web: "tile",                       cli: "key=value",               renpy: "text widget",            terminal: "status seg" },
  { w: "Item list",     web: "roster",                      cli: "'- item (detail)'",       renpy: "inventory screen",       terminal: "list cmd" },
  { w: "Table",         web: "<table>",                     cli: "aligned cols",            renpy: "grid()",                 terminal: "aligned cols" },
  { w: "Toast / user_event", web: "bottom toast",           cli: "'* note' line",           renpy: "notify()",               terminal: "status flash" },
  { w: "control update/delete", web: "re-render target",    cli: "re-print with marker",    renpy: "re-show statement",      terminal: "re-print" },
];

function ParityTable() {
  return (
    <table className="parity-table">
      <thead><tr><th>Widget</th><th>Web (Vue / bespoke)</th><th>CLI (current)</th><th>Ren'Py / Godot</th><th>Tcl / terminal</th></tr></thead>
      <tbody>{PARITY.map((r,i) => (
        <tr key={i}><td className="w">{r.w}</td><td>{r.web}</td><td>{r.cli}</td><td>{r.renpy}</td><td>{r.terminal}</td></tr>
      ))}</tbody>
    </table>
  );
}

Object.assign(window, { SpecCards, Matrix, ParityTable });
