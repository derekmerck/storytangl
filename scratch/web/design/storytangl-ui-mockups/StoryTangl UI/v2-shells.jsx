// v2-shells.jsx — three shells rendering the SAME fixture
// Scroll, Dossier, Stage+Log. Each consumes envelope.fragments + projected_state.

const { useMemo, useState } = React;

// ---------- fragment helpers ----------
const byId = (frags) => Object.fromEntries(frags.map(f => [f.uid, f]));

// Scene group gives us the canonical turn. We flatten it into a render list
// but also keep dialog-group nesting.
function flattenTurn(envelope) {
  const frags = envelope.fragments;
  const idx = byId(frags);
  const sceneGroup = frags.find(f => f.fragment_type === "group" && f.group_type === "scene");
  if (!sceneGroup) return { items: frags, dialogGroups: [], choices: [] };

  const items = sceneGroup.member_ids.map(id => idx[id]).filter(Boolean);
  const dialogGroups = items.filter(f => f.fragment_type === "group" && f.group_type === "dialog");
  const choices = items.filter(f => f.fragment_type === "choice");
  return { items, dialogGroups, choices, idx };
}

function dialogLines(group, idx) {
  const members = group.member_ids.map(id => idx[id]).filter(Boolean);
  // attach immediately-following avatar_im media to the preceding attributed
  const out = [];
  let pendingMedia = [];
  members.forEach(m => {
    if (m.fragment_type === "attributed") {
      out.push({ ...m, attached_media: [] });
    } else if (m.fragment_type === "media") {
      if (out.length) out[out.length - 1].attached_media.push(m);
      else pendingMedia.push(m);
    }
  });
  return out;
}

// ---------- Scroll shell ----------
function ScrollShell({ envelope, onPick }) {
  const { items, idx } = flattenTurn(envelope);
  return (
    <div className="v2-scroll" role="log" aria-live="polite">
      {items.map((f, i) => {
        if (f.fragment_type === "media" && f.media_role === "cover_im") {
          return <div key={i} className="sc-media">cover_im — banner · top · fade_in</div>;
        }
        if (f.fragment_type === "content") {
          return <p key={i} className="sc-para">{f.content}</p>;
        }
        if (f.fragment_type === "media" && f.media_role === "narrative_im") {
          return <div key={i} className="sc-media" style={{aspectRatio:"4/3"}}>narrative_im — portrait · right</div>;
        }
        if (f.fragment_type === "group" && f.group_type === "dialog") {
          const lines = dialogLines(f, idx);
          return (
            <div key={i} className="sc-dialog-group" aria-label="dialog">
              {lines.map((l, j) => (
                <div key={j} className="sc-dialog-line">
                  <div className="sc-avatar">{l.attached_media.find(m => m.media_role==="avatar_im") ? "AVA" : "?"}</div>
                  <div>
                    <div>
                      <span className="who">{l.who}</span>
                      <span className="how">({l.how})</span>
                    </div>
                    <div>{l.content}</div>
                    {l.attached_media.find(m => m.generation_status === "pending") && (
                      <div style={{fontFamily:"var(--mono)",fontSize:10,color:"var(--blue-pencil)",marginTop:4}}>
                        [dialog_im · generating…]
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          );
        }
        if (f.fragment_type === "kv") {
          return (
            <div key={i} className="sc-kv-inline" aria-label="scene status">
              {f.content.map(([k,v], j) => (
                <span key={j} className="kv-pair">{k}:<b>{String(v)}</b></span>
              ))}
            </div>
          );
        }
        return null;
      })}

      <div className="sc-choices" role="group" aria-label="choices">
        {items.filter(f => f.fragment_type === "choice").map((c, i) => (
          <button
            key={i}
            className={"sc-choice" + (c.available ? "" : " locked")}
            disabled={!c.available}
            onClick={() => c.available && onPick(c)}
            aria-disabled={!c.available}
          >
            <span className="key">{c.ui_hints?.hotkey || (i+1)}</span>
            <span className="label">{c.text}</span>
            {c.accepts && <span className="accept">accepts · {c.accepts.input}</span>}
            {!c.available && <span className="reason">{c.unavailable_reason}</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------- Dossier shell ----------
function DossierShell({ envelope, projected }) {
  const { items, idx } = flattenTurn(envelope);
  const choices = items.filter(f => f.fragment_type === "choice");
  return (
    <div className="v2-dossier">
      <div className="dos-stage">
        <div className="dos-cover">cover_im — crossroads_inn_night.jpg</div>
        {items.filter(f => f.fragment_type === "content").map((f, i) => (
          <p key={i} className="dos-prose">{f.content}</p>
        ))}
        {items.filter(f => f.fragment_type === "group" && f.group_type === "dialog").map((g, i) => {
          const lines = dialogLines(g, idx);
          return (
            <div key={i} className="dos-dialog">
              {lines.map((l, j) => (
                <div key={j}>
                  <span style={{fontFamily:"var(--sans)",fontWeight:700,fontSize:11,color:"var(--accent-ink)"}}>{l.who} </span>
                  <span style={{fontSize:10.5,color:"var(--ink-3)",fontStyle:"italic"}}>({l.how}) </span>
                  <span>{l.content}</span>
                </div>
              ))}
            </div>
          );
        })}
        <div className="dos-choices" role="group" aria-label="choices">
          {choices.map((c, i) => (
            <div key={i} className={"dos-choice" + (c.available ? "" : " locked")}>
              <span className="key">{c.ui_hints?.hotkey || (i+1)}</span>
              <span className="dos-label">{c.text}</span>
              {c.accepts && <span className="dos-meta" style={{color:"var(--blue-pencil)"}}>⌨ {c.accepts.input}</span>}
              {!c.available && <span className="dos-meta" style={{color:"var(--accent)",whiteSpace:"normal"}}>{c.unavailable_reason}</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="dos-rail">
        {projected.sections.map((s, i) => <RailSection key={i} section={s} />)}
      </div>
    </div>
  );
}

function RailSection({ section }) {
  const v = section.value;
  return (
    <div className="rail-section">
      <h4>{section.title}<span className="tag">{v.value_type}</span></h4>
      <div className="body">
        {v.value_type === "scalar" && <div className="rail-scalar">{String(v.value)}</div>}
        {v.value_type === "kv_list" && v.items.map((it,i) => (
          <div key={i} className="rail-kv-row"><span>{it.key}</span><b>{String(it.value)}</b></div>
        ))}
        {v.value_type === "item_list" && (
          <div className="rail-items">
            {v.items.map((it,i) => (
              <div key={i} className="item">
                <div className="label">{it.label}</div>
                {it.detail && <div className="detail">{it.detail}</div>}
                {it.tags.length > 0 && <div className="tags">{it.tags.map((t,j) => <span key={j} className="tag">{t}</span>)}</div>}
              </div>
            ))}
          </div>
        )}
        {v.value_type === "table" && (
          <table style={{width:"100%",fontSize:10,borderCollapse:"collapse"}}>
            <thead><tr>{v.columns.map((c,i) => <th key={i} style={{textAlign:"left",color:"var(--ink-3)",borderBottom:"1px solid var(--rule)",padding:"2px 4px"}}>{c}</th>)}</tr></thead>
            <tbody>{v.rows.map((r,i) => (
              <tr key={i}>{r.map((cell,j) => <td key={j} style={{padding:"2px 4px",borderBottom:"1px dotted var(--rule)"}}>{String(cell)}</td>)}</tr>
            ))}</tbody>
          </table>
        )}
        {v.value_type === "badges" && (
          <div className="rail-badges">{v.items.map((b,i) => <span key={i} className="rail-badge">{b}</span>)}</div>
        )}
      </div>
    </div>
  );
}

// ---------- Stage+Log shell ----------
function StageShell({ envelope }) {
  const { items, idx } = flattenTurn(envelope);
  const dialogGroup = items.find(f => f.fragment_type === "group" && f.group_type === "dialog");
  const lines = dialogGroup ? dialogLines(dialogGroup, idx) : [];
  const [lineIdx, setLineIdx] = useState(lines.length - 1);
  const current = lines[lineIdx] || lines[lines.length - 1];
  const choices = items.filter(f => f.fragment_type === "choice");

  // log rows derived from fragment stream
  const logRows = items.flatMap((f, i) => {
    if (f.fragment_type === "content") return [{ kind: "content", text: f.content.slice(0,60) + "…", idx: i }];
    if (f.fragment_type === "attributed") return [{ kind: "attrib", text: `${f.who}: ${f.content.slice(0,44)}…`, idx: i }];
    if (f.fragment_type === "media") return [{ kind: "media", text: `${f.media_role} ${f.content_format}`, idx: i }];
    if (f.fragment_type === "kv") return [{ kind: "kv", text: `${f.content.length} keys`, idx: i }];
    if (f.fragment_type === "choice") return [{ kind: "choice", text: f.text, idx: i }];
    if (f.fragment_type === "group") return [{ kind: "group", text: `${f.group_type} × ${f.member_ids.length}`, idx: i }];
    return [];
  });

  return (
    <div className="v2-stage">
      <div className="stage-top">
        <div className="stage-bg" />
        <div className="stage-tag">scene · crossroads_inn · rain · night</div>
        <div className="stage-chars">
          <div className="stage-char">Bram</div>
          <div className="stage-char speaking">Stranger</div>
          <div className="stage-char">Elen</div>
        </div>
        {current && (
          <div className="stage-caption">
            <span className="who">{current.who} — {current.how}</span>
            {current.content}
          </div>
        )}
      </div>
      <div className="stage-log" aria-label="fragment log">
        {logRows.map((r, i) => (
          <div key={i} className={"log-row" + (r.kind === "attrib" ? " current" : "")}>
            <span className="t">+0:0{i}</span>
            <span className="kind">{r.kind}</span>
            <span>{r.text}</span>
          </div>
        ))}
      </div>
      <div className="stage-choices">
        {choices.map((c, i) => (
          <button key={i} className={"stage-choice" + (c.available ? "" : " locked")} disabled={!c.available}>
            <span className="key">{c.ui_hints?.hotkey || (i+1)}</span>
            <span>{c.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { ScrollShell, DossierShell, StageShell });
