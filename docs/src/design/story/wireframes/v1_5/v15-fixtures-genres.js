// v15-fixtures-genres.js — fixtures for the 4 Tier P3 genre extensions
// bundled into the v1.5 wireframe doc.
//
//   credentials   — packet inspection, severity-coded findings, mediation
//   training      — scheduled study, mood modulator, stat_check preview
//   elefant_hunt  — graph-traversal board, composite hunt roll, journal-as-story
//
// Every fixture is a normal { envelope, projected_state } pair. The same
// widgets + shells from v15-widgets.jsx / v15-shells.jsx render them.
// Genre layers are pure enrichments — choice ui_hints sub-shapes, additional
// piece kinds, conventional projected section kinds. No new fragment types.

window.V15_FIXTURES_GENRES = (function () {

  // ==========================================================================
  // CREDENTIALS — Bek Tarsus, mid-inspection (Papers-Please-style)
  // ==========================================================================
  // Demonstrates:
  //   - PieceFragment(kind="candidate") + a packet zone of document pieces
  //   - KvFragment with severity-coded findings (KvRow.emphasis ok/warn/danger)
  //   - Disposition severity (primary/warning/danger) via ui_hints.emphasis
  //   - Blocker[] on disposition; restriction map projected as kv_list
  //   - Shift summary table; time-remaining bar
  const credentials = {
    envelope: {
      cursor_id: "cred-bek-t2",
      step: 14,
      fragments: [
        { uid: "g-scene", fragment_type: "group", group_type: "scene",
          member_ids: [
            "c-prose", "pc-cand",
            "z-packet", "f-findings",
            "ch-inspect", "ch-verify", "ch-search",
            "ch-allow", "ch-deny", "ch-arrest",
            "ch-cmd",
          ] },

        { uid: "c-prose", fragment_type: "content", content_format: "md",
          content: "You unfold the permit. The **Imperial seal** is sound, but the date stamp shows expiry months past. Bek waits without expression, breath fogging the slot." },

        // Candidate piece (not in packet zone)
        { uid: "pc-cand", fragment_type: "piece",
          piece_id: "bek-tarsus", kind: "candidate", realized: true,
          properties: {
            name: "Bek Tarsus",
            declared_purpose: "merchant",
            declared_origin: "Kalden",
          },
          hints: { label_text: "Bek Tarsus" } },

        // Packet zone (zone_role="packet")
        { uid: "z-packet", fragment_type: "group", group_type: "zone",
          member_ids: ["pc-permit", "pc-id", "pc-ticket"],
          layout_hints: { orientation: "row", reveal: "all", zone_role: "packet" },
          hints: { label_text: "Credentials packet" } },

        { uid: "pc-permit", fragment_type: "piece",
          piece_id: "permit-9472", kind: "permit", realized: true,
          zone_ref: "z-packet",
          properties: {
            name: "Permit", seal: "Imperial", holder: "Bek Tarsus",
            expiry: "2026-03-01", purpose: "merchant",
          },
          hints: { label_text: "Permit (Imperial)",
                   description_text: "expires 2026-03-01" } },

        { uid: "pc-id", fragment_type: "piece",
          piece_id: "id-3382", kind: "id_card", realized: true,
          zone_ref: "z-packet",
          properties: {
            name: "ID card", holder: "Bek Tarsus", origin: "Kalden",
          },
          hints: { label_text: "ID card" } },

        { uid: "pc-ticket", fragment_type: "piece",
          piece_id: "ticket-117", kind: "ticket", realized: true,
          zone_ref: "z-packet",
          properties: {
            name: "Travel ticket", origin: "Kalden",
            destination: "Imperial Gate", issued: "2026-05-19",
          },
          hints: { label_text: "Travel ticket" } },

        // Findings — scene-bound KvFragment with severity-coded rows
        { uid: "f-findings", fragment_type: "kv",
          content: [
            { key: "permit_seal",   value: "Imperial",  emphasis: "ok",
              code: "seal_valid",     target: "pc-permit", state: "verified" },
            { key: "permit_holder", value: "Bek Tarsus", emphasis: "ok",
              code: "holder_match",   target: "pc-permit", state: "verified" },
            { key: "permit_expiry", value: "2026-03-01", emphasis: "danger",
              code: "permit_expired", target: "pc-permit", state: "flag" },
            { key: "origin",        value: "Kalden",     emphasis: "warn",
              code: "origin_review",  target: "pc-id",     state: "flag" },
          ],
          hints: { style_tags: ["findings", "inline"], label_text: "findings" } },

        // Mediation moves
        { uid: "ch-inspect", fragment_type: "choice", edge_id: "e-inspect",
          text: "Inspect another document.",
          available: true,
          accepts: { kind: "pieces", min: 1, max: 1,
            constraints: { target_zone_ref: "z-packet" } },
          ui_hints: { hotkey: "1",
            cost_previews: [{ ledger_key: "time", delta: -1, unit: "min" }],
            source: "packet", source_kind: "fixture",
            contribution: "interaction" } },

        { uid: "ch-verify", fragment_type: "choice", edge_id: "e-verify-id",
          text: "Verify ID against registry.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "2",
            cost_previews: [{ ledger_key: "time", delta: -1, unit: "min" }],
            // genre hint — validity_check (analogous to stat_check)
            validity_check: {
              label: "Registry lookup",
              target_ref: "pc-id",
              published_rule: "ID verification",
              risk_text: "Costs 1 minute",
            },
            source: "registry", source_kind: "fixture",
            contribution: "interaction" } },

        { uid: "ch-search", fragment_type: "choice", edge_id: "e-search",
          text: "Search the candidate's belongings.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "3", emphasis: "warning",
            cost_previews: [{ ledger_key: "time", delta: -2, unit: "min" }],
            source: "candidate", source_kind: "actor",
            contribution: "interaction" } },

        // Dispositions — severity by ui_hints.emphasis
        { uid: "ch-allow", fragment_type: "choice", edge_id: "e-allow",
          text: "Allow passage.",
          available: false,
          unavailable_reason: "Permit expired (see findings).",
          blockers: [
            { code: "permit_expired",
              message: "Permit expired 2026-03-01.",
              refs: ["pc-permit", "f-findings"] },
          ],
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "a", emphasis: "primary",
            source: "disposition", source_kind: "asset",
            contribution: "disposition" } },

        { uid: "ch-deny", fragment_type: "choice", edge_id: "e-deny",
          text: "Deny passage.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "d", emphasis: "warning",
            source: "disposition", source_kind: "asset",
            contribution: "disposition" } },

        { uid: "ch-arrest", fragment_type: "choice", edge_id: "e-arrest",
          text: "Arrest.",
          available: false,
          unavailable_reason: "Insufficient evidence for arrest.",
          blockers: [
            { code: "no_arrestable_findings",
              message: "No finding with emphasis=danger that is also criminal.",
              refs: [] },
          ],
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "x", emphasis: "danger",
            source: "disposition", source_kind: "asset",
            contribution: "disposition" } },

        { uid: "ch-cmd", fragment_type: "choice", edge_id: "interpret_command",
          text: "Try a command.", available: true,
          accepts: { kind: "raw_command" },
          ui_hints: { hotkey: ">", reserved: "command_bar" } },
      ],
      metadata: {
        world: "credentials",
        grammar: {
          verbs: [
            { verb: "inspect", aliases: [], frames: ["inspect {noun}"] },
            { verb: "verify",  aliases: [], frames: ["verify {noun}"] },
            { verb: "search",  aliases: [], frames: ["search"] },
            { verb: "allow",   aliases: ["pass"], frames: ["allow"] },
            { verb: "deny",    aliases: ["reject"], frames: ["deny"] },
          ],
          nouns: [
            { noun: "permit", aliases: [], piece_ids: ["permit-9472"] },
            { noun: "id",     aliases: ["card"], piece_ids: ["id-3382"] },
            { noun: "ticket", aliases: [], piece_ids: ["ticket-117"] },
          ],
          placeholder: "try: inspect ticket · verify id · deny",
        },
      },
    },

    projected_state: {
      sections: [
        { section_id: "shift_time", title: "Shift", kind: "world_time",
          value: { value_type: "kv_list", items: [
            { key: "remaining", value: 42, max: 90, unit: "min", hint: "bar" },
            { key: "candidates", value: "3 of 8" },
          ] } },

        { section_id: "restrictions", title: "Shift directives", kind: "restrictions",
          value: { value_type: "kv_list", items: [
            { key: "Imperial citizens",    value: "allowed",                emphasis: "ok",     hint: "tag" },
            { key: "Kaldenese refugees",   value: "allowed with permit",    emphasis: "warn",   hint: "tag" },
            { key: "Eastern merchants",    value: "denied — embargo",       emphasis: "danger", hint: "tag" },
            { key: "Diplomatic envoys",    value: "privileged",             emphasis: "subtle", hint: "tag" },
          ] } },

        { section_id: "shift_summary", title: "Shift so far", kind: "shift_summary",
          value: { value_type: "table",
            columns: ["Candidate", "Decision", "Correct", "Notes"],
            rows: [
              ["Anya Volkov",  "Allowed", "✓", "purpose mismatch flagged"],
              ["Tomi Ren",     "Denied",  "✓", "permit forged"],
              ["Bek Tarsus",   "(open)",  "—", "permit expired · origin review"],
            ] } },

        { section_id: "score", title: "Accuracy", kind: "score",
          value: { value_type: "kv_list", items: [
            { key: "correct", value: 2, max: 2, unit: "of 2", hint: "fraction", emphasis: "ok" },
            { key: "salary",  value: 14, unit: "cr", delta: +6, hint: "delta" },
          ] } },
      ],
    },
  };

  // ==========================================================================
  // TRAINING — Coronate the Regent, Week 2 (Long Live the Queen-style)
  // ==========================================================================
  // Demonstrates:
  //   - Stats and skills as projected kv_list rows with hint:"bar"
  //   - Mood as projected scalar (kind="mood") + cost_previews modulation
  //   - Scheduled event = next envelope; ui_hints.stat_check preview on the
  //     triggering choice
  //   - Inventory zone with realized=true item pieces + a catalog offer
  //   - Calendar/schedule scalar (Week 2 of 4)
  const training = {
    envelope: {
      cursor_id: "training-w2",
      step: 9,
      fragments: [
        { uid: "g-scene", fragment_type: "group", group_type: "scene",
          member_ids: ["c-prose", "z-inv", "z-merchant",
                       "ch-prince", "ch-combat", "ch-charm",
                       "ch-buy-sword", "ch-cmd"] },

        { uid: "c-prose", fragment_type: "content", content_format: "md",
          content: "**Week 2.** A royal visitor is expected. The court master shrugs at your sword belt; the dance master smirks at your gait. You have one decision before the week begins." },

        // Inventory zone (Tier P2 richer rendering than badges)
        { uid: "z-inv", fragment_type: "group", group_type: "zone",
          member_ids: ["pc-inv-letter"],
          layout_hints: { orientation: "row", reveal: "all", zone_role: "hand" },
          hints: { label_text: "Inventory" } },

        { uid: "pc-inv-letter", fragment_type: "piece",
          piece_id: "letter-mother", kind: "item", realized: true,
          zone_ref: "z-inv", owner: "regent",
          properties: { name: "Mother's letter" },
          hints: { label_text: "Mother's letter" } },

        // Catalog zone (merchant's wares; offers with cost)
        { uid: "z-merchant", fragment_type: "group", group_type: "zone",
          member_ids: ["pc-offer-sword", "pc-offer-cloak"],
          layout_hints: { orientation: "grid", reveal: "all", zone_role: "catalog" },
          hints: { label_text: "The merchant" } },

        { uid: "pc-offer-sword", fragment_type: "piece",
          piece_id: "dragonslayer-sword", kind: "weapon", realized: false,
          zone_ref: "z-merchant",
          properties: { name: "Dragonslayer sword", weight: 3 },
          cost: [{ ledger_key: "coin", delta: -3, unit: "c" }],
          available: false,
          unavailable_reason: "You only have 2 coin.",
          hints: { label_text: "Dragonslayer sword",
                   description_text: "Said to slay dragons." } },

        { uid: "pc-offer-cloak", fragment_type: "piece",
          piece_id: "warm-cloak", kind: "armor", realized: false,
          zone_ref: "z-merchant",
          properties: { name: "Warm cloak", weight: 1 },
          cost: [{ ledger_key: "coin", delta: -1, unit: "c" }],
          available: true,
          hints: { label_text: "Warm cloak",
                   description_text: "Wards off the autumn chill." } },

        // Three weekly choices
        { uid: "ch-prince", fragment_type: "choice", edge_id: "e-receive-prince",
          text: "Receive the visiting prince.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "1", emphasis: "primary",
            stat_check: {
              label: "Audience",
              dice: "1d20", target: 10, modifier: 0,
              against: { piece_id: "player", property: "charm" },
              success_text: "10/20 chance (charm 10)",
            },
            source: "schedule.prince", source_kind: "schedule",
            contribution: "interaction" } },

        { uid: "ch-combat", fragment_type: "choice", edge_id: "e-train-combat",
          text: "Train at arms instead.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "2",
            // mood "martial" → +2 combat (full gain)
            cost_previews: [{ ledger_key: "skills.combat", delta: +2, unit: "xp" }],
            source: "instructor.swords", source_kind: "actor",
            contribution: "skill_gain" } },

        { uid: "ch-charm", fragment_type: "choice", edge_id: "e-train-charm",
          text: "Study courtly graces.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "3",
            // mood "martial" → +1 charm (HALVED by SituationalEffect)
            cost_previews: [{ ledger_key: "skills.charm", delta: +1, unit: "xp" }],
            source: "instructor.court", source_kind: "actor",
            contribution: "skill_gain" } },

        { uid: "ch-buy-sword", fragment_type: "choice", edge_id: "e-buy-sword",
          text: "Buy the dragonslayer sword (3 coin).",
          available: false,
          unavailable_reason: "You only have 2 coin.",
          blockers: [
            { code: "insufficient_coin",
              message: "Need 3 coin; have 2.",
              refs: ["coin"] },
          ],
          accepts: { kind: "pieces", min: 1, max: 1,
            constraints: { target_zone_ref: "z-merchant" } },
          ui_hints: { hotkey: "4",
            cost_previews: [{ ledger_key: "coin", delta: -3, unit: "c" }],
            source: "merchant", source_kind: "actor",
            contribution: "transfer" } },

        { uid: "ch-cmd", fragment_type: "choice", edge_id: "interpret_command",
          text: "Try a command.", available: true,
          accepts: { kind: "raw_command" },
          ui_hints: { hotkey: ">", reserved: "command_bar" } },
      ],
      metadata: { world: "coronate_the_regent" },
    },

    projected_state: {
      sections: [
        { section_id: "schedule", title: "Schedule", kind: "calendar",
          value: { value_type: "scalar", value: "Week 2 of 4" },
          hints: { icon: "calendar" } },

        { section_id: "mood", title: "Mood", kind: "mood",
          value: { value_type: "scalar", value: "martial" },
          hints: { icon: "sword", style_tags: ["mood-indicator"] } },

        { section_id: "stats", title: "Stats", kind: "stats",
          value: { value_type: "kv_list", items: [
            { key: "body",   value: 10, max: 20, hint: "bar" },
            { key: "mind",   value: 10, max: 20, hint: "bar" },
            { key: "spirit", value: 10, max: 20, hint: "bar" },
            { key: "combat", value: 12, max: 20, hint: "bar", emphasis: "ok" },
            { key: "magic",  value: 10, max: 20, hint: "bar" },
            { key: "charm",  value: 10, max: 20, hint: "bar" },
          ] } },

        { section_id: "wallet", title: "Wallet", kind: "wallet",
          value: { value_type: "kv_list", items: [
            { key: "coin",    value: 2, unit: "c" },
            { key: "stamina", value: 5, max: 5, hint: "bar", emphasis: "ok" },
          ] } },

        { section_id: "agenda", title: "Coming up", kind: "agenda",
          value: { value_type: "item_list", items: [
            { label: "Audience with prince", detail: "this week, charm check", tags: ["upcoming", "known"] },
            { label: "Dragon fight",         detail: "week 4, body check",     tags: ["scheduled"] },
            { label: "Coronation",           detail: "week 4 finale",          tags: ["scheduled"] },
          ] } },

        { section_id: "flags", title: "Reputation", kind: "tags",
          value: { value_type: "badges", items: ["studied", "young", "untested"] } },
      ],
    },

    // Post-roll envelope (after committing e-receive-prince)
    post_audience: {
      envelope: {
        cursor_id: "training-w2",
        step: 10,
        fragments: [
          { uid: "g-scene", fragment_type: "group", group_type: "scene",
            member_ids: ["c-room", "r-audience", "c-after", "ch-next"] },

          { uid: "c-room", fragment_type: "content", content_format: "md",
            content: "The prince watches you across the receiving hall. The guards lower their eyes. You step forward and bow." },

          { uid: "r-audience", fragment_type: "roll",
            label: "Prince's audience",
            kind: "dice",
            inputs: { dice: "1d20", rolled: [14], modifier: 0, total: 14, target: 10 },
            outcome: "success",
            narrative: "The prince leaves visibly charmed by your bearing. He will speak well of you at court.",
            against: { piece_id: "player", property: "charm" },
            ritual_hints: { skip_label: "Skip", duration_ms: 1400,
              auto_skip_after_seen: false, allow_replay: true } },

          { uid: "c-after", fragment_type: "content", content_format: "md",
            content: "Inventory: *impressed_prince*. The court's eyes are on you now." },

          { uid: "ch-next", fragment_type: "choice", edge_id: "e-week3",
            text: "Begin Week 3.",
            available: true,
            accepts: { kind: "pick" },
            ui_hints: { hotkey: "1", emphasis: "primary" } },
        ],
      },
      projected_state: { sections: [] },
    },
  };

  // ==========================================================================
  // ELEFANT_HUNT — at the watering hole, mid-expedition (Wham-inspired)
  // ==========================================================================
  // Demonstrates:
  //   - Board zone with layout_hints.graph (locations as sub-zones)
  //   - Hunters as pieces with hunting_value + status; expedition zone
  //   - Composite RollFragment(kind="custom") for hunt resolution
  //   - Supplies projected with hint:"bar"; score projected as scalar
  //   - encounter_check hint on movement choices entering hazards
  //   - journal-as-narrative transcript sample
  const elefantHunt = {
    envelope: {
      cursor_id: "hunt-watering-t8",
      step: 8,
      fragments: [
        { uid: "g-scene", fragment_type: "group", group_type: "scene",
          member_ids: [
            "c-prose",
            "z-board",
            "z-expedition",
            "r-hunt",
            "ch-clockwise", "ch-return", "ch-camp", "ch-cmd",
          ] },

        { uid: "c-prose", fragment_type: "content", content_format: "md",
          content: "**The watering hole.** Reeds. Rotting jacaranda. You spot a hippo and—no, a zebra and a vulture, circling. Zartan readies his rifle." },

        // Board zone (location sub-zones live inside)
        { uid: "z-board", fragment_type: "group", group_type: "zone",
          member_ids: ["pc-loc-port", "pc-loc-trail1", "pc-loc-river", "pc-loc-trail2",
                       "pc-loc-wh3", "pc-loc-albert", "pc-loc-graveyard"],
          layout_hints: {
            zone_role: "board",
            graph: {
              nodes: ["pc-loc-port", "pc-loc-trail1", "pc-loc-river", "pc-loc-trail2",
                      "pc-loc-wh3", "pc-loc-albert", "pc-loc-graveyard"],
              edges: [
                { uid: "e-port-t1",     a: "pc-loc-port",   b: "pc-loc-trail1", kind: "clockwise" },
                { uid: "e-t1-river",    a: "pc-loc-trail1", b: "pc-loc-river",  kind: "clockwise" },
                { uid: "e-river-t2",    a: "pc-loc-river",  b: "pc-loc-trail2", kind: "clockwise" },
                { uid: "e-t2-wh3",      a: "pc-loc-trail2", b: "pc-loc-wh3",    kind: "clockwise" },
                { uid: "e-wh3-albert",  a: "pc-loc-wh3",    b: "pc-loc-albert", kind: "clockwise" },
                { uid: "e-albert-grave", a: "pc-loc-albert", b: "pc-loc-graveyard", kind: "left" },
                { uid: "e-albert-port", a: "pc-loc-albert", b: "pc-loc-port",   kind: "return" },
              ],
            },
          },
          hints: { label_text: "The expedition" } },

        // Location pieces as nodes inside the board
        { uid: "pc-loc-port", fragment_type: "piece",
          piece_id: "loc-port", kind: "location", realized: true, zone_ref: "z-board",
          position: { x: 0, y: 1 },
          properties: { name: "Port Stanley", state: "visited", loc_kind: "port" },
          hints: { label_text: "Port Stanley", style_tags: ["scoring-location"] } },
        { uid: "pc-loc-trail1", fragment_type: "piece",
          piece_id: "loc-trail1", kind: "location", realized: true, zone_ref: "z-board",
          position: { x: 1, y: 0 },
          properties: { name: "Trail 1", state: "visited", loc_kind: "trail" },
          hints: { label_text: "Trail" } },
        { uid: "pc-loc-river", fragment_type: "piece",
          piece_id: "loc-river", kind: "location", realized: true, zone_ref: "z-board",
          position: { x: 2, y: 0 },
          properties: { name: "River crossing", state: "visited", loc_kind: "hazard" },
          hints: { label_text: "River crossing", style_tags: ["probabilistic-hazard"] } },
        { uid: "pc-loc-trail2", fragment_type: "piece",
          piece_id: "loc-trail2", kind: "location", realized: true, zone_ref: "z-board",
          position: { x: 3, y: 0 },
          properties: { name: "Trail 2", state: "visited", loc_kind: "trail" },
          hints: { label_text: "Trail" } },
        { uid: "pc-loc-wh3", fragment_type: "piece",
          piece_id: "loc-wh3", kind: "location", realized: true, zone_ref: "z-board",
          position: { x: 4, y: 1 },
          properties: { name: "Watering hole", state: "here", loc_kind: "hunting_ground", encounter_size: 3 },
          hints: { label_text: "Watering hole" } },
        { uid: "pc-loc-albert", fragment_type: "piece",
          piece_id: "loc-albert", kind: "location", realized: true, zone_ref: "z-board",
          position: { x: 4, y: 2 },
          properties: { name: "Albert Falls", state: "unexplored", loc_kind: "junction" },
          hints: { label_text: "Albert Falls" } },
        { uid: "pc-loc-graveyard", fragment_type: "piece",
          piece_id: "loc-graveyard", kind: "location", realized: true, zone_ref: "z-board",
          position: { x: 3, y: 3 },
          properties: { name: "Elefant graveyard", state: "unexplored", loc_kind: "graveyard" },
          hints: { label_text: "Elefant graveyard" } },

        // Expedition zone (hunters + captured animals + ivory)
        { uid: "z-expedition", fragment_type: "group", group_type: "zone",
          member_ids: ["pc-h-zartan", "pc-h-ned", "pc-h-skip", "pc-a-hippo", "pc-ivory-1"],
          layout_hints: { orientation: "row", reveal: "all", zone_role: "hand" },
          hints: { label_text: "Expedition" } },

        { uid: "pc-h-zartan", fragment_type: "piece",
          piece_id: "hunter-zartan", kind: "hunter", realized: true,
          zone_ref: "z-expedition",
          properties: { name: "Zartan", hunting_value: 4, status: "fit" },
          hints: { label_text: "Zartan (HV 4)" } },
        { uid: "pc-h-ned", fragment_type: "piece",
          piece_id: "hunter-ned", kind: "hunter", realized: true,
          zone_ref: "z-expedition",
          properties: { name: "Ned Net", hunting_value: 3, status: "fit" },
          hints: { label_text: "Ned Net (HV 3)" } },
        { uid: "pc-h-skip", fragment_type: "piece",
          piece_id: "hunter-skip", kind: "hunter", realized: true,
          zone_ref: "z-expedition",
          properties: { name: "Skip", hunting_value: 2, status: "fit" },
          hints: { label_text: "Skip (HV 2)" } },
        { uid: "pc-a-hippo", fragment_type: "piece",
          piece_id: "animal-hippo-1", kind: "animal", realized: true,
          zone_ref: "z-expedition",
          properties: { name: "hippo", point_value: 6, is_killer: true },
          hints: { label_text: "Hippo" } },
        { uid: "pc-ivory-1", fragment_type: "piece",
          piece_id: "ivory-1", kind: "ivory", realized: true,
          zone_ref: "z-expedition",
          properties: { name: "Ivory marker", value: null },
          hints: { label_text: "Ivory marker" } },

        // Composite hunt roll (just resolved this turn)
        { uid: "r-hunt", fragment_type: "roll",
          label: "Hunt at the watering hole",
          kind: "custom",
          inputs: {
            drawn: [
              { species: "hippo",   point_value: 6, is_killer: true },
              { species: "zebra",   point_value: 2, is_killer: false },
              { species: "vulture", point_value: 1, is_killer: false },
            ],
            assignments: [
              { hunter: "Zartan",  target: "hippo",   d6: 5, total: 9 },
              { hunter: "Ned Net", target: "zebra",   d6: 3, total: 5 },
              { hunter: "Skip",    target: "vulture", d6: 1, total: 2 },
            ],
            captures:   ["hippo"],
            escapes:    ["zebra", "vulture"],
            casualties: [],
          },
          outcome: "mixed_success",
          narrative: "Zartan brings the hippo down with a clean shot. Ned Net's zebra slips through the reeds. Skip rolls a one; the vulture takes wing and is gone.",
          ritual_hints: { skip_label: "Skip the hunt", duration_ms: 2400,
            auto_skip_after_seen: false, allow_replay: true } },

        // Movement choices (with encounter_check hints on hazardous exits)
        { uid: "ch-clockwise", fragment_type: "choice", edge_id: "e-wh3-albert",
          text: "Continue clockwise to Albert Falls.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "1", emphasis: "primary",
            encounter_check: {
              label: "Albert Falls (junction)",
              risk_text: "Forces a one-turn rest at the cliff.",
              consequence_text: "Choose left or right next turn.",
            },
            source: "location.albert", source_kind: "location",
            contribution: "movement",
            cost_previews: [{ ledger_key: "supplies", delta: -1, unit: "day" }] } },

        { uid: "ch-return", fragment_type: "choice", edge_id: "e-return-port",
          text: "Turn back toward Port Stanley.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "2", emphasis: "subtle",
            encounter_check: {
              label: "River crossing (re-cross)",
              risk_text: "1-in-6: lose an animal to the current.",
              predicate_ref: "river_loss_d6_eq_6",
            },
            source: "location.river", source_kind: "location",
            contribution: "movement",
            cost_previews: [{ ledger_key: "supplies", delta: -2, unit: "days" }] } },

        { uid: "ch-camp", fragment_type: "choice", edge_id: "e-camp",
          text: "Camp at the watering hole.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "3",
            source: "location.watering", source_kind: "location",
            contribution: "wait",
            cost_previews: [{ ledger_key: "supplies", delta: -1, unit: "day" }] } },

        { uid: "ch-cmd", fragment_type: "choice", edge_id: "interpret_command",
          text: "Try a command.", available: true,
          accepts: { kind: "raw_command" },
          ui_hints: { hotkey: ">", reserved: "command_bar" } },
      ],
      metadata: {
        world: "elefant_hunt",
        info_affordances: [
          { kind: "map",        label: "Map",        shortcuts: ["m", "map"],
            query: { type: "map", format: "graph" } },
          { kind: "expedition", label: "Party",      shortcuts: ["p"],
            query: { kinds: ["expedition"] } },
          { kind: "score",      label: "Score",      shortcuts: ["s"],
            query: { kinds: ["score"] } },
          { kind: "help",       label: "Help",       shortcuts: ["?"],
            query: null },
        ],
        info_state: {
          version: 8,
          dirty_kinds: ["expedition", "score"],
          available_kinds: ["map", "expedition", "score", "help"],
        },
      },
    },

    projected_state: {
      sections: [
        { section_id: "score", title: "Score", kind: "score",
          value: { value_type: "scalar", value: 21 } },

        { section_id: "supplies", title: "Supplies", kind: "resource",
          value: { value_type: "kv_list", items: [
            { key: "days", value: 4, max: 8, unit: "days", hint: "bar", emphasis: "warn" },
          ] } },

        { section_id: "expedition", title: "Expedition", kind: "roster",
          value: { value_type: "item_list", items: [
            { label: "Zartan",  detail: "HV 4 · fit",     tags: ["hunter"] },
            { label: "Ned Net", detail: "HV 3 · fit",     tags: ["hunter"] },
            { label: "Skip",    detail: "HV 2 · fit",     tags: ["hunter"] },
            { label: "Hippo",   detail: "6 pts · killer", tags: ["animal", "captured"] },
            { label: "Ivory",   detail: "to be appraised", tags: ["asset"] },
          ] } },

        { section_id: "location", title: "Here", kind: "location",
          value: { value_type: "item_list", items: [
            { label: "Watering hole",    detail: "hunting ground · encounter draws 3", tags: ["place"] },
            { label: "Albert Falls",     detail: "north, junction",                    tags: ["exit"] },
            { label: "Trail 2 (return)", detail: "back toward River crossing",         tags: ["exit"] },
          ] } },
      ],
    },

    // Journal-as-story validation transcript (§0.8) — a real CLI playback
    // of a complete expedition arc. Used in the journal-as-story section
    // to demonstrate that envelope streams produce legible narrative
    // without authored prose beyond per-location flavor.
    journal_transcript: [
      "Port Stanley. The harbormaster greets you with a ledger. You",
      "hire two hunters and load four days of supplies.",
      "",
      "  1) Set off into the interior.",
      "  > 1",
      "",
      "You move deeper into the interior. Camp. Consumed 1 supply.",
      "",
      "  1) Continue to the river.",
      "  > 1",
      "",
      "The river runs fast and brown. You wade in, supplies held high.",
      "  [River crossing]  rolled 6 / target 6",
      "  A zebra is lost to the current.",
      "",
      "  1) Continue along the trail.",
      "  > 1",
      "",
      "You move deeper still. Camp. Consumed 1 supply.",
      "",
      "  1) Approach the watering hole.",
      "  > 1",
      "",
      "You spot a hippo and two zebras — no, a zebra and a vulture,",
      "circling. Zartan brings the hippo down with a clean shot.",
      "Ned Net's zebra slips through the reeds. Skip rolls a one;",
      "the vulture takes wing and is gone.",
      "",
      "  [Hunt at the watering hole]",
      "    captures: hippo",
      "    escapes:  zebra, vulture",
      "",
      "  1) Continue clockwise.",
      "  2) Turn back to Port Stanley.",
      "  > 2",
      "",
      "[long return journey, abbreviated]",
      "",
      "Port Stanley. The harbormaster greets you with a ledger.",
      "",
      "  [Ivory appraisal]  rolled 5 + 4 + 6 = 15",
      "  The ivory weighs out at 15 points.",
      "",
      "Expedition returns to Port Stanley. Score: 21 points.",
      "",
      "  1) Resupply and depart again (consumes 4 stamina).",
      "  2) End the expedition.",
    ],
  };

  return { credentials, training, elefant_hunt: elefantHunt };
})();
