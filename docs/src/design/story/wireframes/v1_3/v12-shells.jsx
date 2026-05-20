// v12-shells.jsx — three reference shells.
// All consume the SAME envelope+projected_state pair. They differ only in
// where content flows: linear journal (Scroll), stage + projected rail
// (Dossier), VN-style caption with full fragment tape (Stage+Log).
//
// Shells are intentionally thin — every fragment-aware decision lives in
// the widgets module. The shells decide layout: which container, which side.

const { useState: useShellState, useMemo: useShellMemo } = React;

// ===========================================================================
// Shared helpers — shell-side flatten
// ===========================================================================
function flattenScene(env) {
  const idx = indexEnvelope(env);
  const scene = findScene(env);
  if (!scene) {
    return {
      idx,
      items: env.fragments,
      choices: env.fragments.filter(f => f.fragment_type === "choice"),
    };
  }
  const items = scene.member_ids.map(id => idx.byUid[id]).filter(Boolean);
  return { idx, scene, items,
    choices: items.filter(f => f.fragment_type === "choice") };
}

// ===========================================================================
// ScrollShell — linear journal
// ===========================================================================

function ScrollShell({ envelope, onPick, onCommand }) {
  const { idx, items, choices } = flattenScene(envelope);
  const hasCmd = choices.some(c => c.edge_id === "interpret_command");
  const byUid = idx.byUid;

  return (
    <div className="v12-scroll-shell" role="log" aria-live="polite">
      {items.map((f) => {
        if (!f) return null;
        if (f.fragment_type === "media" && f.media_role === "cover_im") {
          return <MediaFrame key={f.uid} frag={f} />;
        }
        if (f.fragment_type === "content") {
          return <ContentBlock key={f.uid} frag={f} />;
        }
        if (f.fragment_type === "interpretation") {
          return <Interpretation key={f.uid} frag={f} />;
        }
        if (f.fragment_type === "media") {
          return <MediaFrame key={f.uid} frag={f} />;
        }
        if (f.fragment_type === "group" && f.group_type === "dialog") {
          return <DialogGroup key={f.uid} group={f} byUid={byUid} />;
        }
        if (f.fragment_type === "kv") {
          return <KvInlineStrip key={f.uid} frag={f} />;
        }
        if (f.fragment_type === "roll") {
          return <RollWidget key={f.uid} frag={f} />;
        }
        return null;
      })}

      <ChoiceList choices={choices} env={envelope} onCommit={onPick} />
      {hasCmd && <CommandBar env={envelope} onSubmit={onCommand} />}
    </div>
  );
}

// ===========================================================================
// DossierShell — stage column + projected rail
// ===========================================================================

function DossierShell({ envelope, projected, onPick, onCommand }) {
  const { idx, items, choices } = flattenScene(envelope);
  const hasCmd = choices.some(c => c.edge_id === "interpret_command");
  const byUid = idx.byUid;

  return (
    <div className="v12-dossier-shell">
      <div className="dos-stage">
        {items.map((f) => {
          if (!f) return null;
          if (f.fragment_type === "media" && f.media_role === "cover_im") {
            return <MediaFrame key={f.uid} frag={f} />;
          }
          if (f.fragment_type === "content") {
            return <ContentBlock key={f.uid} frag={f} />;
          }
          if (f.fragment_type === "interpretation") {
            return <Interpretation key={f.uid} frag={f} />;
          }
          if (f.fragment_type === "media") {
            return <MediaFrame key={f.uid} frag={f} />;
          }
          if (f.fragment_type === "group" && f.group_type === "dialog") {
            return <DialogGroup key={f.uid} group={f} byUid={byUid} />;
          }
          if (f.fragment_type === "kv") {
            return <KvInlineStrip key={f.uid} frag={f} />;
          }
          if (f.fragment_type === "roll") {
            return <RollWidget key={f.uid} frag={f} />;
          }
          return null;
        })}

        <div style={{marginTop: "auto"}}>
          <ChoiceList choices={choices} env={envelope} onCommit={onPick} />
          {hasCmd && <CommandBar env={envelope} onSubmit={onCommand} />}
        </div>
      </div>
      <div className="dos-rail">
        {(projected?.sections || []).map((s) => <RailSection key={s.section_id} section={s} />)}
        {(!projected || projected.sections.length === 0) && (
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:11, fontStyle:"italic"}}>
            (no projected sections)
          </div>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// StageLogShell — VN-style caption + every fragment listed as a log row
// ===========================================================================

function StageLogShell({ envelope, onPick }) {
  const { idx, items, choices } = flattenScene(envelope);
  const byUid = idx.byUid;
  const dialogGroup = items.find(f => f.fragment_type === "group" && f.group_type === "dialog");
  let captionLines = [];
  if (dialogGroup) {
    const members = membersOf(dialogGroup, byUid);
    captionLines = members.filter(m => m.fragment_type === "attributed");
  }
  const current = captionLines[captionLines.length - 1];

  // Build log rows from the scene members
  const log = items.flatMap((f) => {
    if (!f) return [];
    if (f.fragment_type === "content")     return [{ kind: "content", text: short(f.content) }];
    if (f.fragment_type === "attributed")  return [{ kind: "attributed", text: `${f.who}: ${short(f.content)}` }];
    if (f.fragment_type === "media")       return [{ kind: "media", text: `${f.media_role || "inline"} · ${f.content_format}` }];
    if (f.fragment_type === "kv")          return [{ kind: "kv", text: `${f.content.length} keys` }];
    if (f.fragment_type === "choice")      return [{ kind: "choice", text: f.text }];
    if (f.fragment_type === "roll")        return [{ kind: "roll", text: `${f.label} → ${f.outcome}` }];
    if (f.fragment_type === "group")       return [{ kind: "group", text: `${f.group_type} ×${f.member_ids?.length||0}` }];
    if (f.fragment_type === "interpretation") return [{ kind: "interp", text: `${f.result}: ${f.text}` }];
    return [];
  });

  return (
    <div className="v12-stage-shell">
      <div className="stage-top">
        <div className="stage-bg" />
        <div className="stage-tag">scene · {envelope.metadata?.world || "—"}</div>
        <div className="stage-chars">
          <div className="stage-char">Bram</div>
          <div className={"stage-char" + (current ? " speaking" : "")}>{current?.who || "Stranger"}</div>
          <div className="stage-char">Elen</div>
        </div>
        {current && (
          <div className="stage-caption">
            <span className="who">{current.who} — {current.how}</span>
            <span>{current.content}</span>
          </div>
        )}
      </div>
      <div className="stage-log" aria-label="fragment log">
        {log.map((r, i) => (
          <div key={i} className={"log-row" + (r.kind === "attributed" ? " current" : "")}>
            <span className="t">+0:0{i}</span>
            <span className="kind">{r.kind}</span>
            <span>{r.text}</span>
          </div>
        ))}
      </div>
      <div className="stage-choices">
        {choices
          .filter(c => c.edge_id !== "interpret_command")
          .map((c, i) => (
          <button
            key={c.uid}
            className={"stage-choice" + (c.available ? "" : " locked")}
            disabled={!c.available}
            onClick={() => c.available && onPick && onPick(c)}
          >
            <span className="key">{c.ui_hints?.hotkey || (i+1)}</span>
            <span>{c.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function short(s, n = 60) {
  if (typeof s !== "string") return String(s);
  return s.length > n ? s.slice(0, n) + "…" : s;
}

Object.assign(window, { ScrollShell, DossierShell, StageLogShell, flattenScene });
