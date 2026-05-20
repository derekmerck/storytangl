// v12-widgets.jsx — primitive widgets shared by every shell.
//
// One widget per fragment type or value_type. Each is a small pure render —
// no internal state unless explicitly noted. State (e.g. catalog selection,
// drag candidate) is held by the shell that hosts them.
//
// Indexing helpers at the top let widgets do constant-time UID/zone lookups
// without re-walking envelope.fragments.

const { useMemo, useState, useEffect, useRef } = React;

// ============================================================================
// Indexing helpers
// ============================================================================

function indexEnvelope(env) {
  const byUid = Object.create(null);
  const piecesById = Object.create(null);   // piece_id → fragment
  const zonesByUid = Object.create(null);
  for (const f of env.fragments) {
    byUid[f.uid] = f;
    if (f.fragment_type === "piece") {
      piecesById[f.piece_id] = f;
    }
    if (f.fragment_type === "group" && f.group_type === "zone") {
      zonesByUid[f.uid] = f;
    }
  }
  // helper to read piece by either uid or piece_id
  const piece = (id) => piecesById[id] || (byUid[id] && byUid[id].fragment_type === "piece" ? byUid[id] : null);
  return { byUid, piecesById, zonesByUid, piece };
}

function findScene(env) {
  return env.fragments.find(f => f.fragment_type === "group" && f.group_type === "scene") || null;
}

function membersOf(group, byUid) {
  if (!group) return [];
  return (group.member_ids || []).map(id => byUid[id]).filter(Boolean);
}

// ============================================================================
// §2.1 / §2.2 — Content + Attributed (prose & dialog)
// ============================================================================

function ContentBlock({ frag }) {
  const tags = frag.hints?.style_tags || [];
  const isHeader = tags.includes("establishing") || tags.includes("chapter");
  const isEcho = tags.includes("echo");
  if (frag.content_format === "md") {
    return (
      <div className={"w-content" + (isHeader ? " is-header" : "") + (isEcho ? " is-echo" : "")}>
        {renderMdInline(frag.content)}
      </div>
    );
  }
  return <div className="w-content">{String(frag.content)}</div>;
}

// Minimal md inline: **bold**, *em*, _i_; preserve paragraph breaks
function renderMdInline(text) {
  if (text == null) return null;
  const paras = String(text).split(/\n\n+/);
  return paras.map((p, i) => (
    <p key={i} style={{margin: i === 0 ? 0 : "0.7em 0 0"}} dangerouslySetInnerHTML={{
      __html: p
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/_(.+?)_/g, "<em>$1</em>")
    }} />
  ));
}

function DialogGroup({ group, byUid }) {
  const members = membersOf(group, byUid);
  // Bind avatar_im/dialog_im to the preceding attributed line.
  const lines = [];
  for (const m of members) {
    if (m.fragment_type === "attributed") {
      lines.push({ ...m, attached: [] });
    } else if (m.fragment_type === "media") {
      if (lines.length) lines[lines.length - 1].attached.push(m);
    }
  }
  return (
    <div className="w-dialog" role="group" aria-label="dialog" aria-live="polite">
      {lines.map((l, i) => {
        const avatar = l.attached.find(m => m.media_role === "avatar_im");
        const pending = l.attached.find(m => m.generation_status === "pending");
        return (
          <div key={i} className="w-dialog-line">
            <div className="w-avatar">
              {avatar ? <span className="ph">AV</span> : <span className="ph">?</span>}
            </div>
            <div className="w-dialog-body">
              <div className="w-dialog-attr">
                <b className="w-who">{l.who}</b>
                <span className="w-how">({l.how})</span>
              </div>
              <div className="w-said">{l.content}</div>
              {pending && (
                <div className="w-media-pending">[dialog_im · generating · {pending.content}]</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ============================================================================
// §2.3 — Media (cover_im / narrative_im / pending RIT)
// ============================================================================

function MediaFrame({ frag }) {
  const role = frag.media_role || "inline";
  const pending = frag.content_format === "rit" || frag.generation_status === "pending";
  const cls = "w-media w-media-" + role + (pending ? " is-pending" : "");
  return (
    <div className={cls} role="img" aria-label={role.replace("_", " ")}>
      <span className="w-media-tag">
        {role} · {pending ? "pending" : frag.content_format}
      </span>
      <span className="w-media-name">
        {pending ? frag.content : (frag.content || "").split("/").pop()}
      </span>
    </div>
  );
}

// ============================================================================
// §2.5 — KvFragment and KvRow (unified)
// Inline strip variant for scene-bound; rail variant in DossierShell uses
// AnnotatedKvRow directly.
// ============================================================================

function KvInlineStrip({ frag }) {
  const rows = Array.isArray(frag.content) ? frag.content : [];
  return (
    <div className="w-kv-inline" role="group" aria-label="scene status">
      {rows.map((r, i) => {
        // unified shape: object {key, value, unit?}; tolerant of legacy [k,v]
        const k = r.key ?? (Array.isArray(r) ? r[0] : "?");
        const v = r.value ?? (Array.isArray(r) ? r[1] : "");
        const unit = r.unit;
        return (
          <span key={i} className="w-kv-pair">
            <span className="k">{k}:</span> <b className="v">{String(v)}{unit ? ` ${unit}` : ""}</b>
          </span>
        );
      })}
    </div>
  );
}

// A single annotated kv row — used by Ledger and projected kv_list.
function AnnotatedKvRow({ row }) {
  const pct = row.max ? Math.max(0, Math.min(1, (Number(row.value) || 0) / row.max)) : 0;
  const emph = row.emphasis || "";
  const hint = row.hint || (row.max != null ? "bar" : null);
  return (
    <div className={"kvrow " + emph}>
      <span className="k">{row.key}</span>
      {hint === "bar" && (
        <span className="v" style={{display:"inline-flex", alignItems:"center", gap:8}}>
          <span className="bar"><span className="fill" style={{width: `${pct*100}%`}} /></span>
          <span>{row.value}/{row.max}{row.unit ? ` ${row.unit}` : ""}</span>
        </span>
      )}
      {hint === "fraction" && (
        <span className="v">{row.value}/{row.max}{row.unit ? ` ${row.unit}` : ""}</span>
      )}
      {hint === "delta" && (
        <span className="v">
          <span className={"delta " + (row.delta > 0 ? "up" : "down")}>
            {row.delta > 0 ? "+" : ""}{row.delta}
          </span>
        </span>
      )}
      {!hint && (
        <span className="v">{String(row.value ?? "")}{row.unit ? ` ${row.unit}` : ""}</span>
      )}
    </div>
  );
}

// ============================================================================
// §2.6 / §6.1 — Choice (pick / quantity / pieces / place / compose / text / raw_command)
// ============================================================================

function ChoiceList({ choices, env, onCommit, options }) {
  const opts = options || {};
  // hide reserved interpret_command (rendered by CommandBar)
  const visible = choices.filter(c =>
    !(c.ui_hints?.reserved === "command_bar" || c.edge_id === "interpret_command")
  );
  return (
    <div className="choices-v12" role="group" aria-label="choices">
      {visible.map((c, i) => (
        <ChoiceRow key={c.uid} c={c} idx={i+1} env={env}
          onCommit={onCommit} showSource={opts.showSource} />
      ))}
    </div>
  );
}

function ChoiceRow({ c, idx, env, onCommit, showSource }) {
  const ak = c.accepts?.kind;
  const acceptsLabel = ak ? `accepts: ${ak}` : null;
  const cps = c.ui_hints?.cost_previews || [];
  const sc = c.ui_hints?.stat_check;
  const td = c.ui_hints?.time_delta;
  const sourceKind = c.ui_hints?.source_kind;

  return (
    <button
      type="button"
      className={"choice-v12" + (c.available ? "" : " locked")}
      onClick={() => c.available && onCommit && onCommit(c)}
      disabled={!c.available}
      aria-disabled={!c.available}
    >
      <span className="key">{c.ui_hints?.hotkey || idx}</span>
      <span className="label">
        {showSource && sourceKind && (
          <span className="source-tag">{sourceKind}</span>
        )}
        {c.text}
        {acceptsLabel && ak !== "pick" && <span className="accepts">{acceptsLabel}</span>}
        {sc && (
          <span className="statcheck-badge" style={{marginLeft:8}}>
            {sc.label} · {sc.dice} vs {sc.target}
            {sc.modifier ? ` (${sc.modifier > 0 ? "+" : ""}${sc.modifier})` : ""}
            {sc.success_text && <span style={{marginLeft:4}}>· {sc.success_text}</span>}
          </span>
        )}
        {!c.available && (
          <div className="reason">{c.unavailable_reason}</div>
        )}
      </span>
      <span className="meta">
        {cps.filter(cp => cp.delta !== 0).map((cp, i) => (
          <span key={i} className={"cost " + (cp.delta < 0 ? "down" : "up")}>
            {cp.delta < 0 ? "−" : "+"}{Math.abs(cp.delta)} {cp.unit}
          </span>
        ))}
        {td && (
          <span className="cost">→ {td.arrives_at}</span>
        )}
      </span>
    </button>
  );
}

// ============================================================================
// §6.5 — Command bar (wraps the reserved interpret_command choice)
// ============================================================================

function CommandBar({ env, onSubmit }) {
  const [text, setText] = useState("");
  const grammar = env.metadata?.grammar;
  const placeholder = grammar?.placeholder || "type a command…";
  return (
    <form
      className="cmdbar"
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim() && onSubmit) onSubmit({ text });
        setText("");
      }}
    >
      <span className="prompt">&gt;</span>
      <input
        type="text"
        placeholder={placeholder}
        value={text}
        onChange={(e) => setText(e.target.value)}
        aria-label="command"
      />
      <span className="hint-chip">
        {grammar ? `${grammar.verbs?.length || 0} verbs · ${grammar.nouns?.length || 0} nouns` : "no grammar"}
      </span>
    </form>
  );
}

// ============================================================================
// §6.4 — InterpretationFragment
// ============================================================================

function Interpretation({ frag }) {
  const cls =
    frag.result === "blocked" ? "blocked" :
    frag.result === "ambiguous" ? "ambig" :
    frag.result === "unknown_verb" || frag.result === "unknown_noun" ? "ambig" :
    frag.result === "validation_failed" ? "blocked" : "ok";
  return (
    <div className={"interp " + cls} role="status" aria-live="polite">
      <div className="result">{frag.result.replace("_", " ")}</div>
      <div>
        <div className="echo">&gt; <b>{frag.text}</b></div>
        <div className="msg">{frag.message}</div>
        {frag.candidates && frag.candidates.length > 0 && (
          <div className="candidates">
            candidates: {frag.candidates.map(x => <code key={x} style={{marginRight:6}}>{x}</code>)}
          </div>
        )}
        {frag.hint && <div className="candidates">hint: {frag.hint}</div>}
      </div>
    </div>
  );
}

// ============================================================================
// §7.1 — PieceFragment widget (chip form)
// ============================================================================

function PieceChip({ piece, selected, onClick, disabled, env }) {
  const props = piece.properties || {};
  const isOffer = piece.realized === false;
  const cost = isOffer && piece.cost && piece.cost[0];
  return (
    <button
      type="button"
      className={"piece" + (isOffer ? " offer" : "") + (selected ? " selected" : "") + (disabled || !piece.available && isOffer ? " disabled" : "")}
      onClick={onClick}
      disabled={disabled}
    >
      <span className="p-kind">{piece.kind}</span>
      <span>
        <span className="p-name">{piece.hints?.label_text || props.name || piece.piece_id}</span>
        <span className="p-meta">
          {props.weight != null && <>{props.weight} wt</>}
          {props.ammo != null && <> · {props.ammo} ammo</>}
          {props.armor != null && <> · {props.armor} ar</>}
        </span>
      </span>
      {cost && (
        <span className="p-cost">
          {cost.delta < 0 ? "−" : "+"}{Math.abs(cost.delta)} {cost.unit}
        </span>
      )}
    </button>
  );
}

// ============================================================================
// §7.2 — Zone widget (generic) + Slot variant (with capacity bar)
// ============================================================================

function ZoneTile({ zone, env, byUid, selectedIds, onPieceClick, dragCandidate, dragTargets }) {
  const members = (zone.member_ids || []).map(id => byUid[id]).filter(Boolean);
  const role = zone.layout_hints?.zone_role || "field";
  const isSlot = role === "slot";

  // Slot variant: render capacity bar + visual feedback during drag
  if (isSlot) {
    return <SlotZone zone={zone} env={env} byUid={byUid}
              selectedIds={selectedIds} onPieceClick={onPieceClick}
              dragCandidate={dragCandidate} dragTargets={dragTargets} />;
  }

  return (
    <div className={"zone " + role}>
      <div className="zone-hd">
        <span>{zone.hints?.label_text || zone.uid}</span>
        <span className="role">{role}</span>
      </div>
      <div className={"zone-body" + (members.length === 0 ? " empty" : "")}>
        {members.length === 0 && <span>(empty)</span>}
        {members.map(m => {
          if (m.fragment_type !== "piece") return null;
          const sel = selectedIds?.includes(m.piece_id);
          return <PieceChip key={m.uid} piece={m} env={env}
            selected={sel}
            onClick={onPieceClick ? () => onPieceClick(m, zone) : undefined} />;
        })}
      </div>
    </div>
  );
}

function SlotZone({ zone, env, byUid, onPieceClick, dragCandidate, dragTargets }) {
  const members = (zone.member_ids || []).map(id => byUid[id]).filter(p => p && p.fragment_type === "piece");
  const cap = (zone.constraints?.capacity || []);
  const acceptsKind = zone.constraints?.accepts_kind || null;
  const isDropTarget = dragTargets?.includes(zone.uid);
  const wrongKind = dragCandidate && acceptsKind &&
                    !acceptsKind.includes(dragCandidate.kind);

  // pick the dominant capacity row to render as a bar — prefer weight-style
  const weightCap = cap.find(c => c.kind === "weight" || c.kind === "power") || cap.find(c => c.kind === "count");
  let occ = 0, projected = 0;
  if (weightCap) {
    if (weightCap.sum_property) {
      occ = members.reduce((s, p) => s + (p.properties?.[weightCap.sum_property] || 0), 0);
      const cand = dragCandidate?.properties?.[weightCap.sum_property] || 0;
      projected = occ + (isDropTarget && !wrongKind ? cand : 0);
    } else {
      occ = members.length;
      projected = occ + (isDropTarget && !wrongKind ? 1 : 0);
    }
  }
  const over = weightCap && projected > weightCap.max;
  const className = "zone slot " +
    (isDropTarget && !wrongKind && !over ? "ok-drop " : "") +
    (isDropTarget && (wrongKind || over) ? "over " : "");

  return (
    <div className={className}>
      <div className="zone-hd">
        <span>{zone.hints?.label_text || zone.uid}</span>
        <span className="cap">
          {acceptsKind && acceptsKind.join("/")}
          {weightCap && <> · {occ}/{weightCap.max} {weightCap.unit}</>}
        </span>
      </div>
      <div className="zone-body" style={{flexDirection:"column", gap:6}}>
        {members.length === 0 && (
          <div className="muted" style={{fontFamily:"var(--mono)", fontSize:10.5, fontStyle:"italic"}}>(empty)</div>
        )}
        {members.map(m => (
          <PieceChip key={m.uid} piece={m} env={env}
            onClick={onPieceClick ? () => onPieceClick(m, zone) : undefined} />
        ))}
        {weightCap && (
          <div className={"cap-bar" + (over ? " over" : "")}>
            <div className="fill" style={{width: `${Math.min(100, (occ/weightCap.max)*100)}%`}} />
            {dragCandidate && isDropTarget && !wrongKind && (
              <div className="ghost" style={{
                left: `${Math.min(100, (occ/weightCap.max)*100)}%`,
                width: `${Math.max(0, Math.min(100 - (occ/weightCap.max)*100, ((projected-occ)/weightCap.max)*100))}%`
              }} />
            )}
          </div>
        )}
        {isDropTarget && wrongKind && (
          <div style={{fontFamily:"var(--mono)", fontSize:9.5, color:"var(--bad)"}}>
            wrong kind — {acceptsKind?.join("/")} only
          </div>
        )}
        {isDropTarget && over && !wrongKind && (
          <div style={{fontFamily:"var(--mono)", fontSize:9.5, color:"var(--bad)"}}>
            over capacity — {projected}/{weightCap.max}
          </div>
        )}
      </div>
    </div>
  );
}

// Catalog: zone_role=catalog showing offer pieces as cards
function CatalogGrid({ zone, env, byUid, selectedIds, onToggle, walletValue }) {
  const offers = (zone.member_ids || [])
    .map(id => byUid[id]).filter(p => p && p.fragment_type === "piece");
  return (
    <div className="catalog-grid">
      {offers.length === 0 && <div className="muted">(no offers)</div>}
      {offers.map(o => {
        const cost = o.cost && o.cost[0];
        const overWallet = cost && walletValue != null && Math.abs(cost.delta) > walletValue && cost.delta < 0;
        const disabled = !o.available || overWallet;
        const sel = selectedIds?.includes(o.piece_id);
        return (
          <button key={o.uid} type="button"
            className={"offer-card" + (sel ? " selected" : "") + (disabled ? " disabled" : "")}
            onClick={() => !disabled && onToggle && onToggle(o.piece_id)}
            aria-pressed={sel} aria-disabled={disabled}>
            <div className="offer-hd">
              <span className="offer-name">{o.hints?.label_text || o.properties?.name}</span>
              {cost && (
                <span className="offer-cost">
                  {cost.delta < 0 ? "−" : "+"}{Math.abs(cost.delta)} {cost.unit}
                </span>
              )}
            </div>
            <div className="offer-meta">
              <span>{o.kind}</span>
              {o.properties?.weight != null && <span>{o.properties.weight} wt</span>}
              {o.properties?.ammo != null && <span>{o.properties.ammo} ammo</span>}
              {o.properties?.armor != null && <span>+{o.properties.armor} armor</span>}
            </div>
            {o.hints?.description_text && (
              <div className="offer-desc">{o.hints.description_text}</div>
            )}
            {!o.available && o.unavailable_reason && (
              <div className="offer-reason">{o.unavailable_reason}</div>
            )}
            {o.available && overWallet && (
              <div className="offer-reason">not enough credit</div>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ============================================================================
// §7.3 — RollFragment (dice ritual + skip)
// ============================================================================

function RollWidget({ frag, defaultSkipped }) {
  const [revealed, setRevealed] = useState(defaultSkipped ? true : false);
  const [skipped, setSkipped] = useState(false);
  const durationMs = frag.ritual_hints?.duration_ms || 1200;

  useEffect(() => {
    if (revealed || skipped || defaultSkipped) return;
    const t = setTimeout(() => setRevealed(true), durationMs);
    return () => clearTimeout(t);
  }, [revealed, skipped, defaultSkipped, durationMs]);

  const c = frag.inputs || {};
  const showResult = revealed || skipped;
  const skipLabel = frag.ritual_hints?.skip_label || "Skip";

  return (
    <div className={"roll outcome-" + frag.outcome}>
      {!showResult && (
        <button type="button" className="roll-skip" onClick={() => setSkipped(true)}>
          {skipLabel} →
        </button>
      )}
      <div className="roll-head">
        <span>{frag.label || "roll"}</span>
        <span className="target">
          {c.dice} vs {c.target}{c.modifier ? ` (${c.modifier > 0 ? "+" : ""}${c.modifier})` : ""}
        </span>
      </div>
      <div className="roll-dice">
        {(c.rolled || []).map((n, i) => (
          <span key={i} className={"die" + (showResult ? "" : " rolling")}>
            {showResult ? n : "?"}
          </span>
        ))}
        <span className="roll-eq">=</span>
        <span className="roll-total">{showResult ? c.total : "…"}</span>
        <span className={"roll-outcome " + (showResult ? frag.outcome : "")}>
          {showResult ? frag.outcome.replace("_", " ") : "rolling"}
        </span>
      </div>
      {showResult && frag.narrative && (
        <div className="roll-narrative">{frag.narrative}</div>
      )}
    </div>
  );
}

// ============================================================================
// §3 — Projected section renderers (rail variant)
// ============================================================================

function RailSection({ section }) {
  const v = section.value;
  return (
    <div className="rail-section">
      <h4>{section.title}<span className="tag">{v.value_type}</span></h4>
      <div className="body">
        {v.value_type === "scalar" && (
          <div className="rail-scalar">{String(v.value)}</div>
        )}
        {v.value_type === "kv_list" && (
          <div style={{display:"grid"}}>
            {v.items.map((it, i) => <AnnotatedKvRow key={i} row={it} />)}
          </div>
        )}
        {v.value_type === "item_list" && (
          <div className="rail-items">
            {v.items.map((it, i) => (
              <div key={i} className="item">
                <div className="label">{it.label}</div>
                {it.detail && <div className="detail">{it.detail}</div>}
                {it.tags?.length > 0 && (
                  <div className="tags">
                    {it.tags.map((t, j) => <span key={j} className="tag">{t}</span>)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        {v.value_type === "table" && (
          <table style={{width:"100%", fontSize:10, borderCollapse:"collapse"}}>
            <thead><tr>
              {v.columns.map((c, i) => (
                <th key={i} style={{textAlign:"left", color:"var(--ink-3)",
                                    borderBottom:"1px solid var(--rule)",
                                    padding:"2px 4px"}}>{c}</th>
              ))}
            </tr></thead>
            <tbody>
              {v.rows.map((r, i) => (
                <tr key={i}>
                  {r.map((cell, j) => (
                    <td key={j} style={{padding:"2px 4px", borderBottom:"1px dotted var(--rule)"}}>{String(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {v.value_type === "badges" && (
          <div className="rail-badges">
            {v.items.map((b, i) => <span key={i} className="rail-badge">{b}</span>)}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Export to global scope so other Babel scripts can use them
// ============================================================================

Object.assign(window, {
  // helpers
  indexEnvelope, findScene, membersOf, renderMdInline,
  // fragment widgets
  ContentBlock, DialogGroup, MediaFrame,
  KvInlineStrip, AnnotatedKvRow,
  ChoiceList, ChoiceRow, CommandBar, Interpretation,
  // piece/zone (P2)
  PieceChip, ZoneTile, SlotZone, CatalogGrid,
  // roll (P2)
  RollWidget,
  // projected
  RailSection,
});
