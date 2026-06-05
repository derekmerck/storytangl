// wp-fixtures.js — content for the World Profiles doc.
//
//   1. CARWARS — a full, authored envelope (no prior fixture existed). Exercises
//      slot zones w/ weight capacity, a parts catalog, a drive stat_check, and
//      a disposition barred by an over-weight blocker — the carwars stresses
//      named in VOCAB_DIGEST §11.
//
//   2. SHARED_TURN — ONE structural fragment graph (same uids, order, types,
//      ui_hints) that every world fills with its own surface copy. This is the
//      proof exhibit: identical skeleton, four costumes. Structure is the
//      constant; content + paint vary.
//
//   credentials and coronate_the_regent reuse the existing v1.5 genre fixtures
//   (window.V15_FIXTURES_GENRES) — loaded before this file.
//
// Nothing here invents a fragment_type, accepts.kind, or value_type. carwars
// adds only kind= strings (chassis/weapon/plating/utility) and a zone_role
// ("slot"), exactly as the genre-extension rules allow.

window.WP_FIXTURES = (function () {

  // =========================================================================
  // CARWARS — "The Sandcat", up on blocks, mid-outfit
  // =========================================================================
  const carwars = {
    envelope: {
      cursor_id: "carwars-sandcat",
      step: 6,
      fragments: [
        { uid: "g-scene", fragment_type: "group", group_type: "scene",
          member_ids: [
            "c-prose",
            "z-turret", "z-hull", "z-under",
            "f-diag",
            "z-yard",
            "ch-mount", "ch-strip", "ch-drive", "ch-cmd",
          ] },

        { uid: "c-prose", fragment_type: "content", content_format: "md",
          content: "The **Sandcat** sits up on blocks under the sodium lamps. Gauntlet's at first light and you're a hundred kilos over the weight you can still steer. Strip something, or bolt on and pray the suspension holds." },

        // --- slot zones (chassis mounts) -------------------------------------
        { uid: "z-turret", fragment_type: "group", group_type: "zone",
          member_ids: ["pc-autocannon"],
          layout_hints: { zone_role: "slot", orientation: "col", reveal: "all" },
          constraints: { accepts_kind: ["weapon"],
                         capacity: [{ kind: "weight", max: 120, unit: "kg", sum_property: "weight" }] },
          hints: { label_text: "Turret mount" } },

        { uid: "pc-autocannon", fragment_type: "piece",
          piece_id: "wpn-autocannon", kind: "weapon", realized: true, zone_ref: "z-turret",
          properties: { name: "Autocannon", weight: 90, ammo: 40, armor: 0 },
          hints: { label_text: "Autocannon" } },

        { uid: "z-hull", fragment_type: "group", group_type: "zone",
          member_ids: ["pc-plate-l", "pc-plate-r"],
          layout_hints: { zone_role: "slot", orientation: "col", reveal: "all" },
          constraints: { accepts_kind: ["plating", "weapon"],
                         capacity: [{ kind: "weight", max: 240, unit: "kg", sum_property: "weight" }] },
          hints: { label_text: "Hull plating" } },

        { uid: "pc-plate-l", fragment_type: "piece",
          piece_id: "plt-port", kind: "plating", realized: true, zone_ref: "z-hull",
          properties: { name: "Port plate", weight: 120, armor: 6 },
          hints: { label_text: "Port plate" } },
        { uid: "pc-plate-r", fragment_type: "piece",
          piece_id: "plt-stbd", kind: "plating", realized: true, zone_ref: "z-hull",
          properties: { name: "Starboard plate", weight: 120, armor: 6 },
          hints: { label_text: "Starboard plate" } },

        { uid: "z-under", fragment_type: "group", group_type: "zone",
          member_ids: [],
          layout_hints: { zone_role: "slot", orientation: "col", reveal: "all" },
          constraints: { accepts_kind: ["utility"],
                         capacity: [{ kind: "weight", max: 60, unit: "kg", sum_property: "weight" }] },
          hints: { label_text: "Underbody" } },

        // --- diagnostics (severity-coded findings) --------------------------
        { uid: "f-diag", fragment_type: "kv",
          content: [
            { key: "chassis_weight", value: "1,540 / 1,440", emphasis: "danger", unit: "kg" },
            { key: "turret_ammo",    value: "40 rounds",     emphasis: "ok" },
            { key: "engine_temp",    value: "running hot",   emphasis: "warn" },
          ],
          hints: { style_tags: ["findings", "inline"], label_text: "diagnostics" } },

        // --- the yard (parts catalog of offers) -----------------------------
        { uid: "z-yard", fragment_type: "group", group_type: "zone",
          member_ids: ["pc-of-spikes", "pc-of-nitro", "pc-of-mg"],
          layout_hints: { zone_role: "catalog", orientation: "grid", reveal: "all" },
          hints: { label_text: "The yard" } },

        { uid: "pc-of-spikes", fragment_type: "piece",
          piece_id: "of-spikes", kind: "utility", realized: false, zone_ref: "z-yard",
          properties: { name: "Wheel spikes", weight: 30, armor: 0 },
          cost: [{ ledger_key: "credit", delta: -2, unit: "scrip" }],
          available: true,
          hints: { label_text: "Wheel spikes", description_text: "Shreds anything that draws alongside." } },
        { uid: "pc-of-nitro", fragment_type: "piece",
          piece_id: "of-nitro", kind: "utility", realized: false, zone_ref: "z-yard",
          properties: { name: "Nitro tank", weight: 45, armor: 0 },
          cost: [{ ledger_key: "credit", delta: -4, unit: "scrip" }],
          available: true,
          hints: { label_text: "Nitro tank", description_text: "One burst of speed. Maybe two. Then nothing." } },
        { uid: "pc-of-mg", fragment_type: "piece",
          piece_id: "of-mg", kind: "weapon", realized: false, zone_ref: "z-yard",
          properties: { name: "Pintle MG", weight: 55, ammo: 200 },
          cost: [{ ledger_key: "credit", delta: -3, unit: "scrip" }],
          available: false,
          unavailable_reason: "Only 3 scrip — and the turret's already loaded.",
          hints: { label_text: "Pintle MG", description_text: "Cheap, loud, thirsty." } },

        // --- moves ----------------------------------------------------------
        { uid: "ch-mount", fragment_type: "choice", edge_id: "e-mount",
          text: "Bolt a part onto the chassis.",
          available: true,
          accepts: { kind: "place", constraints: { from_zone_ref: "z-yard" } },
          ui_hints: { hotkey: "1",
            cost_previews: [{ ledger_key: "credit", delta: -2, unit: "scrip" }],
            source: "yard", source_kind: "catalog", contribution: "transfer" } },

        { uid: "ch-strip", fragment_type: "choice", edge_id: "e-strip",
          text: "Strip a part for weight.",
          available: true,
          accepts: { kind: "pieces", min: 1, max: 1, constraints: { from_chassis: true } },
          ui_hints: { hotkey: "2", emphasis: "subtle",
            source: "chassis", source_kind: "fixture", contribution: "interaction" } },

        { uid: "ch-drive", fragment_type: "choice", edge_id: "e-drive",
          text: "Floor it onto the gauntlet.",
          available: false,
          unavailable_reason: "1,540 kg — 100 over. Shed mass before the run.",
          blockers: [
            { code: "over_weight",
              message: "Chassis 1,540 kg exceeds steerable 1,440 kg.",
              refs: ["f-diag", "z-hull"] },
          ],
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "3", emphasis: "primary",
            stat_check: { label: "Gauntlet run", dice: "2d6", target: 7, modifier: -2,
                          success_text: "−2 while over weight" },
            source: "disposition", source_kind: "asset", contribution: "disposition" } },

        { uid: "ch-cmd", fragment_type: "choice", edge_id: "interpret_command",
          text: "Try a command.", available: true,
          accepts: { kind: "raw_command" },
          ui_hints: { hotkey: ">", reserved: "command_bar" } },
      ],
      metadata: {
        world: "carwars",
        grammar: {
          verbs: [
            { verb: "mount",  aliases: ["bolt"],  frames: ["mount {noun}"] },
            { verb: "strip",  aliases: ["pull"],  frames: ["strip {noun}"] },
            { verb: "drive",  aliases: ["floor", "go"], frames: ["drive"] },
          ],
          nouns: [
            { noun: "spikes", aliases: [], piece_ids: ["of-spikes"] },
            { noun: "nitro",  aliases: ["tank"], piece_ids: ["of-nitro"] },
            { noun: "plate",  aliases: ["plating"], piece_ids: ["plt-port", "plt-stbd"] },
          ],
          placeholder: "try: mount nitro · strip plate · drive",
        },
      },
    },
    projected_state: {
      sections: [
        { section_id: "credit", title: "Build credit", kind: "wallet",
          value: { value_type: "scalar", value: "3 scrip" } },
        { section_id: "weight", title: "Chassis", kind: "stats",
          value: { value_type: "kv_list", items: [
            { key: "weight", value: 1540, max: 1440, unit: "kg", hint: "bar", emphasis: "danger" },
            { key: "armor",  value: 12, max: 24, unit: "ar", hint: "bar", emphasis: "ok" },
            { key: "ammo",   value: 40, max: 40, unit: "rd", hint: "bar", emphasis: "ok" },
          ] } },
        { section_id: "loadout", title: "On the chassis", kind: "roster",
          value: { value_type: "item_list", items: [
            { label: "Autocannon", detail: "turret · 90 kg · 40 rd", tags: ["weapon"] },
            { label: "Port plate", detail: "hull · 120 kg · +6 ar", tags: ["plating"] },
            { label: "Starboard plate", detail: "hull · 120 kg · +6 ar", tags: ["plating"] },
          ] } },
        { section_id: "tally", title: "Kill tally", kind: "score",
          value: { value_type: "scalar", value: 11 } },
      ],
    },
  };

  // =========================================================================
  // SHARED_TURN — one structural skeleton, world-specific fills.
  // =========================================================================
  // The skeleton (fixed for every world):
  //   scene → [ prose, parts-zone(3 pieces), findings(3 rows: ok/warn/danger),
  //             choice·primary(avail), choice·second(avail),
  //             choice·locked(blocker), command ]
  //   rail  → [ resource(kv bar), roster(item_list ×3), score(scalar) ]
  //
  // Only the strings change between worlds. uids, order, types, ui_hints,
  // emphases, blocker shape — all identical. Diff two of these envelopes and
  // the only deltas are content. That is the whole claim.

  const SHARED_CONTENT = {
    generic: {
      pieces: [
        { kind: "item", label: "Item A", meta: "—" },
        { kind: "item", label: "Item B", meta: "—" },
        { kind: "item", label: "Item C", meta: "—" },
      ],
      findings: [
        { key: "check_one",   value: "pass",  emphasis: "ok" },
        { key: "check_two",   value: "review", emphasis: "warn" },
        { key: "check_three", value: "flag",  emphasis: "danger" },
      ],
      resource: { key: "budget", value: 42, max: 90, unit: "u" },
      roster: [
        { label: "Record 1", detail: "logged", tags: ["entry"] },
        { label: "Record 2", detail: "logged", tags: ["entry"] },
        { label: "Record 3", detail: "open",   tags: ["entry"] },
      ],
      score: "—",
    },
    carwars: {
      pieces: [
        { kind: "weapon",  label: "Autocannon",  meta: "90 kg" },
        { kind: "plating", label: "Port plate",  meta: "120 kg" },
        { kind: "plating", label: "Stbd plate",  meta: "120 kg" },
      ],
      findings: [
        { key: "turret_ammo",    value: "40 rd",        emphasis: "ok" },
        { key: "engine_temp",    value: "running hot",  emphasis: "warn" },
        { key: "chassis_weight", value: "100 kg over",  emphasis: "danger" },
      ],
      resource: { key: "scrip", value: 3, max: 12, unit: "scrip" },
      roster: [
        { label: "Autocannon", detail: "turret · 40 rd", tags: ["weapon"] },
        { label: "Port plate", detail: "hull · +6 ar",   tags: ["plating"] },
        { label: "Stbd plate", detail: "hull · +6 ar",   tags: ["plating"] },
      ],
      score: "11 kills",
    },
    credentials: {
      pieces: [
        { kind: "permit",  label: "Permit",  meta: "Imperial" },
        { kind: "id_card", label: "ID card", meta: "Kalden" },
        { kind: "ticket",  label: "Ticket",  meta: "→ Gate" },
      ],
      findings: [
        { key: "permit_seal",   value: "Imperial",   emphasis: "ok" },
        { key: "origin",        value: "Kalden",     emphasis: "warn" },
        { key: "permit_expiry", value: "2026-03-01", emphasis: "danger" },
      ],
      resource: { key: "shift", value: 42, max: 90, unit: "min" },
      roster: [
        { label: "Anya Volkov", detail: "allowed ✓", tags: ["cleared"] },
        { label: "Tomi Ren",    detail: "denied ✓",  tags: ["cleared"] },
        { label: "Bek Tarsus",  detail: "open",      tags: ["current"] },
      ],
      score: "2 / 2 correct",
    },
    coronate_the_regent: {
      pieces: [
        { kind: "lesson", label: "Posture", meta: "court" },
        { kind: "lesson", label: "Poison",  meta: "intrigue" },
        { kind: "lesson", label: "The dance", meta: "charm" },
      ],
      findings: [
        { key: "the_prince",  value: "favorable",  emphasis: "ok" },
        { key: "the_council", value: "watchful",   emphasis: "warn" },
        { key: "the_duke",    value: "plotting",   emphasis: "danger" },
      ],
      resource: { key: "the week", value: 2, max: 4, unit: "of 4" },
      roster: [
        { label: "The Prince",  detail: "charmed",  tags: ["ally"] },
        { label: "The Council", detail: "wary",     tags: ["court"] },
        { label: "The Duke",    detail: "rival",    tags: ["threat"] },
      ],
      score: "approval 61",
    },
  };

  function buildSharedTurn(worldName, profile) {
    const lex = profile.lexicon;
    const c = SHARED_CONTENT[worldName] || SHARED_CONTENT.generic;
    const pieceFrags = c.pieces.map((p, i) => ({
      uid: "pc-" + i, fragment_type: "piece",
      piece_id: "pc-" + i, kind: p.kind, realized: true, zone_ref: "z-parts",
      properties: { name: p.label, weight: undefined },
      hints: { label_text: p.label + (p.meta && p.meta !== "—" ? "  ·  " + p.meta : "") },
    }));
    return {
      envelope: {
        cursor_id: "shared-" + worldName, step: 7,
        fragments: [
          { uid: "g-scene", fragment_type: "group", group_type: "scene",
            member_ids: ["c-prose", "z-parts", "f-find", "ch-a", "ch-b", "ch-locked", "ch-cmd"] },
          { uid: "c-prose", fragment_type: "content", content_format: "md", content: lex.prose },
          { uid: "z-parts", fragment_type: "group", group_type: "zone",
            member_ids: pieceFrags.map(p => p.uid),
            layout_hints: { zone_role: "field", orientation: "row", reveal: "all" },
            hints: { label_text: lex.parts } },
          ...pieceFrags,
          { uid: "f-find", fragment_type: "kv",
            content: c.findings.map(f => ({ key: f.key, value: f.value, emphasis: f.emphasis })),
            hints: { style_tags: ["findings", "inline"], label_text: lex.findings } },
          { uid: "ch-a", fragment_type: "choice", edge_id: "e-a", text: lex.move_primary,
            available: true, accepts: { kind: "pick" },
            ui_hints: { hotkey: "1", emphasis: "primary", source: "world", source_kind: "fixture" } },
          { uid: "ch-b", fragment_type: "choice", edge_id: "e-b", text: lex.move_second,
            available: true, accepts: { kind: "pick" },
            ui_hints: { hotkey: "2", emphasis: "subtle", source: "world", source_kind: "fixture" } },
          { uid: "ch-locked", fragment_type: "choice", edge_id: "e-locked", text: lex.move_locked,
            available: false, unavailable_reason: lex.locked_reason,
            blockers: [{ code: "barred", message: lex.locked_reason, refs: ["f-find"] }],
            accepts: { kind: "pick" },
            ui_hints: { hotkey: "3", emphasis: "danger", source: "disposition", source_kind: "asset" } },
          { uid: "ch-cmd", fragment_type: "choice", edge_id: "interpret_command",
            text: "Try a command.", available: true, accepts: { kind: "raw_command" },
            ui_hints: { hotkey: ">", reserved: "command_bar" } },
        ],
        metadata: { world: worldName, grammar: { verbs: [], nouns: [], placeholder: lex.cmd } },
      },
      projected_state: {
        sections: [
          { section_id: "resource", title: lex.resource, kind: "resource",
            value: { value_type: "kv_list", items: [
              { key: c.resource.key, value: c.resource.value, max: c.resource.max, unit: c.resource.unit, hint: "bar" },
            ] } },
          { section_id: "roster", title: lex.roster, kind: "roster",
            value: { value_type: "item_list", items: c.roster } },
          { section_id: "score", title: lex.score, kind: "score",
            value: { value_type: "scalar", value: c.score } },
        ],
      },
    };
  }

  // Pull the existing genre fixtures (loaded separately).
  function genre(name) {
    const G = window.V15_FIXTURES_GENRES || {};
    if (name === "credentials") return G.credentials;
    if (name === "coronate_the_regent") return G.training;  // training fixture IS coronate_the_regent
    return null;
  }

  return { carwars, buildSharedTurn, SHARED_CONTENT, genre };
})();
