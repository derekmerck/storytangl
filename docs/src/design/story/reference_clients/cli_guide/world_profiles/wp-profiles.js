// wp-profiles.js — World Profile packs (the "rebrand pack" wire format).
//
// A WorldProfile is to the *render* layer what a genre bundle is to the
// *vocabulary* layer: a configuration, never new primitives. Where a bundle
// adds kind= strings but never a fragment_type, a profile overrides token
// VALUES but never the token SET. The override surface is closed; the values
// dropped into it can be as loud as the world likes. "Full costume, same
// skeleton."
//
// The object below is the literal thing a backend would publish at
// GET /story/info (metadata.world_profile). The reference client reads it,
// keeps the slots it understands, and ignores the rest — degrading to the
// generic identity profile slot-by-slot. A client that ignores the whole
// world layer still conforms; it just renders the engineering-notebook
// default, exactly as a client that ignores the genre layer still renders
// generic pieces.
//
// CLOSED OVERRIDE SURFACE (the only themeable slots):
//   palette.{light|ink}  — values for the FIXED kit token set, nothing new
//   mode_policy          — dual | light_only | ink_only  (a world may ship one theme)
//   type_register.display— ONE display face, bound to wordmark + section heads only
//   texture              — a named substrate the client knows how to paint
//   logo                 — { letter, treatment }  the turned-glyph mark
//   lexicon              — surface copy substitutions (never structural)
//   signature_shell      — a PREFERENCE; client may override for its form factor
//
// FORBIDDEN (the floor — mirrors §10 of the vocab digest):
//   new token names · new fragment shapes · new shells · 4th body font ·
//   anything that moves a widget, breaks decision-legibility, or defeats a
//   conformance gate. A profile paints the room; it cannot move the walls.

window.WP_PROFILES = (function () {

  // The closed kit token set a profile is allowed to set values for.
  // (Used by the doc to render the "what may be overridden" inventory and
  //  by applyProfile to whitelist — a value for any key NOT here is dropped.)
  const TOKEN_SLOTS = [
    "paper", "paper-2", "paper-3",
    "ink", "ink-2", "ink-3", "ink-4",
    "rule", "rule-strong",
    "accent", "accent-ink", "blue-pencil",
    "ok", "warn", "bad",
    "grid", "grid-minor",
  ];

  // ---- GENERIC — the identity profile. No overrides. This is the slot every
  //      unknown world falls back to, and the "default world profile" cell of
  //      the matrix. Engineering-notebook paper + ink.
  const generic = {
    world: "generic",
    display_name: "StoryTangl",
    tagline: "the identity profile · default render",
    voice: "dry, parsimonious, research-grade",
    signature_shell: "dossier",
    mode_policy: "dual",
    default_mode: "light",
    logo: { letter: "G", treatment: "plain" },
    type_register: { display: null, display_role: null },
    texture: "graph",
    palette: { light: null, ink: { /* kit has no built-in ink; supply one */
      "paper": "#15140f", "paper-2": "#1f1e18", "paper-3": "#2a2920",
      "ink": "#e8dfc6", "ink-2": "#c9c2ad", "ink-3": "#8a8472", "ink-4": "#6b6a64",
      "rule": "#2f2d24", "rule-strong": "#4d4a3d",
      "accent": "#e07a40", "accent-ink": "#f0a06a", "blue-pencil": "#8db4ff",
      "ok": "#6fbf8c", "warn": "#d6a35a", "bad": "#d65a4a",
      "grid": "#23221b", "grid-minor": "#1c1b15",
    } },
    lexicon: {
      subject: "the subject", parts: "its parts", findings: "findings",
      move_primary: "Proceed.", move_second: "Set it aside.",
      move_locked: "Escalate.", locked_reason: "Threshold not met.",
      resource: "Budget", roster: "On record", score: "Standing",
      prose: "A **subject** is set before you; its parts lie open. Three findings stand on the record. Three moves remain — and one is barred.",
      cmd: "try: inspect · set aside · escalate",
    },
  };

  // ---- CARWARS — Mad Max, American Southwest, 2-bit gamebook. Silhouettes,
  //      hazard stripes, sun-bleached bone on asphalt. Night is home (ink
  //      default) but it survives daylight too (dual). Turned W → reads as M.
  const carwars = {
    world: "carwars",
    display_name: "Car Wars",
    tagline: "outfit the rig · drive the gauntlet",
    voice: "deadpan wasteland; nouns are gear, verbs are violence",
    signature_shell: "dossier",
    mode_policy: "dual",
    default_mode: "ink",
    logo: { letter: "W", treatment: "stencil" },
    type_register: { display: "'Saira Stencil One', 'Arial Narrow', sans-serif",
                     display_role: "wordmark + section heads only" },
    texture: "asphalt",
    palette: {
      ink: {
        "paper": "#14110c", "paper-2": "#1e1810", "paper-3": "#2a2114",
        "ink": "#ece0c2", "ink-2": "#cdbd97", "ink-3": "#90815f", "ink-4": "#695d44",
        "rule": "#3a2f1c", "rule-strong": "#5e4c2c",
        "accent": "#e2531a", "accent-ink": "#ff8a3d", "blue-pencil": "#c9a24a",
        "ok": "#93a23f", "warn": "#d8962a", "bad": "#d2371a",
        "grid": "#221b11", "grid-minor": "#1a150d",
      },
      light: {
        "paper": "#d6cbb0", "paper-2": "#cabd9d", "paper-3": "#bcad87",
        "ink": "#1f180e", "ink-2": "#3d3119", "ink-3": "#6a5a39", "ink-4": "#8f7d54",
        "rule": "#a8966f", "rule-strong": "#5e4c2c",
        "accent": "#bf3f12", "accent-ink": "#7a2708", "blue-pencil": "#8a6a26",
        "ok": "#6e7a2a", "warn": "#a8701a", "bad": "#b2301a",
        "grid": "#c2b48d", "grid-minor": "#cfc29c",
      },
    },
    lexicon: {
      subject: "the rig", parts: "the loadout", findings: "diagnostics",
      move_primary: "Bolt it on.", move_second: "Strip it for weight.",
      move_locked: "Floor it onto the gauntlet.", locked_reason: "Chassis over weight — shed mass first.",
      resource: "Build credit", roster: "On the chassis", score: "Kill tally",
      prose: "The **rig** sits up on blocks under the sodium lamps. Its loadout is laid out on the tarp. Three diagnostics flag amber and red. Three moves remain — and the gauntlet is barred until you make weight.",
      cmd: "try: mount autocannon · strip plating · drive",
    },
  };

  // ---- CREDENTIALS — Papers, Please. The booth is always dim, so the world
  //      declares ink_only: a single, non-negotiable theme. Cold institutional
  //      bone on charcoal; stamp-red is the only heat. 8-bit pixel wordmark.
  const credentials = {
    world: "credentials",
    display_name: "Credentials",
    tagline: "inspect the packet · render disposition",
    voice: "bureaucratic, clipped, Kafkaesque; the rules change at shift start",
    signature_shell: "dossier",
    mode_policy: "ink_only",            // <-- a world may ship ONE theme
    default_mode: "ink",
    logo: { letter: "C", treatment: "stamp" },
    type_register: { display: "'Silkscreen', 'Courier New', monospace",
                     display_role: "wordmark + section heads only" },
    texture: "scanline",
    palette: {
      ink: {
        "paper": "#14171a", "paper-2": "#1c2024", "paper-3": "#262b30",
        "ink": "#c3c8bd", "ink-2": "#9aa198", "ink-3": "#6d736b", "ink-4": "#4d534c",
        "rule": "#2b3035", "rule-strong": "#454c52",
        "accent": "#b23a2a", "accent-ink": "#e0644a", "blue-pencil": "#5d808f",
        "ok": "#5f8a59", "warn": "#b08a39", "bad": "#c23a2a",
        "grid": "#1a1e22", "grid-minor": "#161a1d",
      },
      light: null,                       // declared absent — client must not invent it
    },
    lexicon: {
      subject: "the candidate", parts: "the packet", findings: "findings",
      move_primary: "Deny passage.", move_second: "Detain for questioning.",
      move_locked: "Allow passage.", locked_reason: "Permit expired — allow is barred.",
      resource: "Shift", roster: "Today's gate", score: "Accuracy",
      prose: "The **candidate** waits at the slot, breath fogging the glass. Their packet is unfolded on the counter. Three findings stand — one stamped red. Three dispositions remain, and the lawful one is barred.",
      cmd: "try: inspect ticket · verify id · deny",
    },
  };

  // ---- CORONATE THE REGENT — Long Live the Queen, soft-pastel court. Political
  //      machination under a dating-sim sheen; in this world danger is *pretty*
  //      (death comes in rose). Candlelit night court is the alt mode (dual).
  const regent = {
    world: "coronate_the_regent",
    display_name: "Coronate the Regent",
    tagline: "survive the week · hold the crown",
    voice: "courtly, sweet on top, lethal underneath; a tutor's lilt",
    signature_shell: "dossier",
    mode_policy: "dual",
    default_mode: "light",
    logo: { letter: "R", treatment: "engraved" },
    type_register: { display: "'Marcellus', 'Cormorant Garamond', serif",
                     display_role: "wordmark + section heads only" },
    texture: "guilloche",
    palette: {
      light: {
        "paper": "#f4edf4", "paper-2": "#eaddec", "paper-3": "#e1d1e5",
        "ink": "#392c45", "ink-2": "#5b4a68", "ink-3": "#8a7a95", "ink-4": "#b4a7be",
        "rule": "#dcc9e0", "rule-strong": "#bb9fc3",
        "accent": "#bb456e", "accent-ink": "#8f2e54", "blue-pencil": "#5a6db2",
        "ok": "#5a9a7c", "warn": "#c98e3a", "bad": "#bb456e",
        "grid": "#e6d8e9", "grid-minor": "#efe5f1",
      },
      ink: {
        "paper": "#1e1726", "paper-2": "#281f33", "paper-3": "#33293f",
        "ink": "#eddff1", "ink-2": "#c9b6d2", "ink-3": "#9785a3", "ink-4": "#6f6079",
        "rule": "#3a2f48", "rule-strong": "#574668",
        "accent": "#e8769e", "accent-ink": "#f4a0bf", "blue-pencil": "#9aa6e8",
        "ok": "#7cc2a0", "warn": "#e0b05c", "bad": "#e8769e",
        "grid": "#271f32", "grid-minor": "#221b2c",
      },
    },
    lexicon: {
      subject: "the court", parts: "the week's lessons", findings: "the mood of the room",
      move_primary: "Receive the visiting prince.", move_second: "Train at arms instead.",
      move_locked: "Sign the treaty.", locked_reason: "You are not yet crowned — the treaty must wait.",
      resource: "The week", roster: "At court", score: "Approval",
      prose: "The **court** assembles below the dais. This week's lessons are set out — posture, poison, the dance. Three currents move through the room; one carries a knife. Three choices stand, and the throne's own business is barred until you wear it.",
      cmd: "try: receive prince · train arms · study graces",
    },
  };

  const ALL = { generic, carwars, credentials, coronate_the_regent: regent };
  const ORDER = ["generic", "carwars", "credentials", "coronate_the_regent"];

  // Resolve the effective mode for a profile given a requested mode, honoring
  // mode_policy (a world that declares ink_only refuses light, etc).
  function resolveMode(profile, requested) {
    const pol = profile.mode_policy;
    if (pol === "ink_only") return "ink";
    if (pol === "light_only") return "light";
    return requested || profile.default_mode || "light";
  }

  // Compile the profile's palette[mode] to a React style object of CSS custom
  // properties — the literal act the client performs when it "accepts" a pack.
  // Only whitelisted token slots are applied; an unknown key is dropped on the
  // floor (the closed-surface guarantee, enforced client-side).
  function cssVars(profile, mode) {
    const m = resolveMode(profile, mode);
    const pal = (profile.palette && profile.palette[m]) || null;
    const out = {};
    if (pal) {
      for (const k of TOKEN_SLOTS) {
        if (pal[k] != null) out["--" + k] = pal[k];
      }
    }
    if (profile.type_register && profile.type_register.display) {
      out["--wp-display"] = profile.type_register.display;
    }
    return out;
  }

  function get(name) { return ALL[name] || generic; }

  return { ALL, ORDER, TOKEN_SLOTS, get, resolveMode, cssVars,
           generic, carwars, credentials, regent };
})();
