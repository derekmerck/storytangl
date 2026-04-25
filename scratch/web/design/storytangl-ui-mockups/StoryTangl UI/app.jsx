/* StoryTangl wireframes — main app */

const { useState, useEffect, useMemo, useRef, useCallback } = React;

// ---------- Fake engine ----------
function useEngine(sceneKey) {
  const scene = window.SCENE;
  const [cursor, setCursor] = useState(scene.start);
  const [step, setStep] = useState(1);
  const [history, setHistory] = useState([]); // past blocks [{id, title, text, choiceTaken, ts}]
  const [state, setState] = useState({ visited: [], met: [], flags: [], knowledge: [], locations: [] });

  const current = scene.blocks[cursor];

  const choose = useCallback((action) => {
    if (!action || !action.to) return;
    const next = scene.blocks[action.to];
    setHistory((h) => [...h, {
      id: current.id,
      title: current.title,
      text: current.text,
      speaker: current.speaker,
      media: current.media,
      choice: action.text,
      step,
    }]);
    // merge state delta
    const d = next.stateDelta || {};
    setState((s) => ({
      visited: Array.from(new Set([...(s.visited||[]), ...(d.visited||[])])),
      met: Array.from(new Set([...(s.met||[]), ...(d.met||[])])),
      flags: Array.from(new Set([...(s.flags||[]), ...(d.flags||[])])),
      knowledge: Array.from(new Set([...(s.knowledge||[]), ...(d.knowledge||[])])),
      locations: Array.from(new Set([...(s.locations||[]), ...(d.locations||[])])),
    }));
    setCursor(action.to);
    setStep((n) => n + 1);
  }, [current, step, scene]);

  const reset = useCallback(() => {
    setCursor(scene.start);
    setStep(1);
    setHistory([]);
    setState({ visited: [], met: [], flags: [], knowledge: [], locations: [] });
  }, [scene]);

  return { scene, current, cursor, step, history, state, choose, reset };
}

// ---------- Shared widget primitives ----------
function PhImg({ kind = "landscape", label, tag, style }) {
  return (
    <div className={`ph-img ${kind}`} style={style}>
      <div className="ph-x"></div>
      <span>{label || "media placeholder"}</span>
      {tag && <span className="tag">{tag}</span>}
    </div>
  );
}

function ChoiceList({ actions, onChoose, compact = false }) {
  if (!actions || !actions.length) {
    return <div className="muted mono tiny" style={{padding:"6px 0"}}>— end of thread —</div>;
  }
  return (
    <div className="choices">
      {actions.map((a, i) => (
        <button key={a.id} className="choice" onClick={() => onChoose(a)}>
          <span className="kbd">{i + 1}</span>
          <span>{a.text}</span>
          <span className="arr">→</span>
        </button>
      ))}
    </div>
  );
}

function DialogLine({ speaker, text }) {
  return (
    <div className="dialog">
      <div className="av">{speaker?.avatar ? "IMG" : "?"}</div>
      <div>
        <div className="who">{speaker?.name || "Narrator"}</div>
        <div className="said">{text}</div>
      </div>
    </div>
  );
}

function Prose({ text }) {
  const paras = text.split("\n\n");
  return (
    <div className="prose">
      {paras.map((p, i) => <p key={i}>{p}</p>)}
    </div>
  );
}

function StatusPanel({ title, state, extra }) {
  return (
    <div className="panel">
      <div className="panel-hd"><span>{title}</span><span className="muted">kv</span></div>
      <div className="panel-bd">
        <div className="kv">
          <span className="k">step</span><span className="v">{extra?.step ?? "—"}</span>
          <span className="k">cursor</span><span className="v">{extra?.cursor ?? "—"}</span>
          <span className="k">scene</span><span className="v">{extra?.scene ?? "—"}</span>
          <span className="k">visited</span><span className="v">{(state.visited||[]).length}</span>
          <span className="k">met</span><span className="v">{(state.met||[]).length}</span>
          <span className="k">flags</span><span className="v">{(state.flags||[]).length}</span>
        </div>
      </div>
    </div>
  );
}

function BadgePanel({ title, items, empty = "—" }) {
  return (
    <div className="panel">
      <div className="panel-hd"><span>{title}</span><span className="muted">badges</span></div>
      <div className="panel-bd">
        <div className="badges">
          {(items && items.length) ? items.map((b, i) => (
            <span key={i} className="badge on">{b}</span>
          )) : <span className="badge dim">{empty}</span>}
        </div>
      </div>
    </div>
  );
}

function ItemList({ title, items, hint }) {
  return (
    <div className="panel">
      <div className="panel-hd"><span>{title}</span><span className="muted">{hint || "item_list"}</span></div>
      <div className="panel-bd">
        {items && items.length ? (
          <div className="item-list">
            {items.map((it, i) => (
              <div className="it" key={i}>
                <span className="lbl">{it.name}</span>
                <span className="meta">{it.kind} · cost {it.cost}</span>
              </div>
            ))}
          </div>
        ) : <div className="muted mono tiny">(empty)</div>}
      </div>
    </div>
  );
}

function CardMini({ card }) {
  return (
    <div className="cardv">
      <span className="c-cost">{card.cost}</span>
      <div className="c-hd"><span>{card.kind}</span><span>{card.id}</span></div>
      <div className="c-name">{card.name}</div>
      <div className="c-art"></div>
      <div className="c-tx">{card.text}</div>
    </div>
  );
}

// ---------- Shells ----------
function DossierShell({ engine }) {
  const { current, state, choose, history, step, cursor } = engine;
  return (
    <div className="dossier">
      <div className="col left">
        <h4 className="col-h">Dossier · Left rail</h4>
        <div className="sub-stack">
          <StatusPanel title="Ledger" state={state} extra={{ step, cursor, scene: current.scene }} />
          <BadgePanel title="Companions & met" items={state.met} empty="no one yet" />
          <BadgePanel title="Locations" items={state.locations} empty="starting area" />
          <BadgePanel title="Knowledge / flags" items={[...state.knowledge, ...state.flags]} empty="none" />
        </div>
      </div>
      <div className="col mid">
        <div className="crumbs">
          fabula › <b>{current.scene}</b> › <b>{current.id.split(".").pop()}</b>
          <span style={{marginLeft:8}} className="pill pill--ghost">step {step}</span>
        </div>

        {current.media && current.media.kind === "landscape" && (
          <PhImg kind="landscape" label={current.media.label} tag="narrative_im" style={{marginBottom: 14}} />
        )}

        <div className="block-kicker">{current.scene} / {current.id.split(".").pop()}</div>
        <h3 className="block-title">{current.title}</h3>

        {current.speaker ? (
          <>
            {current.media && current.media.kind === "portrait" && (
              <div style={{float:"right", width:160, marginLeft:16, marginBottom:8}}>
                <PhImg kind="portrait" label={current.media.label} tag="avatar_im" />
              </div>
            )}
            <DialogLine speaker={current.speaker} text={current.text} />
          </>
        ) : (
          <Prose text={current.text} />
        )}

        <div style={{marginTop: 18}}>
          <div className="block-kicker">Choices</div>
          <ChoiceList actions={current.actions} onChoose={choose} />
        </div>
      </div>
      <div className="col right">
        <h4 className="col-h">Right rail</h4>
        <div className="sub-stack">
          <ItemList title="Deck (speculative CCG)" items={window.SCENE.cards} hint="card-view" />
          <div className="panel">
            <div className="panel-hd"><span>History</span><span className="muted">journal</span></div>
            <div className="panel-bd" style={{fontFamily: "var(--mono)", fontSize: 11, maxHeight: 180, overflowY: "auto"}}>
              {history.length === 0 && <span className="muted">(no steps yet)</span>}
              {history.map((h, i) => (
                <div key={i} style={{padding: "4px 0", borderBottom: "1px dashed var(--rule)"}}>
                  <div style={{color: "var(--ink-3)"}}>#{h.step} · {h.id}</div>
                  <div style={{color: "var(--accent-ink)"}}>↳ {h.choice}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="margin-note">
            Dossier keeps the engine's structured sidecar data (kv, badges, item_list, table)
            visible across every step — matching what the CLI's <span className="mono">status</span> shows.
          </div>
        </div>
      </div>
    </div>
  );
}

function ScrollShell({ engine }) {
  const { current, history, choose, step } = engine;
  const bottomRef = useRef(null);
  useEffect(() => {
    bottomRef.current?.parentElement?.scrollTo({ top: 99999, behavior: "smooth" });
  }, [step]);
  return (
    <div className="scroll" style={{maxHeight: 520, overflowY: "auto"}}>
      {history.map((h, i) => (
        <div className="entry past" key={i}>
          <div className="step-idx">step {h.step} · {h.id}</div>
          {h.media && h.media.kind === "landscape" && (
            <div style={{maxWidth: 520, marginBottom: 10}}>
              <PhImg kind="landscape" label={h.media.label} tag="narrative_im" />
            </div>
          )}
          <h3 className="block-title">{h.title}</h3>
          {h.speaker ? <DialogLine speaker={h.speaker} text={h.text} /> : <Prose text={h.text} />}
          <div className="mono tiny" style={{marginTop: 6, color: "var(--accent-ink)"}}>↳ {h.choice}</div>
        </div>
      ))}
      <div className="entry">
        <div className="step-idx">step {step} · {current.id} · current</div>
        {current.media && current.media.kind === "landscape" && (
          <div style={{maxWidth: 640, marginBottom: 10}}>
            <PhImg kind="landscape" label={current.media.label} tag="narrative_im" />
          </div>
        )}
        <h3 className="block-title">{current.title}</h3>
        {current.speaker ? <DialogLine speaker={current.speaker} text={current.text} /> : <Prose text={current.text} />}
        <div style={{marginTop: 12, maxWidth: 540}}>
          <ChoiceList actions={current.actions} onChoose={choose} />
        </div>
        <div ref={bottomRef}></div>
      </div>
    </div>
  );
}

function StageLogShell({ engine }) {
  const { current, history, choose, step } = engine;
  return (
    <div className="stage-log">
      <div className="stage">
        <PhImg
          kind="landscape"
          label={current.media?.label || "stage · no media"}
          tag={current.media?.role || "scene"}
        />
        <div className="stage-meta">
          <div>
            <div className="block-kicker">{current.scene}</div>
            <h3 className="block-title">{current.title}</h3>
            <div className="mono tiny muted">cursor · {current.id}</div>
          </div>
          <div>
            <div className="block-kicker">choices</div>
            <ChoiceList actions={current.actions} onChoose={choose} />
          </div>
        </div>
      </div>
      <div className="log">
        <div className="block-kicker" style={{marginBottom: 8}}>rolling journal</div>
        {history.length === 0 && <div className="mono tiny muted">(no steps yet — stage above is live)</div>}
        {history.map((h, i) => (
          <div key={i} className="log-entry narr">
            <span className="t mono tiny">#{h.step}</span>
            <b>{h.speaker?.name ? h.speaker.name + ": " : ""}</b>
            {h.text.split("\n\n")[0].slice(0, 140)}…
            <span className="mono tiny" style={{color: "var(--accent-ink)", marginLeft: 8}}>↳ {h.choice}</span>
          </div>
        ))}
        {/* show current as the tail */}
        <div className="log-entry narr" style={{background: "rgba(0,0,0,0.03)"}}>
          <span className="t mono tiny">#{step}</span>
          <b>{current.speaker?.name ? current.speaker.name + ": " : ""}</b>
          {current.text.split("\n\n")[0].slice(0, 160)}…
        </div>
      </div>
    </div>
  );
}

function VNShell({ engine }) {
  const { current, choose } = engine;
  return (
    <div className="vn">
      <div className="vn-media-tag">
        {current.media?.label || "no backdrop"} · narrative_im
      </div>
      {current.speaker && (
        <div className="vn-sprite">{current.speaker.name}</div>
      )}
      <div className="scrim"></div>
      <div className="vn-choices">
        {current.actions.map((a, i) => (
          <button key={a.id} className="choice" onClick={() => choose(a)}>
            <span className="kbd">{i + 1}</span>
            <span>{a.text}</span>
            <span className="arr">→</span>
          </button>
        ))}
        {current.actions.length === 0 && (
          <div className="mono tiny muted">— end of thread —</div>
        )}
      </div>
      <div className="vn-box">
        <div className="vn-who">{current.speaker?.name || current.title}</div>
        <div className="vn-said">{current.text}</div>
      </div>
    </div>
  );
}

function DeckShell({ engine }) {
  const { current, history, choose, step } = engine;
  const behind = history.slice(-2);
  return (
    <div className="deck">
      <div className="deck-stack">
        {behind[0] && (
          <div className="deck-card behind-2">
            <div className="block-kicker">#{behind[0].step} · {behind[0].id}</div>
            <h3 className="block-title">{behind[0].title}</h3>
            <div className="prose" style={{maxHeight: 120, overflow: "hidden"}}>{behind[0].text.slice(0, 120)}…</div>
          </div>
        )}
        {behind[1] && (
          <div className="deck-card behind-1">
            <div className="block-kicker">#{behind[1].step} · {behind[1].id}</div>
            <h3 className="block-title">{behind[1].title}</h3>
            <div className="prose" style={{maxHeight: 120, overflow: "hidden"}}>{behind[1].text.slice(0, 120)}…</div>
          </div>
        )}
        <div className="deck-card">
          <div className="block-kicker">step {step} · {current.id}</div>
          <h3 className="block-title">{current.title}</h3>
          {current.media && current.media.kind === "landscape" && (
            <div style={{margin: "10px 0"}}>
              <PhImg kind="landscape" label={current.media.label} tag="narrative_im" />
            </div>
          )}
          {current.speaker
            ? <DialogLine speaker={current.speaker} text={current.text} />
            : <Prose text={current.text} />}
          <div style={{marginTop: 14}}>
            <ChoiceList actions={current.actions} onChoose={choose} />
          </div>
        </div>
      </div>
      <div className="stack-md">
        <div className="margin-note">
          Each block is a card; swipe stacks into history.
          Good shell for the speculative CCG overlay — the narrative IS cards.
        </div>
        <ItemList title="Hand" items={window.SCENE.cards.slice(0, 3)} hint="card-view" />
        <div className="panel">
          <div className="panel-hd"><span>Stack</span><span className="muted">{history.length} past</span></div>
          <div className="panel-bd mono tiny">
            {history.map((h, i) => <div key={i}>#{h.step} · {h.id}</div>)}
            {history.length === 0 && <span className="muted">(empty)</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

function TerminalShell({ engine }) {
  const { current, history, choose, step } = engine;
  return (
    <div className="terminal">
      <div className="t-dim">StoryTangl cli · ledger 7f3c…a81e · user derek</div>
      <hr />
      {history.map((h, i) => (
        <div key={i} style={{marginBottom: 8}}>
          <div className="t-dim">— step {h.step} · {h.id} —</div>
          <div className="t-block">{h.text}</div>
          <div className="t-accent">↳ {h.choice}</div>
        </div>
      ))}
      <div className="t-dim">— step {step} · {current.id} —</div>
      {current.media && (
        <div className="t-dim">[media · {current.media.label} · role={current.media.role}]</div>
      )}
      {current.speaker && (
        <div className="t-accent">{current.speaker.name}:</div>
      )}
      <div className="t-block">{current.text}</div>
      <div style={{marginTop: 8}} className="t-dim">Choices:</div>
      {current.actions.map((a, i) => (
        <div key={a.id} className="t-choice" onClick={() => choose(a)}>
          <span className="t-prompt">  {i + 1}.</span> <span className="t-underline">{a.text}</span>
        </div>
      ))}
      {current.actions.length === 0 && <div className="t-dim">  (terminal — story complete)</div>}
      <div style={{marginTop: 14}}>
        <span className="t-prompt">tangl&gt;</span> <span className="t-dim">do _</span>
      </div>
    </div>
  );
}

const SHELLS = {
  dossier: { label: "Dossier split", code: "shell.dossier", comp: DossierShell, sub: "primary focus" },
  scroll:  { label: "Sugarcube scroll", code: "shell.scroll", comp: ScrollShell, sub: "today's web client" },
  stage:   { label: "Stage + log", code: "shell.stage_log", comp: StageLogShell, sub: "" },
  vn:      { label: "Visual novel", code: "shell.vn", comp: VNShell, sub: "" },
  deck:    { label: "Card deck", code: "shell.deck", comp: DeckShell, sub: "hooks into CCG idea" },
  terminal:{ label: "Terminal", code: "shell.terminal", comp: TerminalShell, sub: "cli parity" },
};

// ---------- Author / debug view ----------
function AuthorView({ engine }) {
  const { current, state, history, step, cursor, choose, scene } = engine;
  const allBlocks = Object.values(scene.blocks);
  const phases = ["VALIDATE","PLANNING","PREREQS","UPDATE","JOURNAL","FINALIZE","POSTREQS","ADVANCE"];

  const fragments = useMemo(() => {
    const f = [];
    f.push({ kind: "control", t: "phase.enter", v: "JOURNAL" });
    if (current.media) f.push({ kind: "media", t: "media_role", v: current.media.role, meta: current.media.label });
    if (current.speaker) {
      f.push({ kind: "dialog", t: current.speaker.name, v: current.text.slice(0, 80) + "…" });
    } else {
      f.push({ kind: "content", t: "prose", v: current.text.slice(0, 80) + "…" });
    }
    current.actions.forEach((a, i) => {
      f.push({ kind: "choice", t: `edge.${i+1}`, v: a.text, meta: `→ ${a.to}` });
    });
    f.push({ kind: "control", t: "phase.exit", v: "JOURNAL" });
    return f;
  }, [current]);

  return (
    <div className="author">
      <div className="col left">
        <h4 className="col-h">Graph · fabula</h4>
        <div className="graph-view">
          {/* very simple absolute-positioned node layout */}
          <GraphPreview blocks={allBlocks} cursor={cursor} history={history} />
        </div>
        <div className="mono tiny muted" style={{marginTop: 8}}>
          nodes: {allBlocks.length} · edges: {allBlocks.reduce((n,b)=>n+(b.actions?.length||0),0)} · cursor: {cursor}
        </div>
        <div className="stack-sm" style={{marginTop: 14}}>
          <div className="panel">
            <div className="panel-hd"><span>Template lineage</span><span className="muted">story</span></div>
            <div className="panel-bd mono tiny">
              <div>scene · {current.scene}</div>
              <div>block · {current.id.split(".").pop()}</div>
              <div>compiled · StoryTemplateBundle@v38.3</div>
              <div>authority · World("crossroads_inn")</div>
            </div>
          </div>
        </div>
      </div>
      <div className="col mid">
        <h4 className="col-h">Phase bus · current step</h4>
        <div className="phase-bus">
          {phases.map((p, i) => (
            <div key={p} className={`ph ${i === 4 ? "active" : i < 4 ? "done" : ""}`}>{p}</div>
          ))}
        </div>
        <div className="mono tiny muted" style={{marginBottom: 10}}>
          follow_edge(→ {cursor}) · frame.step {step} · ledger 7f3c…a81e
        </div>

        <h4 className="col-h" style={{marginTop: 10}}>Emitted fragments</h4>
        <div className="receipts">
          {fragments.map((f, i) => (
            <div key={i} className="row">
              <span className="dispatch">[{f.kind.padEnd(7)}]</span>{" "}
              <span className="ok">{f.t}</span>{" "}
              <span className="muted">{f.v}</span>
              {f.meta && <span className="skip"> {f.meta}</span>}
            </div>
          ))}
        </div>

        <h4 className="col-h" style={{marginTop: 14}}>Provisioning receipts</h4>
        <div className="receipts">
          <div className="row"><span className="dispatch">[resolve ]</span> <span className="ok">Role(companion)</span> <span className="muted">→ Actor(Aria)</span> <span className="skip">bound</span></div>
          <div className="row"><span className="dispatch">[resolve ]</span> <span className="ok">Setting(inn)</span> <span className="muted">→ Location(Crossroads Inn)</span> <span className="skip">bound</span></div>
          <div className="row skip"><span className="dispatch">[offer   ]</span> Template(innkeeper) · rank 0.72 (not bound)</div>
          <div className="row"><span className="dispatch">[fanout  ]</span> <span className="ok">MenuBlock</span> <span className="muted">yielded {current.actions.length} edges</span></div>
        </div>

        <div className="margin-note" style={{marginTop: 14}}>
          Author view is its own screen — reader never sees this. But every widget here reuses
          the same primitives (kv, item_list, badges) as the reader's sidebars.
        </div>
      </div>
      <div className="col right">
        <h4 className="col-h">Inspector · selected</h4>
        <div className="stack-sm">
          <div className="panel">
            <div className="panel-hd"><span>block.{current.id.split(".").pop()}</span><span className="muted">node</span></div>
            <div className="panel-bd">
              <div className="kv mono tiny">
                <span className="k">uid</span><span className="v">{current.id}</span>
                <span className="k">kind</span><span className="v">story.episode.Block</span>
                <span className="k">scene</span><span className="v">{current.scene}</span>
                <span className="k">speaker</span><span className="v">{current.speaker?.name || "—"}</span>
                <span className="k">media</span><span className="v">{current.media?.label || "—"}</span>
                <span className="k">visits</span><span className="v">{state.visited.filter(v => v === current.id).length + 1}</span>
                <span className="k">terminal</span><span className="v">{current.terminal ? "true" : "false"}</span>
              </div>
            </div>
          </div>
          <div className="panel">
            <div className="panel-hd"><span>Outgoing edges</span><span className="muted">Action[]</span></div>
            <div className="panel-bd mono tiny stack-sm">
              {current.actions.map((a, i) => (
                <div key={a.id} style={{borderLeft: "2px solid var(--ink)", paddingLeft: 8}}>
                  <div><b>edge.{i+1}</b> → {a.to}</div>
                  <div className="muted">"{a.text}"</div>
                  <button className="ghost-btn" onClick={() => choose(a)} style={{marginTop: 4}}>
                    follow_edge
                  </button>
                </div>
              ))}
              {current.actions.length === 0 && <span className="muted">(no outgoing)</span>}
            </div>
          </div>
          <div className="panel">
            <div className="panel-hd"><span>Ledger journal</span><span className="muted">{history.length + 1} steps</span></div>
            <div className="panel-bd mono tiny" style={{maxHeight: 180, overflowY: "auto"}}>
              {history.map((h, i) => (
                <div key={i} style={{borderBottom: "1px dashed var(--rule)", padding: "2px 0"}}>
                  <span className="muted">#{h.step}</span> {h.id} → {h.choice}
                </div>
              ))}
              <div style={{padding: "2px 0", background: "var(--paper-2)"}}>
                <span className="muted">#{step}</span> <b>{current.id}</b> · cursor
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// tiny graph viz for author view
function GraphPreview({ blocks, cursor, history }) {
  // hand-laid-out coords for the 9 known blocks
  const layout = {
    start:           { x: 40,  y: 160, label: "start" },
    meet_aria:       { x: 180, y: 80,  label: "meet_aria" },
    request_help:    { x: 330, y: 40,  label: "request_help" },
    innkeeper:       { x: 180, y: 240, label: "innkeeper" },
    rumors:          { x: 330, y: 280, label: "rumors" },
    trail_start:     { x: 480, y: 80,  label: "trail_start" },
    forest_encounter:{ x: 620, y: 80,  label: "forest_encounter" },
    left_path:       { x: 760, y: 30,  label: "left_path" },
    right_path:      { x: 760, y: 140, label: "right_path" },
    end:             { x: 900, y: 80,  label: "end" },
  };
  const visited = new Set(history.map(h => h.id.split(".").pop()));
  const edges = [];
  blocks.forEach(b => {
    const from = b.id.split(".").pop();
    (b.actions||[]).forEach(a => edges.push([from, a.to]));
  });
  const cursorKey = cursor;

  return (
    <svg width="100%" height="100%" viewBox="0 0 960 340" style={{display: "block"}}>
      {edges.map(([from, to], i) => {
        const f = layout[from], t = layout[to];
        if (!f || !t) return null;
        const traversed = visited.has(from) && (visited.has(to) || to === cursorKey);
        return (
          <line key={i}
            x1={f.x + 50} y1={f.y + 12}
            x2={t.x} y2={t.y + 12}
            stroke={traversed ? "#b23a1d" : "#9a9a9a"}
            strokeWidth={traversed ? 1.5 : 1}
            strokeDasharray={traversed ? "none" : "4 3"}
            markerEnd="url(#arrow)"
          />
        );
      })}
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill="#6a6a6a" />
        </marker>
      </defs>
      {Object.entries(layout).map(([k, p]) => {
        const isCursor = k === cursorKey;
        const isVisited = visited.has(k);
        return (
          <g key={k} transform={`translate(${p.x}, ${p.y})`}>
            <rect width="100" height="24" rx="0"
              fill={isCursor ? "#1a1a1a" : "#f6f3ea"}
              stroke={isCursor ? "#b23a1d" : "#1a1a1a"}
              strokeWidth={isCursor ? 2 : 1.25}
            />
            <text x="50" y="16" textAnchor="middle"
              fill={isCursor ? "#f6f3ea" : "#1a1a1a"}
              fontFamily="var(--mono)" fontSize="10"
              style={{letterSpacing: "0.04em"}}>
              {p.label}
            </text>
            {isVisited && !isCursor && (
              <circle cx="94" cy="4" r="3" fill="#b23a1d" />
            )}
          </g>
        );
      })}
    </svg>
  );
}

// ---------- Top-level app ----------
function App() {
  const engine = useEngine();
  const [tab, setTab] = useState("reader"); // reader | author
  const [shell, setShell] = useState("dossier");
  const [density, setDensity] = useState("comfortable");
  const [tweaksOn, setTweaksOn] = useState(false);

  // Expose tweaks protocol
  useEffect(() => {
    const handler = (e) => {
      if (e.data?.type === "__activate_edit_mode") setTweaksOn(true);
      if (e.data?.type === "__deactivate_edit_mode") setTweaksOn(false);
    };
    window.addEventListener("message", handler);
    window.parent.postMessage({ type: "__edit_mode_available" }, "*");
    return () => window.removeEventListener("message", handler);
  }, []);

  const ShellComp = SHELLS[shell].comp;

  return (
    <div className="paper">
      <div className="rail">
        <div className="brand"><b>Story</b>Tangl · front-end wireframes</div>
        <span className="sep"></span>
        <div className="doc-meta">v38.3 · sketchbook · derek · apr 2026</div>
        <span className="spacer"></span>
        <div className="tabs" role="tablist">
          <button className="tab" role="tab" aria-selected={tab === "reader"} onClick={() => setTab("reader")}>Reader</button>
          <button className="tab" role="tab" aria-selected={tab === "author"} onClick={() => setTab("author")}>Author / debug</button>
        </div>
      </div>

      <div className="page">
        {tab === "reader" ? (
          <>
            {/* Intro / premise */}
            <div className="sec-head">
              <div className="idx">§1 · premise</div>
              <h2>A shared widget vocabulary, many layout shells</h2>
              <div className="sub">wireframes, not pixel-final</div>
            </div>

            <div className="cols-2">
              <div className="frame">
                <span className="frame-label">design thesis</span>
                <span className="frame-tag">01</span>
                <div className="frame-body">
                  <p className="prose" style={{fontSize: 15}}>
                    The engine already emits a structured fragment stream:
                    <span className="mono"> content</span>, <span className="mono">choice</span>,
                    <span className="mono"> dialog</span>, <span className="mono">media</span>,
                    <span className="mono"> kv</span>, <span className="mono">group</span>,
                    <span className="mono"> control</span>. Each client only needs
                    to render these primitives — the <em>layout shell</em> above them is
                    where personality lives.
                  </p>
                  <p className="prose" style={{fontSize: 15}}>
                    Bespoke per-world clients keep the primitive set and swap shells.
                    Ports to Qt / Godot / Unity / TS re-implement the primitives but
                    must match this vocabulary so any authored script plays anywhere.
                  </p>
                </div>
              </div>

              <div className="frame">
                <span className="frame-label">shared primitives</span>
                <span className="frame-tag">02</span>
                <div className="frame-body">
                  <div className="cols-3" style={{gap: 10}}>
                    <ChoiceList actions={[
                      { id: "x1", text: "Sample choice A", to: "" },
                      { id: "x2", text: "Sample choice B", to: "" },
                    ]} onChoose={() => {}} />
                    <StatusPanel
                      state={{ visited: [1,2], met: [1], flags: [], knowledge: [] }}
                      extra={{ step: 3, cursor: "prologue.meet_aria", scene: "prologue" }}
                      title="Ledger"
                    />
                    <BadgePanel title="Flags" items={["rain", "warm"]} />
                  </div>
                  <div style={{height: 10}}></div>
                  <div className="margin-note note--small">
                    same components, every shell.
                  </div>
                </div>
              </div>
            </div>

            {/* Shell overview */}
            <div className="sec-head" style={{marginTop: 42}}>
              <div className="idx">§2 · layout shells</div>
              <h2>Six ways to compose the same fragment stream</h2>
              <div className="sub">try the flow — click a choice →</div>
            </div>

            <div className="frame" style={{marginBottom: 18}}>
              <span className="frame-label">controls</span>
              <span className="frame-tag">live · crossroads_inn · step {engine.step}</span>
              <div className="frame-body" style={{display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap"}}>
                <div className="mono tiny muted">shell</div>
                <div className="tab-toggle">
                  {Object.entries(SHELLS).map(([k, s]) => (
                    <button key={k} className={k === shell ? "on" : ""} onClick={() => setShell(k)}>
                      {s.label}
                    </button>
                  ))}
                </div>
                <span className="spacer" style={{flex: 1}}></span>
                <div className="mono tiny muted">cursor: <b style={{color: "var(--ink)"}}>{engine.current.id}</b></div>
                <button className="ghost-btn" onClick={engine.reset}>reset story</button>
              </div>
            </div>

            {/* Active shell */}
            <div className="shell-showcase">
              <div className="shell-head">
                <h3>{SHELLS[shell].label}</h3>
                <span className="shell-code">{SHELLS[shell].code}</span>
                {SHELLS[shell].sub && <span className="shell-sub">{SHELLS[shell].sub}</span>}
              </div>
              <div className="device">
                <div className="device-chrome">
                  <div className="dots">
                    <span className="dot"></span><span className="dot"></span><span className="dot"></span>
                  </div>
                  <div className="url">crossroads-inn.storytangl.local / reader / {shell}</div>
                  <div>tangl-web · {SHELLS[shell].code}</div>
                </div>
                <div className="device-body">
                  <ShellComp engine={engine} />
                </div>
              </div>

              <div className="cols-2" style={{marginTop: 14}}>
                <div className="margin-note note--small note--ink">
                  <span className="hand" style={{color: "var(--accent)"}}>→ note:</span> the
                  engine output is identical for every shell above. Only the
                  arrangement and affordance pattern differs. The dossier shell
                  keeps kv_list + badges persistent so authored status panels
                  don't compete with prose for attention.
                </div>
                <div className="margin-note note--small note--blue">
                  <span className="hand" style={{color: "var(--blue-pencil)"}}>follow-up:</span>{" "}
                  the Card-deck shell is where the speculative CCG could live —
                  cards-in-hand overlay on top of the narrative card, with
                  Calvin-ball rules surfacing as <span className="mono">kv_list</span> tooltips.
                </div>
              </div>
            </div>

            {/* Widget catalog */}
            <div className="sec-head" style={{marginTop: 42}}>
              <div className="idx">§3 · widget catalog</div>
              <h2>The rendering primitives, in isolation</h2>
              <div className="sub">reuse everywhere, port verbatim</div>
            </div>

            <div className="cols-3">
              <div className="frame">
                <span className="frame-label">choice list</span>
                <span className="frame-tag">primitive</span>
                <div className="frame-body stack-md">
                  <ChoiceList actions={[
                    { id: "d1", text: "Approach the fireplace", to: "" },
                    { id: "d2", text: "Talk to the innkeeper", to: "" },
                  ]} onChoose={() => {}} />
                  <div className="choices">
                    <button className="choice locked" disabled>
                      <span className="kbd">3</span>
                      <span>Climb the stairs — <em>needs key</em></span>
                      <span className="arr">⊘</span>
                    </button>
                  </div>
                </div>
              </div>

              <div className="frame">
                <span className="frame-label">dialog line</span>
                <span className="frame-tag">primitive</span>
                <div className="frame-body">
                  <DialogLine
                    speaker={{ name: "Aria", avatar: "companion.svg" }}
                    text={"\"The Northern Pass? Dangerous this time of year.\""}
                  />
                  <DialogLine
                    speaker={{ name: "Innkeeper" }}
                    text={"\"They say the old fortress holds treasure beyond measure.\""}
                  />
                </div>
              </div>

              <div className="frame">
                <span className="frame-label">media frame</span>
                <span className="frame-tag">primitive</span>
                <div className="frame-body stack-md">
                  <PhImg kind="landscape" label="narrative_im · tavern.svg" />
                  <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:8}}>
                    <PhImg kind="portrait" label="portrait_im" />
                    <PhImg kind="square" label="avatar_im" />
                  </div>
                </div>
              </div>

              <div className="frame">
                <span className="frame-label">kv · status</span>
                <span className="frame-tag">primitive</span>
                <div className="frame-body">
                  <StatusPanel
                    state={{ visited: [1,2,3], met: [1], flags: ["rain"], knowledge: [] }}
                    extra={{ step: 3, cursor: "prologue.meet_aria", scene: "prologue" }}
                    title="Ledger"
                  />
                </div>
              </div>

              <div className="frame">
                <span className="frame-label">badges · item_list</span>
                <span className="frame-tag">primitive</span>
                <div className="frame-body stack-md">
                  <BadgePanel title="Companions" items={["Aria", "Hound"]} />
                  <ItemList title="Carried" items={[
                    { name: "Brass Key", kind: "relic", cost: "—" },
                    { name: "Old Map", kind: "paper", cost: "—" },
                  ]} />
                </div>
              </div>

              <div className="frame">
                <span className="frame-label">card-view (speculative)</span>
                <span className="frame-tag">future</span>
                <div className="frame-body" style={{display: "flex", gap: 10, flexWrap: "wrap"}}>
                  {window.SCENE.cards.map(c => <CardMini key={c.id} card={c} />)}
                </div>
                <div style={{padding: "0 22px 16px"}}>
                  <div className="margin-note note--small note--blue">
                    Calvin-ball CCG hook: each block can emit card-view fragments,
                    decks auto-built per world theme (high fantasy / steampunk / …).
                    Parks here as a primitive slot; no mechanics yet.
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="sec-head">
              <div className="idx">§A · author view</div>
              <h2>Separate screen · graph · phase bus · fragments · ledger</h2>
              <div className="sub">not visible to the reader</div>
            </div>

            <div className="frame">
              <span className="frame-label">author / debug</span>
              <span className="frame-tag">step {engine.step} · cursor {engine.cursor}</span>
              <div className="frame-body" style={{padding: 0}}>
                <AuthorView engine={engine} />
              </div>
            </div>

            <div className="frame" style={{marginTop: 24}}>
              <span className="frame-label">notes</span>
              <span className="frame-tag">margins</span>
              <div className="frame-body">
                <div className="cols-2">
                  <div className="margin-note">
                    Everything here rides the same primitives as the reader: kv_list
                    for block metadata, item_list for edges, badges for flags.
                    A port to Qt/Godot mostly just reuses the Reader's widget library.
                  </div>
                  <div className="margin-note note--blue">
                    Phase-bus visualization maps directly to the 8-phase pipeline
                    (VALIDATE → PLANNING → PREREQS → UPDATE → JOURNAL → FINALIZE →
                    POSTREQS → advance). Handlers attach at phases; receipts stream live.
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Tweaks panel */}
      <div className={`tweaks ${tweaksOn ? "on" : ""}`}>
        <div className="tw-hd"><span>Tweaks</span><button className="ghost-btn" onClick={() => setTweaksOn(false)}>×</button></div>
        <div className="tw-bd">
          <label>Active shell
            <select value={shell} onChange={(e) => setShell(e.target.value)}>
              {Object.entries(SHELLS).map(([k, s]) => <option key={k} value={k}>{s.label}</option>)}
            </select>
          </label>
          <label>Top-level view
            <select value={tab} onChange={(e) => setTab(e.target.value)}>
              <option value="reader">Reader</option>
              <option value="author">Author / debug</option>
            </select>
          </label>
          <div className="toggle-row">
            <span>reset story</span>
            <button className="ghost-btn" onClick={engine.reset}>run</button>
          </div>
          <div className="mono tiny muted">
            step {engine.step} · {engine.cursor}
          </div>
        </div>
      </div>
    </div>
  );
}

// Export shells + primitives for print.jsx
Object.assign(window, {
  PhImg, ChoiceList, DialogLine, Prose,
  StatusPanel, BadgePanel, ItemList, CardMini,
  DossierShell, ScrollShell, StageLogShell, VNShell, DeckShell, TerminalShell,
  AuthorView, GraphPreview, SHELLS, useEngine, App,
});

if (!window.__PRINT_MODE) {
  ReactDOM.createRoot(document.getElementById("root")).render(<App />);
}
