// wp-sections.jsx — shared chrome + sections §0–§3.
// Depends on window.WP_PROFILES, window.WP_FIXTURES, and the kit widgets/shells.

const { useState: useS, useMemo: useM } = React;

// ===========================================================================
// Shared chrome
// ===========================================================================

// Turn a single letter of a name 180°, mirroring the wordmark's turned-G.
function turnLetter(name, letter) {
  let i = name.indexOf(letter);
  if (i < 0) i = name.toLowerCase().indexOf((letter || "").toLowerCase());
  if (i < 0) return name;
  return [
    name.slice(0, i),
    <span key="t" className="turned">{name[i]}</span>,
    name.slice(i + 1),
  ];
}

function WpGlyph({ profile, style }) {
  const t = profile.logo.treatment;
  return (
    <span className={"wp-glyph wp-display t-" + t} style={style} aria-hidden="true">
      <span className="turned">{profile.logo.letter}</span>
    </span>
  );
}

function WpWordmark({ profile, withGlyph, style }) {
  const t = profile.logo.treatment;
  return (
    <span className={"wp-wordmark wp-display t-" + t} style={style}>
      {withGlyph && <WpGlyph profile={profile} />}
      <span>{turnLetter(profile.display_name, profile.logo.letter)}</span>
    </span>
  );
}

// Themed surface: applies the profile's compiled CSS custom properties + data
// attributes. This IS the client "accepting" a pack — palette from the wire,
// texture/face keyed by name.
function WorldSkin({ world, mode, children, className, style }) {
  const profile = WP_PROFILES.get(world);
  const m = WP_PROFILES.resolveMode(profile, mode);
  const vars = WP_PROFILES.cssVars(profile, m);
  return (
    <div className={"world-skin " + (className || "")}
         data-world={world} data-mode={m}
         style={{ ...vars, ...(style || {}) }}>
      {children}
    </div>
  );
}

function SecHead({ idx, title, sub }) {
  return (
    <div className="sec-head">
      <span className="idx">{idx}</span>
      <h2>{title}</h2>
      {sub && <span className="sub">{sub}</span>}
    </div>
  );
}

function Swatches({ profile, mode }) {
  const m = WP_PROFILES.resolveMode(profile, mode);
  const pal = (profile.palette && profile.palette[m]) || {};
  const keys = ["paper", "ink", "accent", "ok", "warn", "bad"];
  return (
    <div className="swatch-row">
      {keys.map(k => (
        <span key={k} className="sw" title={k + " " + (pal[k] || "(kit default)")}
          style={{ background: pal[k] || (k === "paper" ? "#f6f3ea" : k === "ink" ? "#1a1a1a" : "#b23a1d") }} />
      ))}
    </div>
  );
}

// ===========================================================================
// Top banner
// ===========================================================================
function TopBanner() {
  return (
    <div className="rail">
      <div className="brand"><b>StoryTan⅁l</b> · UI 1.5</div>
      <div className="sep"></div>
      <div className="doc-meta">World Profiles × Render Profiles</div>
      <div className="spacer"></div>
      <div className="doc-meta">design study · {WP_PROFILES.ORDER.length - 1} worlds</div>
    </div>
  );
}

function Lede() {
  return (
    <div style={{ margin: "22px 0 8px" }}>
      <div className="block-kicker">extending the matrix</div>
      <h1 style={{ fontFamily: "var(--serif)", fontWeight: 600, fontSize: 38, letterSpacing: "-0.02em", margin: "0 0 12px", maxWidth: 980 }}>
        Same ergonomics, different world. A profile paints the room; it never moves the walls.
      </h1>
      <p className="prose" style={{ maxWidth: 820, fontSize: 17 }}>
        Today the renderer matrix is <b>one</b> world (generic) across three render
        profiles — <span className="mono">ascii</span>, <span className="mono">rich</span>,{" "}
        <span className="mono">vue</span>. This study adds a second axis. A backend
        ships a <b>world profile</b> — a closed pack of palette, texture, one display
        face, a turned-glyph mark, and a copy lexicon — and the client wears it. Load
        a world and you drop into a different story with a different feel, rendered
        through the <i>same shells</i>, the <i>same widget vocabulary</i>, and the{" "}
        <i>same four conformance gates</i>. <span className="note">generic is just the identity profile.</span>
      </p>
    </div>
  );
}

// ===========================================================================
// §0 — the {world × render} matrix
// ===========================================================================
function MatrixSection() {
  const worlds = WP_PROFILES.ORDER;
  const renders = [
    { id: "cli", label: "ascii · CLI floor", note: "parity floor" },
    { id: "rich", label: "rich · web", note: "this study" },
    { id: "vue", label: "vue · web app", note: "production port" },
  ];
  // per cell: a one-line description of how the world reads under that render
  const cell = {
    "generic/cli":  "the reference port. splash banner, prompt glyph, journal text.",
    "generic/rich": "engineering-notebook paper + ink. the identity.",
    "generic/vue":  "the shipped default theme.",
    "carwars/cli":  "ASCII splash + ⅋> prompt; palette & texture drop, lexicon stays.",
    "carwars/rich": "asphalt + hazard, bone-on-black, stencil mark. ink default.",
    "carwars/vue":  "same pack, native widgets.",
    "credentials/cli": "dim is just text here; the booth survives as lexicon.",
    "credentials/rich": "scanline charcoal, stamp-red, pixel mark. ink-only.",
    "credentials/vue":  "same pack, native widgets.",
    "coronate_the_regent/cli": "pastel can't cross the wire; the tutor's lilt does.",
    "coronate_the_regent/rich": "guilloché orchid, rose danger, engraved mark.",
    "coronate_the_regent/vue":  "same pack, native widgets.",
  };
  return (
    <section>
      <SecHead idx="§0" title="The matrix gains an axis" sub="{world} × {render}" />
      <p className="prose" style={{ maxWidth: 880, marginBottom: 16 }}>
        Render profiles already let one story render from a 40-column terminal to a
        Vue app, each clearing the same floor. World profiles are the orthogonal move:
        one client renders <i>many</i> worlds, each clearing the same floor. The cell
        where they meet is a <b>costume that honors the render profile</b> — paint and
        texture degrade exactly as content does, and the lexicon rides all the way
        down to the terminal.
      </p>
      <table className="wp-matrix">
        <thead>
          <tr>
            <th style={{ width: 130 }}>render ↓ / world →</th>
            {worlds.map(w => {
              const p = WP_PROFILES.get(w);
              return (
                <th key={w}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <WpGlyph profile={p} style={{ fontSize: 13 }} />
                    <span>{p.display_name}</span>
                  </div>
                  <Swatches profile={p} mode={p.default_mode} />
                  <span className={"policy " + p.mode_policy} style={{ marginTop: 5, display: "inline-block" }}>
                    {p.mode_policy.replace("_", " ")}
                  </span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {renders.map(r => (
            <tr key={r.id}>
              <th>
                {r.label}
                <span className="cell-k" style={{ marginTop: 4 }}>{r.note}</span>
              </th>
              {worlds.map(w => {
                const isId = w === "generic";
                return (
                  <td key={w} className={(isId ? "cell-id " : "") + (r.id === "rich" ? "cell-on" : "")}>
                    {cell[w + "/" + r.id]}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="margin-note" style={{ marginTop: 14, maxWidth: 880 }}>
        The shaded column is the identity profile — every unknown world falls back to
        it. The blue-edged row is what this document renders concretely.
      </div>
    </section>
  );
}

// ===========================================================================
// §1 — the negotiation handshake
// ===========================================================================
function HandshakeSection() {
  return (
    <section style={{ marginTop: 40 }}>
      <SecHead idx="§1" title="The handshake" sub="how a pack is offered & accepted" />
      <p className="prose" style={{ maxWidth: 880, marginBottom: 16 }}>
        This is the load-bearing question: <i>what has to cross the wire for a backend
        to propose a re-brand and a client to accept it?</i> The answer mirrors the
        render-capability handshake exactly, run in the other direction. The client
        already tells the backend what it can <i>render</i>; now it also tells the
        backend what it can <i>theme</i>. The backend answers with a pack. Each side
        keeps only what it understands.
      </p>

      <div className="wp-handshake">
        <div className="wp-hs-side">
          <h4>Client <span className="role-tag">front end</span></h4>
          <div className="tiny muted" style={{ fontFamily: "var(--mono)" }}>
            advertises, in GET /story/info reply or a capability frame:
          </div>
          <ul>
            <li><code>render_caps</code> — already shipped (ascii / rich / vue, width, color)</li>
            <li><code>theme_surface</code> — the closed list of slots it can paint</li>
            <li><code>mode_caps</code> — can it do <code>ink</code>? <code>light</code>? both?</li>
            <li><code>face_caps</code> — will it load a declared display face, or ignore it?</li>
          </ul>
          <div className="tiny muted" style={{ marginTop: "auto", fontFamily: "var(--mono)" }}>
            a client that advertises an empty <code>theme_surface</code> is the generic
            renderer. It still conforms.
          </div>
        </div>

        <div className="wp-hs-mid">
          <div className="wp-hs-arrow">
            <span className="dir">▲</span>
            <span className="wire">render_caps + theme_surface</span>
            <span className="tiny muted">client → backend</span>
          </div>
          <div className="wp-hs-arrow">
            <span className="wire" style={{ borderColor: "var(--accent)", background: "rgba(178,58,29,0.06)", color: "var(--accent-ink)" }}>
              world_profile pack
            </span>
            <span className="dir">▼</span>
            <span className="tiny muted">backend → client</span>
          </div>
        </div>

        <div className="wp-hs-side">
          <h4>Backend / World <span className="role-tag" style={{ background: "var(--accent)" }}>bundle</span></h4>
          <div className="tiny muted" style={{ fontFamily: "var(--mono)" }}>
            publishes in metadata.world_profile:
          </div>
          <ul>
            <li><code>palette.{`{light|ink}`}</code> — values for the fixed token set</li>
            <li><code>mode_policy</code> — may declare a single theme (<code>ink_only</code>)</li>
            <li><code>type_register.display</code> — one face, heads + wordmark only</li>
            <li><code>texture</code> · <code>logo</code> · <code>lexicon</code> · <code>signature_shell</code></li>
          </ul>
          <div className="tiny muted" style={{ marginTop: "auto", fontFamily: "var(--mono)" }}>
            proposes only. The client resolves every slot against its own caps and
            drops what it can't honor.
          </div>
        </div>
      </div>

      <h3 style={{ fontFamily: "var(--serif)", fontSize: 18, margin: "24px 0 10px" }}>
        Three ways a client can sit on this spectrum
      </h3>
      <div className="cols-3">
        {[
          { k: "bespoke", t: "Baked-in client", d: "Single-world app. The theme is hard-coded; it ignores world_profile entirely and would look wrong rendering anything else. No negotiation — and no portability.", tag: "no handshake" },
          { k: "reference", t: "Reference client (this study)", d: "Advertises a theme_surface of paintable slots; accepts any world_profile that fits, degrades the rest. One binary wears every world.", tag: "full handshake" },
          { k: "generic", t: "Generic / identity", d: "Advertises an empty surface. Renders every world in the engineering-notebook default. Always conforms; never costumed.", tag: "fallback" },
        ].map(x => (
          <div key={x.k} className="panel">
            <div className="panel-hd"><span>{x.t}</span><span className="pill pill--ghost">{x.tag}</span></div>
            <div className="panel-bd">
              <p className="tiny" style={{ margin: 0, lineHeight: 1.5, fontFamily: "var(--sans)", fontSize: 12.5, color: "var(--ink-2)" }}>{x.d}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ===========================================================================
// §2 — the closed override surface (the contract)
// ===========================================================================
function ContractSection() {
  const may = [
    { name: "palette.*", desc: <>New <i>values</i> for the fixed token set: <code>--paper</code>, <code>--ink…4</code>, <code>--accent</code>, <code>--ok/warn/bad</code>. As loud as you like.</> },
    { name: "mode_policy", desc: <>Ship <code>dual</code>, or declare a single <code>ink_only</code> / <code>light_only</code> theme. The booth is always dim.</> },
    { name: "type_register.display", desc: <>One display face, bound to the wordmark + section heads. Never body, never widgets.</> },
    { name: "texture", desc: <>A named substrate the client knows how to paint: <code>asphalt</code>, <code>scanline</code>, <code>guilloche</code>…</> },
    { name: "logo", desc: <>Which letter is turned 180°, and its treatment (<code>stencil</code> / <code>stamp</code> / <code>engraved</code>).</> },
    { name: "lexicon", desc: <>Surface copy: a candidate becomes a runner becomes a rival. Rides all the way to the CLI.</> },
    { name: "signature_shell", desc: <>A <i>preference</i>. The client may override it for its form factor.</> },
  ];
  const mayNot = [
    { name: "token set", desc: <>No new custom-property <i>names</i>. The palette is closed; you re-value it, you don't extend it.</> },
    { name: "fragment shapes", desc: <>No new <code>fragment_type</code>, <code>accepts.kind</code>, or <code>value_type</code>. Theming is presentation, not vocabulary.</> },
    { name: "widget geometry", desc: <>A profile can't move, hide, or reorder a widget. Decision legibility is non-negotiable.</> },
    { name: "the four gates", desc: <>CLI floor, decision legibility, time parity, input parity hold under every costume.</> },
    { name: "a 4th body font", desc: <>The three-role stack (prose / mono / chrome) is fixed. The display face is the one sanctioned exception, scoped tight.</> },
    { name: "shell ergonomics", desc: <>Same gestures, same hotkeys, same commit payloads. Different feel, identical muscle memory.</> },
  ];
  return (
    <section style={{ marginTop: 40 }}>
      <SecHead idx="§2" title="The override surface is closed" sub="full costume, same skeleton" />
      <p className="prose" style={{ maxWidth: 880, marginBottom: 16 }}>
        Here is how "full costume" and "still family" stop fighting. The <i>surface</i>
        a world may theme is a fixed, closed list of slots — but the <i>values</i> it
        drops into them are unbounded. This is the precise mirror of the genre rule:
        a bundle adds <code className="mono">kind=</code> strings freely but never a new{" "}
        <code className="mono">fragment_type</code>. A profile re-values <code className="mono">--accent</code> to
        hazard-orange or rose freely, but never adds <code className="mono">--neon</code>.
      </p>
      <div className="wp-contract">
        <div className="col may">
          <h4><span className="dot">●</span> A world MAY override</h4>
          {may.map(s => (
            <div key={s.name} className="wp-slot">
              <span className="name">{s.name}</span>
              <span className="desc">{s.desc}</span>
            </div>
          ))}
        </div>
        <div className="col may-not">
          <h4><span className="dot">●</span> A world MAY NOT touch</h4>
          {mayNot.map(s => (
            <div key={s.name} className="wp-slot">
              <span className="name">{s.name}</span>
              <span className="desc">{s.desc}</span>
            </div>
          ))}
        </div>
      </div>

      <h3 style={{ fontFamily: "var(--serif)", fontSize: 18, margin: "24px 0 10px" }}>
        The pack, on the wire <span className="note note--small">— carwars, abridged</span>
      </h3>
      <CodeBlock />
    </section>
  );
}

function CodeBlock() {
  const lines = [
    ['k', 'world_profile'], ['p', ': {'],
    ['nl'],
    ['i', '  world'], ['p', ': '], ['s', '"carwars"'], ['p', ','],
    ['nl'],
    ['i', '  mode_policy'], ['p', ': '], ['s', '"dual"'], ['p', ',  '], ['c', '// or ink_only — a world may ship one theme'],
    ['nl'],
    ['i', '  palette'], ['p', ': { '], ['i', 'ink'], ['p', ': { '],
    ['v', '"paper"'], ['p', ':'], ['s', '"#14110c"'], ['p', ', '],
    ['v', '"ink"'], ['p', ':'], ['s', '"#ece0c2"'], ['p', ', '],
    ['v', '"accent"'], ['p', ':'], ['s', '"#e2531a"'], ['p', ' … } },'],
    ['nl'],
    ['i', '  type_register'], ['p', ': { '], ['v', 'display'], ['p', ': '], ['s', '"Saira Stencil One"'], ['p', ' },  '], ['c', '// heads + wordmark ONLY'],
    ['nl'],
    ['i', '  texture'], ['p', ': '], ['s', '"asphalt"'], ['p', ', '],
    ['i', 'logo'], ['p', ': { '], ['v', 'letter'], ['p', ':'], ['s', '"W"'], ['p', ', '], ['v', 'treatment'], ['p', ':'], ['s', '"stencil"'], ['p', ' },'],
    ['nl'],
    ['i', '  lexicon'], ['p', ': { '], ['v', 'subject'], ['p', ':'], ['s', '"the rig"'], ['p', ', '], ['v', 'findings'], ['p', ':'], ['s', '"diagnostics"'], ['p', ' … },'],
    ['nl'],
    ['i', '  signature_shell'], ['p', ': '], ['s', '"dossier"'], ['p', '  '], ['c', '// a preference, not a demand'],
    ['nl'],
    ['p', '}'],
  ];
  const colorOf = { k: "#8db4ff", i: "#e8dfc6", p: "#8a8472", s: "#d88b52", v: "#c9a24a", c: "#6a8a4a", nl: null };
  const out = [];
  let cur = [];
  lines.forEach((tok, idx) => {
    if (tok[0] === "nl") { out.push(cur); cur = []; }
    else cur.push(<span key={idx} style={{ color: colorOf[tok[0]] }}>{tok[1]}</span>);
  });
  if (cur.length) out.push(cur);
  return (
    <pre style={{
      margin: 0, background: "#15140f", color: "#e8dfc6", border: "1.5px solid var(--ink)",
      boxShadow: "3px 3px 0 0 var(--ink)", padding: "14px 16px", fontFamily: "var(--mono)",
      fontSize: 12.5, lineHeight: 1.7, overflowX: "auto",
    }}>
      {out.map((ln, i) => <div key={i}>{ln.length ? ln : "\u00a0"}</div>)}
    </pre>
  );
}

Object.assign(window, {
  turnLetter, WpGlyph, WpWordmark, WorldSkin, SecHead, Swatches,
  TopBanner, Lede, MatrixSection, HandshakeSection, ContractSection,
});
