/* Print build of StoryTangl wireframes — static, all shells stacked */

function PrintApp() {
  // Use a fresh engine for each shell so each shows the opening state cleanly
  const makeEngine = () => {
    const scene = window.SCENE;
    const current = scene.blocks[scene.start];
    return {
      scene,
      current,
      cursor: scene.start,
      step: 1,
      history: [],
      state: { visited: [], met: [], flags: [], knowledge: [], locations: [] },
      choose: () => {},
      reset: () => {},
    };
  };

  // Mid-flow engine — step 4, having met Aria and asked about the pass
  const makeMidEngine = () => {
    const scene = window.SCENE;
    return {
      scene,
      current: scene.blocks.request_help,
      cursor: "request_help",
      step: 4,
      history: [
        {
          id: "prologue.start",
          title: "The Crossroads Inn",
          text: scene.blocks.start.text,
          media: scene.blocks.start.media,
          choice: "Approach the fireplace",
          step: 1,
        },
        {
          id: "prologue.meet_aria",
          title: "By the fire",
          text: scene.blocks.meet_aria.text,
          speaker: scene.blocks.meet_aria.speaker,
          media: scene.blocks.meet_aria.media,
          choice: "I'm looking for the Northern Pass",
          step: 2,
        },
      ],
      state: { visited: ["prologue.start","prologue.meet_aria"], met: ["Aria"], flags: [], knowledge: [], locations: [] },
      choose: () => {},
      reset: () => {},
    };
  };

  const openEng = makeEngine();
  const midEng = makeMidEngine();

  return (
    <div className="paper">
      {/* COVER */}
      <section className="print-page">
        <div style={{minHeight: "80vh", display: "flex", flexDirection: "column", justifyContent: "space-between"}}>
          <div>
            <div className="mono tiny" style={{letterSpacing: "0.14em", color: "var(--ink-3)", textTransform: "uppercase"}}>
              StoryTangl · front-end wireframes
            </div>
            <div style={{height: 2, background: "var(--ink)", margin: "10px 0 24px"}}></div>
            <h1 style={{fontFamily: "var(--serif)", fontSize: 48, fontWeight: 600, margin: 0, letterSpacing: "-0.01em", lineHeight: 1.05}}>
              A shared widget vocabulary,<br/>
              <em style={{color: "var(--ink-3)"}}>many</em> layout shells.
            </h1>
            <div className="hand" style={{marginTop: 24, fontSize: 22, color: "var(--accent)", transform: "rotate(-1deg)", display: "inline-block"}}>
              mid-fi · engineering notebook · apr 2026
            </div>
          </div>

          <div className="cols-2">
            <div className="frame">
              <span className="frame-label">design thesis</span>
              <div className="frame-body">
                <p className="prose" style={{fontSize: 14, margin: 0}}>
                  The engine already emits a structured fragment stream:
                  <span className="mono"> content</span>, <span className="mono">choice</span>,
                  <span className="mono"> dialog</span>, <span className="mono">media</span>,
                  <span className="mono"> kv</span>, <span className="mono">group</span>,
                  <span className="mono"> control</span>. Each client only needs to render
                  these primitives — the <em>layout shell</em> above them is where
                  personality lives. Bespoke per-world clients keep the primitive set
                  and swap shells.
                </p>
              </div>
            </div>
            <div className="frame">
              <span className="frame-label">contents</span>
              <div className="frame-body mono tiny" style={{lineHeight: 1.8}}>
                <div>§2 · shell · dossier split <span className="muted">(primary)</span></div>
                <div>§3 · shell · sugarcube scroll</div>
                <div>§4 · shell · stage + log</div>
                <div>§5 · shell · visual novel</div>
                <div>§6 · shell · card deck</div>
                <div>§7 · shell · terminal</div>
                <div>§8 · widget catalog</div>
                <div>§A · author / debug view</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* DOSSIER */}
      <section className="print-page">
        <div className="print-head">
          <span className="idx">§2 · shell.dossier</span>
          <h2>Dossier split — primary focus</h2>
          <span className="sub">narrative mid, persistent sidebars</span>
        </div>
        <div className="device">
          <div className="device-chrome">
            <div className="dots"><span className="dot"></span><span className="dot"></span><span className="dot"></span></div>
            <div className="url">crossroads-inn.storytangl.local / reader / dossier</div>
            <div>tangl-web · shell.dossier</div>
          </div>
          <DossierShell engine={midEng} />
        </div>
        <div style={{marginTop: 12}} className="margin-note note--small">
          Keeps the engine's structured sidecar data (kv, badges, item_list) persistent
          across every step — matching what the CLI's <span className="mono">status</span> shows.
          This is the shell I'd default bespoke worlds to.
        </div>
      </section>

      {/* SCROLL */}
      <section className="print-page">
        <div className="print-head">
          <span className="idx">§3 · shell.scroll</span>
          <h2>Sugarcube scroll — today's web client</h2>
          <span className="sub">text-forward, infinite history</span>
        </div>
        <div className="device">
          <div className="device-chrome">
            <div className="dots"><span className="dot"></span><span className="dot"></span><span className="dot"></span></div>
            <div className="url">crossroads-inn.storytangl.local / reader / scroll</div>
            <div>tangl-web · shell.scroll</div>
          </div>
          <ScrollShell engine={midEng} />
        </div>
        <div style={{marginTop: 12}} className="margin-note note--small note--blue">
          Today's Vue client lives closest to this. Nothing wrong with it —
          but all the structured fragments (kv, badges, item_list) have nowhere to go
          unless we inject panels between blocks.
        </div>
      </section>

      {/* STAGE + LOG */}
      <section className="print-page">
        <div className="print-head">
          <span className="idx">§4 · shell.stage_log</span>
          <h2>Stage + log</h2>
          <span className="sub">persistent scene, rolling journal</span>
        </div>
        <div className="device">
          <div className="device-chrome">
            <div className="dots"><span className="dot"></span><span className="dot"></span><span className="dot"></span></div>
            <div className="url">crossroads-inn.storytangl.local / reader / stage</div>
            <div>tangl-web · shell.stage_log</div>
          </div>
          <StageLogShell engine={midEng} />
        </div>
        <div style={{marginTop: 12}} className="margin-note note--small">
          Media and current choices stay "on stage"; the log keeps a trimmed history.
          Good for worlds where media is the primary carrier.
        </div>
      </section>

      {/* VN */}
      <section className="print-page">
        <div className="print-head">
          <span className="idx">§5 · shell.vn</span>
          <h2>Visual novel</h2>
          <span className="sub">full-bleed, dialog box, overlay choices</span>
        </div>
        <div className="device">
          <div className="device-chrome">
            <div className="dots"><span className="dot"></span><span className="dot"></span><span className="dot"></span></div>
            <div className="url">crossroads-inn.storytangl.local / reader / vn</div>
            <div>tangl-web · shell.vn</div>
          </div>
          <VNShell engine={midEng} />
        </div>
        <div style={{marginTop: 12}} className="margin-note note--small note--blue">
          This is a natural target for the Ren'Py / Godot clients — the dialog box +
          sprite + backdrop maps straight onto those engines' idioms.
        </div>
      </section>

      {/* DECK */}
      <section className="print-page">
        <div className="print-head">
          <span className="idx">§6 · shell.deck</span>
          <h2>Card deck</h2>
          <span className="sub">where the Calvin-ball CCG could live</span>
        </div>
        <div className="device">
          <div className="device-chrome">
            <div className="dots"><span className="dot"></span><span className="dot"></span><span className="dot"></span></div>
            <div className="url">crossroads-inn.storytangl.local / reader / deck</div>
            <div>tangl-web · shell.deck</div>
          </div>
          <DeckShell engine={midEng} />
        </div>
        <div style={{marginTop: 12}} className="margin-note note--small">
          Each block is a card; stack builds behind. Speculative hook: auto-built
          themed decks (high fantasy, steampunk…) emitted as card-view fragments
          alongside the narrative card.
        </div>
      </section>

      {/* TERMINAL */}
      <section className="print-page">
        <div className="print-head">
          <span className="idx">§7 · shell.terminal</span>
          <h2>Terminal — CLI parity</h2>
          <span className="sub">same fragments, different medium</span>
        </div>
        <div className="device">
          <div className="device-chrome">
            <div className="dots"><span className="dot"></span><span className="dot"></span><span className="dot"></span></div>
            <div className="url">tty · tangl-cli · derek@crossroads_inn</div>
            <div>tangl-cli · shell.terminal</div>
          </div>
          <TerminalShell engine={midEng} />
        </div>
        <div style={{marginTop: 12}} className="margin-note note--small note--blue">
          Same fragment stream, rendered as monospace. Confirms the widget vocabulary
          is medium-agnostic — a port to Qt/TCL is the same exercise.
        </div>
      </section>

      {/* WIDGET CATALOG */}
      <section className="print-page">
        <div className="print-head">
          <span className="idx">§8 · widget catalog</span>
          <h2>Rendering primitives in isolation</h2>
          <span className="sub">reuse everywhere, port verbatim</span>
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
              <DialogLine speaker={{ name: "Aria", avatar: "companion.svg" }}
                text={"\"The Northern Pass? Dangerous this time of year.\""} />
              <DialogLine speaker={{ name: "Innkeeper" }}
                text={"\"They say the old fortress holds treasure beyond measure.\""} />
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
            <div className="frame-body" style={{display: "flex", gap: 8, flexWrap: "wrap"}}>
              {window.SCENE.cards.map(c => <CardMini key={c.id} card={c} />)}
            </div>
          </div>
        </div>
      </section>

      {/* AUTHOR */}
      <section className="print-page">
        <div className="print-head">
          <span className="idx">§A · author / debug</span>
          <h2>Separate screen — graph, phase bus, fragments, ledger</h2>
          <span className="sub">not visible to the reader</span>
        </div>
        <div className="frame">
          <span className="frame-label">author / debug</span>
          <span className="frame-tag">step {midEng.step} · cursor {midEng.cursor}</span>
          <div className="frame-body" style={{padding: 0}}>
            <AuthorView engine={midEng} />
          </div>
        </div>
        <div style={{marginTop: 12}} className="cols-2">
          <div className="margin-note note--small">
            Everything here rides the same primitives as the reader: kv_list for
            block metadata, item_list for edges, badges for flags. A port to Qt/Godot
            mostly just reuses the Reader's widget library.
          </div>
          <div className="margin-note note--small note--blue">
            Phase-bus maps directly to VALIDATE → PLANNING → PREREQS → UPDATE → JOURNAL
            → FINALIZE → POSTREQS → advance. Handlers attach at phases; receipts stream live.
          </div>
        </div>
      </section>
    </div>
  );
}

// Mark body for print styles, then render
document.body.classList.add("print-mode");
ReactDOM.createRoot(document.getElementById("root")).render(<PrintApp />);

// Auto-print once fonts + layout settle
(async function autoPrint() {
  try { if (document.fonts && document.fonts.ready) { await document.fonts.ready; } } catch (_) {}
  await new Promise(r => setTimeout(r, 700));
  window.print();
})();
