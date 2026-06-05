// wp-sections2.jsx — §3 proof strip, §4–6 deep dives, §7 render axis,
// §8 logo system, §9 the floor. Depends on kit widgets + wp-sections.jsx.

// ===========================================================================
// GenreDossier — a Dossier shell that ALSO renders P2 zones/pieces/catalogs.
// (The bare kit DossierShell only walks prose/dialog/kv/roll; the genre demos
//  need zones. This composes the kit widgets directly so every fill is themed.)
// ===========================================================================
function GenreDossier({ envelope, projected, onPick }) {
  const idx = indexEnvelope(envelope);
  const scene = findScene(envelope);
  const items = (scene?.member_ids || []).map(id => idx.byUid[id]).filter(Boolean);
  const choices = items.filter(f => f.fragment_type === "choice");
  const hasCmd = choices.some(c => c.edge_id === "interpret_command");

  function renderFrag(f) {
    if (f.fragment_type === "content") return <ContentBlock key={f.uid} frag={f} />;
    if (f.fragment_type === "kv") return <KvInlineStrip key={f.uid} frag={f} />;
    if (f.fragment_type === "roll") return <RollWidget key={f.uid} frag={f} defaultSkipped />;
    if (f.fragment_type === "group" && f.group_type === "dialog")
      return <DialogGroup key={f.uid} group={f} byUid={idx.byUid} />;
    if (f.fragment_type === "group" && f.group_type === "zone") {
      const role = f.layout_hints?.zone_role;
      if (role === "catalog")
        return (
          <div key={f.uid} style={{ margin: "4px 0" }}>
            <div className="wp-kicker" style={{ fontSize: 10, textTransform: "uppercase", color: "var(--ink-3)", marginBottom: 6, fontFamily: "var(--mono)" }}>
              {f.hints?.label_text || "catalog"}
            </div>
            <CatalogGrid zone={f} env={envelope} byUid={idx.byUid} />
          </div>
        );
      return <ZoneTile key={f.uid} zone={f} env={envelope} byUid={idx.byUid} />;
    }
    return null;
  }

  // group consecutive slot zones into a row so the chassis reads as a unit
  const stage = [];
  let slotRun = [];
  const flushSlots = () => {
    if (slotRun.length) {
      stage.push(
        <div key={"slots-" + stage.length} style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(slotRun.length, 3)}, 1fr)`, gap: 8 }}>
          {slotRun.map(renderFrag)}
        </div>
      );
      slotRun = [];
    }
  };
  for (const f of items) {
    if (f.fragment_type === "choice") continue;
    if (f.fragment_type === "group" && f.group_type === "zone" && f.layout_hints?.zone_role === "slot") {
      slotRun.push(f); continue;
    }
    flushSlots();
    stage.push(renderFrag(f));
  }
  flushSlots();

  return (
    <div className="v12-dossier-shell">
      <div className="dos-stage">
        {stage}
        <div style={{ marginTop: 10 }}>
          <ChoiceList choices={choices} env={envelope} onCommit={onPick} options={{ showSource: false }} />
          {hasCmd && <CommandBar env={envelope} onSubmit={() => {}} />}
        </div>
      </div>
      <div className="dos-rail">
        {(projected?.sections || []).map(s => <RailSection key={s.section_id} section={s} />)}
      </div>
    </div>
  );
}

function ThemeVars({ world, mode, children, style, className }) {
  const profile = WP_PROFILES.get(world);
  const m = WP_PROFILES.resolveMode(profile, mode);
  return (
    <span className={className} style={{ ...WP_PROFILES.cssVars(profile, m), ...(style || {}) }}>
      {children}
    </span>
  );
}

// ===========================================================================
// §3 — the proof strip: one envelope, four costumes
// ===========================================================================
function ProofSection() {
  const cols = WP_PROFILES.ORDER;
  return (
    <section style={{ marginTop: 40 }}>
      <SecHead idx="§3" title="One envelope, four costumes" sub="the proof" />
      <p className="prose" style={{ maxWidth: 880, marginBottom: 16 }}>
        Every column below renders the <b>same fragment graph</b> — identical{" "}
        <span className="mono">uid</span>s, identical order, identical{" "}
        <span className="mono">fragment_type</span>s, identical{" "}
        <span className="mono">ui_hints</span> and <span className="mono">emphasis</span>{" "}
        ladder, identical blocker on the third move. The backend bundle filled the
        slots; the world profile painted them. Diff any two envelopes and the only
        deltas are surface strings. The position-1 prose, the part zone, the
        three-row severity strip, the primary / secondary / <i>barred</i> moves, the
        resource bar — all land in the same place every time.
      </p>
      <div className="wp-proof-grid">
        {cols.map(w => {
          const p = WP_PROFILES.get(w);
          const m = p.default_mode;
          const fx = WP_FIXTURES.buildSharedTurn(w, p);
          return (
            <div key={w} className="wp-proof-col">
              <ThemeVars world={w} mode={m} className="wp-proof-head" style={{ display: "flex" }}>
                <WpGlyph profile={p} style={{ fontSize: 13 }} />
                <span className="pname">{p.display_name}</span>
                <span className="pmode">{m}</span>
              </ThemeVars>
              <WorldSkin world={w} mode={m} className="wp-proof-body">
                <div className="skin-substrate" />
                <GenreDossier envelope={fx.envelope} projected={fx.projected_state} />
              </WorldSkin>
            </div>
          );
        })}
      </div>
      <div className="wp-rhyme">
        <div className="slot"><b>position 1</b> content · the prose</div>
        <div className="slot"><b>position 2</b> zone · three pieces</div>
        <div className="slot"><b>position 3</b> kv · ok / warn / danger</div>
        <div className="slot"><b>positions 4–6</b> primary · second · <i>barred</i></div>
        <div className="slot"><b>rail</b> resource bar · roster · score</div>
      </div>
      <div className="margin-note" style={{ marginTop: 14, maxWidth: 880 }}>
        Note credentials renders <i>ink-only</i> even though the strip is asking for
        each world's default — it declared a single theme and the client honors it.
      </div>
    </section>
  );
}

// ===========================================================================
// Deep-dive frame
// ===========================================================================
function DeepDive({ idx, world, mode, fixture, height, notes, kicker }) {
  const p = WP_PROFILES.get(world);
  const m = WP_PROFILES.resolveMode(p, mode);
  return (
    <section className="wp-dive" style={{ marginTop: 44 }}>
      <div className="sec-head" style={{ borderBottom: "none", marginBottom: 6 }}>
        <span className="idx">{idx}</span>
        <h2 style={{ visibility: "hidden", width: 0 }}>x</h2>
      </div>
      <div className="wp-dive-head">
        <ThemeVars world={world} mode={m} style={{ display: "inline-flex", alignItems: "center", gap: 12 }}>
          <WpGlyph profile={p} style={{ fontSize: 24 }} />
          <WpWordmark profile={p} />
        </ThemeVars>
        <span className="wp-tagline">{p.tagline}</span>
        <div className="wp-dive-meta">
          <div>signature shell · <b>{p.signature_shell}</b></div>
          <div>mode · <span className={"policy " + p.mode_policy}>{p.mode_policy.replace("_", " ")}</span> · default <b>{m}</b></div>
          <div>face · <b>{(p.type_register.display || "—").split(",")[0].replace(/'/g, "")}</b></div>
        </div>
      </div>

      <div className="wp-axis" style={{ gridTemplateColumns: "1.55fr 1fr" }}>
        <WorldSkin world={world} mode={m} className="device wp-dive-device">
          <div className="wp-device-bar">
            <ThemeVars world={world} mode={m} style={{ display: "inline-flex" }}>
              <WpWordmark profile={p} withGlyph />
            </ThemeVars>
            <span className="bar-meta">{kicker}</span>
          </div>
          <div className="skin-edge" style={{ height: world === "carwars" ? 5 : 0 }} />
          <div style={{ position: "relative", height: height || 560 }}>
            <div className="skin-substrate" />
            <div style={{ position: "relative", height: "100%", overflow: "auto" }}>
              <GenreDossier envelope={fixture.envelope} projected={fixture.projected_state} />
            </div>
          </div>
        </WorldSkin>

        <aside className="panel" style={{ background: "#fff", alignSelf: "start" }}>
          <div className="panel-hd"><span>Costume notes</span><span className="pill pill--ghost">{world}</span></div>
          <div className="panel-bd" style={{ display: "grid", gap: 12 }}>
            {notes.map((n, i) => (
              <div key={i}>
                <div className="block-kicker" style={{ marginBottom: 3 }}>{n.k}</div>
                <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.5, color: "var(--ink-2)", fontFamily: "var(--sans)" }}>{n.d}</p>
              </div>
            ))}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 2 }}>
              {["paper", "ink", "accent", "ok", "warn", "bad"].map(k => {
                const pal = (p.palette && p.palette[m]) || {};
                return <span key={k} className="wp-chip"><span className="sw" style={{ background: pal[k] || "#ccc" }} />{k}</span>;
              })}
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}

// ===========================================================================
// §4–6 deep dives
// ===========================================================================
function CarwarsDive() {
  return (
    <DeepDive
      idx="§4 · world" world="carwars" mode="ink" height={620}
      fixture={WP_FIXTURES.carwars}
      kicker="dossier · garage · outfit"
      notes={[
        { k: "the loop", d: "Slot zones with weight capacity bars; bolt-on previews ghost into the bar. Drive is barred by an over-weight blocker — strip mass first. Pure carwars stresses, zero new vocabulary." },
        { k: "palette", d: "Sun-bleached bone on asphalt; hazard-orange is the single heat, riding --accent. Olive/amber/red severity reads as a dashboard, not a notebook." },
        { k: "type & mark", d: "Saira Stencil One stencils the wordmark and heads only — body and widgets stay in the three-role stack. Turned W reads as M. Mad Max by glyph." },
        { k: "mode", d: "Dual, ink by default — the gauntlet runs at night. Daylight (light mode) is a dust-tan inversion of the same tokens." },
      ]}
    />
  );
}

function CredentialsDive() {
  const fx = WP_FIXTURES.genre("credentials");
  return (
    <DeepDive
      idx="§5 · world" world="credentials" mode="ink" height={620}
      fixture={fx}
      kicker="dossier · booth · inspect"
      notes={[
        { k: "the loop", d: "The packet is a zone of document pieces; findings carry severity; the lawful disposition (Allow) is barred by an expired-permit blocker whose refs are all on screen. Decision legibility, untouched." },
        { k: "palette", d: "Cold institutional bone on charcoal; stamp-red is the only saturated note — the DENIED ink. The shift directives change at the top of every shift, Kafka-style." },
        { k: "type & mark", d: "Silkscreen sets a bitmap wordmark; the turned C sits in a rubber-stamp ring, canted 8°. 8-bit booth without a single new widget." },
        { k: "mode", d: "Declares ink_only — the booth is always dim. The client must not invent a light theme; the proof strip honored that." },
      ]}
    />
  );
}

function RegentDive() {
  const fx = WP_FIXTURES.genre("coronate_the_regent");
  return (
    <DeepDive
      idx="§6 · world" world="coronate_the_regent" mode="light" height={640}
      fixture={fx}
      kicker="dossier · court · the week"
      notes={[
        { k: "the loop", d: "Stats and mood project to the rail as bars and a scalar; the week's choices carry stat_check previews; the merchant's wares are a catalog of offers, one barred by coin. Long Live the Queen, by the book." },
        { k: "palette", d: "Pale orchid and periwinkle, with rose as the danger color — in this world death comes pretty, so --bad and --accent share the blush. Persona-cool, softened to pastel." },
        { k: "type & mark", d: "Marcellus gives a regal Roman-cap wordmark; the turned R is double-engraved. Courtly, not edgy." },
        { k: "mode", d: "Dual — pastel day court and a candlelit night court (ink) that inverts the same orchid tokens." },
      ]}
    />
  );
}

// ===========================================================================
// §7 — render axis: one world, two render profiles
// ===========================================================================
function RenderAxisSection() {
  const p = WP_PROFILES.get("carwars");
  const fx = WP_FIXTURES.carwars;
  const cliLines = cliRenderEnvelope(fx.envelope, fx.projected_state, { width: 42 });
  return (
    <section style={{ marginTop: 44 }}>
      <SecHead idx="§7" title="The costume honors the render profile" sub="{carwars} × {rich, ascii}" />
      <p className="prose" style={{ maxWidth: 880, marginBottom: 16 }}>
        A world profile degrades exactly as content does. Cross the wire to the CLI
        floor and the paint, texture and display face fall away — but the structure
        and the <i>lexicon</i> ride all the way down. The terminal still says{" "}
        <span className="mono">rig</span>, <span className="mono">loadout</span>,{" "}
        <span className="mono">gauntlet</span>; the over-weight block still bars the
        drive; the journal still reads as story. This is the {`{world × render}`} cell,
        made literal.
      </p>
      <div className="wp-axis">
        <WorldSkin world="carwars" mode="ink" className="device wp-dive-device">
          <div className="wp-device-bar">
            <ThemeVars world="carwars" mode="ink" style={{ display: "inline-flex" }}>
              <WpWordmark profile={p} withGlyph />
            </ThemeVars>
            <span className="bar-meta">render · rich</span>
          </div>
          <div className="skin-edge" style={{ height: 5 }} />
          <div style={{ position: "relative", height: 560 }}>
            <div className="skin-substrate" />
            <div style={{ position: "relative", height: "100%", overflow: "auto" }}>
              <GenreDossier envelope={fx.envelope} projected={fx.projected_state} />
            </div>
          </div>
        </WorldSkin>
        <CliPane lines={cliLines} label="carwars · cli_reference_port.py" width={42} />
      </div>
      <div className="margin-note" style={{ marginTop: 14, maxWidth: 880 }}>
        Same envelope, same commit payloads. The CLI floor is colorless and faceless by
        design — the profile asked for nothing the terminal can't give, so nothing breaks.
      </div>
    </section>
  );
}

// ===========================================================================
// §8 — the turned-glyph logo family
// ===========================================================================
function LogoSection() {
  const order = WP_PROFILES.ORDER;
  return (
    <section style={{ marginTop: 44 }}>
      <SecHead idx="§8" title="The mark turns, the letter doesn't matter" sub="one family, four letters" />
      <p className="prose" style={{ maxWidth: 880, marginBottom: 18 }}>
        The house mark is <b>StoryTan⅁l</b> — a capital G turned 180° to stand in for
        its lowercase g. The <i>rotation is the brand</i>, not the letterform. So a
        world keeps the family by keeping the turn and swapping which letter takes it:
        the regent turns an R, the booth turns a C, the wasteland turns a W. The
        treatment costumes it — stencilled, stamped, engraved — but the gesture is
        constant. Recognisable as kin across a parking lot.
      </p>
      <div className="cols-2" style={{ gap: 18 }}>
        {order.map(w => {
          const p = WP_PROFILES.get(w);
          const m = p.default_mode;
          return (
            <WorldSkin key={w} world={w} mode={m} className="device" style={{ padding: 0 }}>
              <div style={{ position: "relative" }}>
                <div className="skin-substrate" style={{ position: "absolute", inset: 0 }} />
                <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 20, padding: "22px 24px" }}>
                  <WpGlyph profile={p} style={{ fontSize: 40 }} />
                  <div style={{ display: "grid", gap: 6 }}>
                    <WpWordmark profile={p} style={{ fontSize: 30 }} />
                    <div style={{ fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--ink-3)", letterSpacing: "0.04em" }}>
                      turned <b style={{ color: "var(--accent-ink)" }}>{p.logo.letter}</b> · {p.logo.treatment}
                      {p.type_register.display ? " · " + p.type_register.display.split(",")[0].replace(/'/g, "") : " · house serif"}
                    </div>
                  </div>
                </div>
              </div>
            </WorldSkin>
          );
        })}
      </div>
      <div className="margin-note" style={{ marginTop: 16, maxWidth: 880 }}>
        Rule of the road: a world may turn a different letter and dress it, but the
        glyph + plain-name lockup is never split, and the turn is never removed. Same
        discipline as the house brand sheet — extended, not broken.
      </div>
    </section>
  );
}

// ===========================================================================
// §9 — the floor that doesn't move
// ===========================================================================
function FloorSection() {
  const gates = [
    { g: "CLI", t: "CLI floor", d: "Every costume renders in the reference port. §7 proved carwars does; the other three are one cliRenderEnvelope away." },
    { g: "LEG", t: "Decision legibility", d: "Every UID a barred move references is on screen — the expired permit, the over-weight chassis, the plotting duke. Paint can't hide a blocker." },
    { g: "TIME", t: "Time parity", d: "Rolls and reveals stay skippable to canonical-instant in one action, in every world. The ritual is costume; the outcome is not." },
    { g: "IN", t: "Input parity", d: "Drag a plate onto a slot or type 'strip plate' — same turn, same payload. The lexicon renames the verb; it never removes the typed path." },
  ];
  return (
    <section style={{ marginTop: 44 }}>
      <SecHead idx="§9" title="The floor doesn't move" sub="what every costume still owes" />
      <p className="prose" style={{ maxWidth: 880, marginBottom: 16 }}>
        Load any world and the four gates still hold — that's what makes it the same
        client and not four. A profile is allowed to be loud precisely because it can't
        reach the floor: it paints, it renames, it sets one face; it cannot move a
        widget, drop a referenced UID, or skip a parity obligation. The walls are the
        contract. The paint is the world.
      </p>
      <div className="stool">
        {gates.map(x => (
          <div key={x.g} className="leg">
            <h5><span className="glyph">{x.g}</span> {x.t}</h5>
            <p>{x.d}</p>
          </div>
        ))}
      </div>
      <div className="frame" style={{ marginTop: 22 }}>
        <span className="frame-label">the whole claim, in one line</span>
        <div className="frame-body" style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "26px 22px" }}>
          <div style={{ fontFamily: "var(--serif)", fontSize: 22, textAlign: "center", maxWidth: 760, lineHeight: 1.4 }}>
            A render profile lets one world reach every screen.<br />
            A world profile lets one screen hold every world.<br />
            <span style={{ color: "var(--accent)", fontStyle: "italic" }}>The matrix is the product.</span>
          </div>
        </div>
      </div>
      <p className="tiny muted" style={{ marginTop: 22, fontFamily: "var(--mono)", maxWidth: 880 }}>
        next · deferred worlds (half-adder world's-fair, the modernized hunt) slot in as
        more columns, not more clients. · open question · should signature_shell be a
        hard request when a world's loop truly needs one shell (regent → dossier), or
        always a preference? · the pack format here is sketch-grade; the real schema
        lives next to the render-capability schema in the spec repo.
      </p>
    </section>
  );
}

Object.assign(window, {
  GenreDossier, ThemeVars, ProofSection, DeepDive,
  CarwarsDive, CredentialsDive, RegentDive,
  RenderAxisSection, LogoSection, FloorSection,
});
