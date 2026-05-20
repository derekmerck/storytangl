// v12-fixtures.js — consolidated fixtures for the v1.2 wireframe demo.
//
// Every fixture is a single { envelope, projected_state } pair shaped against
// STORYTANGL_WIDGET_VOCAB v1.1, with the v1.2 conventions for sandbox + carwars
// extensions layered on top. The shells/widgets in this doc consume these
// directly — no synthetic adapter layer.
//
// Fixtures included:
//   crossroads — Tier S baseline (prose, dialog, choices, kv, projected sections)
//   garage     — Tier P2 piece/zone/slot/catalog + Tier P3 stat_check/drag
//   gravel     — Tier P2 RollFragment ritual + InterpretationFragment
//   manor      — Tier P2 sandbox: info affordances, world_time, agenda, map,
//                location/presence, command bar, choice provenance

window.V12_FIXTURES = (function () {

  // ===========================================================================
  // 1) CROSSROADS — the canonical baseline (Tier S, drives the triptych)
  // ===========================================================================

  const crossroads = {
    envelope: {
      cursor_id: "b6e0f3a4-1d5f-4b62-9e1e-aa8101b2d7f1",
      step: 47,
      fragments: [
        // scene group ties the turn together
        { uid: "g-scene",     fragment_type: "group", group_type: "scene",
          member_ids: [
            "m-cover", "c-open", "m-narr",
            "g-dlg", "kv-scene",
            "ch-bargain", "ch-refuse", "ch-haggle", "ch-sneak", "ch-cmd",
          ] },

        { uid: "m-cover", fragment_type: "media",
          content: "assets/crossroads_inn_night.jpg",
          content_format: "url",
          media_role: "cover_im",
          scope: "world",
          staging_hints: { media_shape: "banner", media_position: "top",
                           media_size: "large", media_transition: "fade_in" } },

        { uid: "c-open", fragment_type: "content", content_format: "md",
          content: "Rain drums on the thatch. Inside the Crossroads Inn the air is smoke and peat. A man in a rust-colored cloak beckons from the corner booth, a folded vellum square weighted under his cup.",
          hints: { style_tags: ["narrative", "establishing"] } },

        { uid: "m-narr", fragment_type: "media",
          content: "assets/stranger_booth.jpg",
          content_format: "url",
          media_role: "narrative_im",
          staging_hints: { media_shape: "portrait", media_position: "right", media_size: "medium" } },

        { uid: "g-dlg", fragment_type: "group", group_type: "dialog",
          member_ids: ["att-1", "m-av", "att-2", "m-dlg"] },

        { uid: "att-1", fragment_type: "attributed",
          who: "Stranger", how: "low, confidential", media: "speech",
          content: "They say you're headed north. I've got something the garrison would pay for and never use." },

        { uid: "m-av", fragment_type: "media",
          content: "assets/stranger_avatar.jpg", content_format: "url",
          media_role: "avatar_im",
          staging_hints: { media_shape: "avatar", media_size: "small" } },

        { uid: "att-2", fragment_type: "attributed",
          who: "Stranger", how: "smiling without teeth", media: "speech",
          content: "Forty silver. You look at it, you buy it. No haggle." },

        // pending generated media — placeholder until a later control.update arrives
        { uid: "m-dlg", fragment_type: "media",
          content: "gen:vellum_map_close_up", content_format: "rit",
          media_role: "dialog_im",
          staging_hints: { media_shape: "square", media_size: "small" },
          generation_status: "pending" },

        // in-stream kv — scene-bound status, NOT a projected section
        { uid: "kv-scene", fragment_type: "kv",
          content: [
            { key: "time",       value: "late evening" },
            { key: "coin",       value: 63, unit: "s" },
            { key: "companions", value: "Bram, Elen" },
            { key: "weather",    value: "rain" },
          ],
          hints: { style_tags: ["status-inline"] } },

        // CHOICES — exercises pick / quantity / locked / raw_command
        { uid: "ch-bargain", fragment_type: "choice",
          edge_id: "e-cr-bargain",
          text: "Pay the forty silver.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "1", icon: "coin", emphasis: "primary",
            cost_previews: [{ ledger_key: "purse", delta: -40, unit: "silver" }] } },

        { uid: "ch-refuse", fragment_type: "choice",
          edge_id: "e-cr-refuse",
          text: "Tell him to keep his paper.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "2" } },

        { uid: "ch-haggle", fragment_type: "choice",
          edge_id: "e-cr-haggle",
          text: "Haggle.",
          available: true,
          accepts: { kind: "quantity",
            min: 1, max: 63, step: 1, unit: "silver",
            ledger_ref: "purse",
            placeholder: "silver to offer" },
          ui_hints: { hotkey: "3", icon: "chat" } },

        { uid: "ch-sneak", fragment_type: "choice",
          edge_id: "e-cr-steal",
          text: "Lift the map while he drinks.",
          available: false,
          unavailable_reason: "Requires Sleight of Hand ≥ 2",
          blockers: [
            { code: "skill_too_low",
              message: "Sleight of Hand 1, need 2.",
              refs: ["pc-you"] },
            { code: "watched",
              message: "Elen is watching.",
              refs: ["pc-elen"] },
          ],
          ui_hints: { hotkey: "4", icon: "hand" } },

        // reserved interpret_command edge — the command bar wraps this choice
        { uid: "ch-cmd", fragment_type: "choice",
          edge_id: "interpret_command",
          text: "Try a command.",
          available: true,
          accepts: { kind: "raw_command" },
          ui_hints: { hotkey: ">", reserved: "command_bar" } },

        // example user_event — clients toast or stash
        { uid: "ue-1", fragment_type: "user_event",
          event_type: "achievement_progress",
          content: { id: "met_10_strangers", progress: "7/10" } },

        // example control update — re-render a prior content UID in place
        { uid: "ctl-1", fragment_type: "update",
          ref_type: "content", ref_id: "glossary:vellum",
          payload: { gloss: "parchment made from calfskin; expensive." } },
      ],
      last_redirect: null,
      redirect_trace: [],
      metadata: {
        world: "crossroads", chapter: "ch01",
        grammar: {
          verbs: [
            { verb: "pay", aliases: [], frames: ["pay {n} {noun}"] },
            { verb: "haggle", aliases: [], frames: ["haggle"] },
            { verb: "leave", aliases: ["refuse"], frames: ["leave", "refuse"] },
          ],
          nouns: [
            { noun: "silver", aliases: ["coin"], piece_ids: [] },
            { noun: "map",    aliases: ["paper", "vellum"], piece_ids: [] },
          ],
          placeholder: "try: pay 40 silver",
          examples: ["pay 40 silver", "haggle", "leave"],
        },
      },
    },

    projected_state: {
      sections: [
        { section_id: "wounds", title: "Wounds", kind: "status",
          value: { value_type: "scalar", value: "Sound" },
          hints: { icon: "heart" } },

        { section_id: "purse", title: "Purse", kind: "wallet",
          value: { value_type: "kv_list", items: [
            { key: "silver", value: 63, unit: "s" },
            { key: "copper", value: 11, unit: "c" },
            { key: "favors", value: 1, delta: 1 },
          ] } },

        { section_id: "satchel", title: "Satchel", kind: "inventory",
          value: { value_type: "item_list", items: [
            { label: "Hooded lantern", detail: "half-oil",        tags: ["light"] },
            { label: "Letter, sealed", detail: "for Captain Ros", tags: ["quest"] },
            { label: "Elen's knife",   detail: "balanced",        tags: ["weapon","borrowed"] },
          ] } },

        { section_id: "party", title: "Party", kind: "roster",
          value: { value_type: "table",
            columns: ["name", "role", "mood"],
            rows: [
              ["Bram", "soldier", "surly"],
              ["Elen", "scout",   "watchful"],
            ] } },

        { section_id: "tags", title: "Conditions", kind: "tags",
          value: { value_type: "badges", items: ["rain-soaked", "hungry", "hunted"] } },
      ],
    },
  };

  // ===========================================================================
  // 2) GARAGE — Tier P2 pieces/zones/slots/catalog + Tier P3 stat_check/drag
  //    Patterns: equip-from-loose, buy-from-catalog, plural cost_previews
  // ===========================================================================

  const garage = {
    envelope: {
      cursor_id: "garage-fixture",
      step: 121,
      fragments: [
        { uid: "g-scene", fragment_type: "group", group_type: "scene",
          member_ids: ["c-prose",
            "z-front", "z-turret", "z-back",
            "z-loose", "z-catalog",
            "ch-mount", "ch-unmount-front", "ch-buy", "ch-leave", "ch-cmd"] },

        { uid: "c-prose", fragment_type: "content", content_format: "md",
          content: "Murph's, end of the strip. Your interceptor sits on the lift, hood up, oil pan dripping. *\"What'll it be today?\"*" },

        // ---- Vehicle slots (group_type=zone, zone_role=slot, with capacity) --
        { uid: "z-front", fragment_type: "group", group_type: "zone",
          member_ids: ["pc-rocket"],
          constraints: {
            accepts_kind: ["weapon"],
            capacity: [
              { kind: "count",  max: 1, unit: "weapon" },
              { kind: "weight", max: 3, unit: "stone", sum_property: "weight",
                ledger_key: "vehicle.front.weight" },
            ],
          },
          layout_hints: { orientation: "stack", reveal: "all",
            silhouette: { region: "front" },
            zone_role: "slot" },
          hints: { label_text: "front mount" } },

        { uid: "z-turret", fragment_type: "group", group_type: "zone",
          member_ids: [],
          constraints: {
            accepts_kind: ["weapon"],
            capacity: [
              { kind: "count",  max: 1, unit: "weapon" },
              { kind: "weight", max: 4, unit: "stone", sum_property: "weight",
                ledger_key: "vehicle.turret.weight" },
            ],
          },
          layout_hints: { orientation: "stack",
            silhouette: { region: "top" },
            zone_role: "slot" },
          hints: { label_text: "turret" } },

        { uid: "z-back", fragment_type: "group", group_type: "zone",
          member_ids: [],
          constraints: {
            accepts_kind: ["weapon"],
            capacity: [
              { kind: "count",  max: 1, unit: "weapon" },
              { kind: "weight", max: 2, unit: "stone", sum_property: "weight",
                ledger_key: "vehicle.back.weight" },
            ],
          },
          layout_hints: { silhouette: { region: "back" }, zone_role: "slot" },
          hints: { label_text: "back mount" } },

        // ---- Loose parts (zone_role=field, owner=you) ------------------------
        { uid: "z-loose", fragment_type: "group", group_type: "zone",
          member_ids: ["pc-spare-armor", "pc-spare-tire"],
          layout_hints: { orientation: "row", zone_role: "field" },
          hints: { label_text: "parts on hand" } },

        // ---- Catalog (zone_role=catalog, members are realized=false offers) -
        { uid: "z-catalog", fragment_type: "group", group_type: "zone",
          member_ids: ["pc-flame", "pc-vulcan", "pc-armor", "pc-rl2"],
          layout_hints: { orientation: "grid", reveal: "all", zone_role: "catalog" },
          hints: { label_text: "Murph's wares" } },

        // ---- Realized pieces -------------------------------------------------
        // owner is the cursor whose channel "owns" the piece (§7.1).
        // For solo play (one cursor) it identifies the player; in multi-cursor
        // sessions visibility="owner_only" is interpreted against it.
        { uid: "pc-rocket", fragment_type: "piece",
          piece_id: "pc-rocket", kind: "weapon", realized: true,
          zone_ref: "z-front", owner: "player_a",
          properties: { name: "Rocket Launcher", weight: 3, power_draw: 1, ammo: 4 },
          hints: { label_text: "Rocket Launcher" } },

        { uid: "pc-spare-armor", fragment_type: "piece",
          piece_id: "pc-spare-armor", kind: "armor", realized: true,
          zone_ref: "z-loose", owner: "player_a",
          properties: { name: "Spare armor plate", weight: 2, armor: 4 },
          hints: { label_text: "Spare armor plate" } },

        { uid: "pc-spare-tire", fragment_type: "piece",
          piece_id: "pc-spare-tire", kind: "item", realized: true,
          zone_ref: "z-loose", owner: "player_a",
          properties: { name: "Spare tire", weight: 1 },
          hints: { label_text: "Spare tire" } },

        // ---- Offers (realized=false) -----------------------------------------
        // Catalog offers have no owner — the merchant's stock is shared until
        // commit mints a realized piece into the player's inventory zone.
        { uid: "pc-flame", fragment_type: "piece",
          piece_id: "flamethrower", kind: "weapon", realized: false,
          zone_ref: "z-catalog",
          properties: { name: "Flamethrower", weight: 3, power_draw: 1, ammo: 4 },
          cost: [{ ledger_key: "wallet", delta: -400, unit: "credit" }],
          available: true,
          hints: { label_text: "Flamethrower",
                   description_text: "Splash damage. Burns 1 fuel per shot." } },

        { uid: "pc-vulcan", fragment_type: "piece",
          piece_id: "vulcan", kind: "weapon", realized: false,
          zone_ref: "z-catalog",
          properties: { name: "Vulcan gun", weight: 2, power_draw: 1, ammo: 10 },
          cost: [{ ledger_key: "wallet", delta: -300, unit: "credit" }],
          available: true,
          hints: { label_text: "Vulcan gun",
                   description_text: "Lighter. Less punch. 10 ammo." } },

        { uid: "pc-armor", fragment_type: "piece",
          piece_id: "armor_plate", kind: "armor", realized: false,
          zone_ref: "z-catalog",
          properties: { name: "Armor plate", weight: 2, armor: 4 },
          cost: [{ ledger_key: "wallet", delta: -200, unit: "credit" }],
          available: true,
          hints: { label_text: "Armor plate",
                   description_text: "+4 armor on a fresh face." } },

        { uid: "pc-rl2", fragment_type: "piece",
          piece_id: "rl_mk2", kind: "weapon", realized: false,
          zone_ref: "z-catalog",
          properties: { name: "Rocket Launcher Mk-II", weight: 3, ammo: 6 },
          cost: [{ ledger_key: "wallet", delta: -650, unit: "credit" }],
          available: false,
          unavailable_reason: "Out of stock until next session.",
          hints: { label_text: "Rocket Launcher Mk-II" } },

        // ---- Choices ---------------------------------------------------------
        { uid: "ch-mount", fragment_type: "choice", edge_id: "e-mount",
          text: "Mount a part.",
          available: true,
          accepts: { kind: "place",
            source_zone_ref: "z-loose",
            predicate_ref: "is_open_weapon_slot" },
          ui_hints: { hotkey: "1",
            drag: { enabled: true,
              grab_zone_ref: "z-loose",
              drop_zone_refs: ["z-front", "z-turret", "z-back"],
              preview: "capacity",
              fallback_label: "or click each step" },
            source: "vehicle", source_kind: "fixture", contribution: "transfer" } },

        { uid: "ch-unmount-front", fragment_type: "choice", edge_id: "e-unmount-front",
          text: "Remove front weapon.",
          available: true,
          accepts: { kind: "pieces", min: 1, max: 1,
            constraints: { target_zone_ref: "z-front" } },
          ui_hints: { hotkey: "2", source: "vehicle", source_kind: "fixture",
            contribution: "transfer" } },

        { uid: "ch-buy", fragment_type: "choice", edge_id: "e-buy",
          text: "Buy from Murph's.",
          available: true,
          accepts: { kind: "pieces", min: 0, max: 5,
            constraints: { target_zone_ref: "z-catalog",
                           target_kind: ["weapon", "armor"] } },
          ui_hints: { hotkey: "3",
            source: "merchant.murph", source_kind: "actor",
            contribution: "transfer" } },

        { uid: "ch-leave", fragment_type: "choice", edge_id: "e-leave",
          text: "Hit the road.",
          available: true,
          accepts: { kind: "pick" },
          ui_hints: { hotkey: "4",
            source: "location.murphs", source_kind: "location",
            contribution: "movement",
            cost_previews: [
              { ledger_key: "wallet",  delta: 0,  unit: "cr" },
              { ledger_key: "periods", delta: -1, unit: "period" },
            ] } },

        { uid: "ch-cmd", fragment_type: "choice", edge_id: "interpret_command",
          text: "Try a command.",
          available: true,
          accepts: { kind: "raw_command" },
          ui_hints: { hotkey: ">", reserved: "command_bar" } },
      ],
      metadata: { world: "carwars", scene: "murphs_garage" },
    },

    projected_state: {
      sections: [
        { section_id: "wallet", title: "Wallet", kind: "wallet",
          value: { value_type: "kv_list", items: [
            { key: "credits", value: 1240, unit: "cr" },
          ] } },

        { section_id: "vehicle_load", title: "Vehicle load", kind: "score",
          value: { value_type: "kv_list", items: [
            { key: "total",  value: 4, max: 12, unit: "stone", hint: "bar", emphasis: "warn" },
            { key: "front",  value: 3, max: 3,  unit: "stone", hint: "bar", emphasis: "warn" },
            { key: "turret", value: 0, max: 4,  unit: "stone", hint: "bar" },
            { key: "back",   value: 0, max: 2,  unit: "stone", hint: "bar" },
          ] } },

        { section_id: "crew", title: "Crew", kind: "roster",
          value: { value_type: "kv_list", items: [
            { key: "driver",  value: "you · gunnery 7 · drive 9" },
            { key: "morale",  value: "shaken", emphasis: "warn" },
          ] } },
      ],
    },
  };

  // ===========================================================================
  // 3) GRAVEL — RollFragment ritual + InterpretationFragment patterns
  // ===========================================================================

  const gravel = {
    pre: {
      envelope: {
        cursor_id: "gravel-pre",
        step: 160,
        fragments: [
          { uid: "g-scene", fragment_type: "group", group_type: "scene",
            member_ids: ["c-prose", "ch-drive", "ch-skid", "ch-cmd"] },

          { uid: "c-prose", fragment_type: "content", content_format: "md",
            content: "The road forks at speed. Gravel under the tires; the interceptor wants to slide. **Driving check incoming.**" },

          { uid: "pc-you", fragment_type: "piece",
            piece_id: "you", kind: "actor", realized: true,
            properties: { name: "You", driving: 9, gunnery: 7 } },

          { uid: "ch-drive", fragment_type: "choice", edge_id: "e-drive",
            text: "Hold the line.",
            available: true,
            accepts: { kind: "pick" },
            ui_hints: { hotkey: "1",
              stat_check: {
                label: "Driving check",
                dice: "2d6", target: 12, modifier: 0,
                against: { piece_id: "you", property: "driving" },
                success_text: "5/12 chance",
              } } },

          { uid: "ch-skid", fragment_type: "choice", edge_id: "e-skid",
            text: "Pull the brake. Eat the skid.",
            available: true,
            accepts: { kind: "pick" },
            ui_hints: { hotkey: "2",
              cost_previews: [
                { ledger_key: "vehicle.armor.front", delta: -1, unit: "pt" },
              ] } },

          { uid: "ch-cmd", fragment_type: "choice", edge_id: "interpret_command",
            text: "Try a command.", available: true,
            accepts: { kind: "raw_command" },
            ui_hints: { hotkey: ">", reserved: "command_bar" } },
        ],
      },
      projected_state: { sections: [] },
    },

    post_fail: {
      envelope: {
        cursor_id: "gravel-post",
        step: 161,
        fragments: [
          { uid: "g-scene", fragment_type: "group", group_type: "scene",
            member_ids: ["r-drive", "c-after", "ch-continue", "ch-cmd"] },

          { uid: "r-drive", fragment_type: "roll",
            label: "Driving check",
            kind: "dice",
            inputs: { dice: "2d6", rolled: [4, 5], modifier: 0, total: 9, target: 12 },
            outcome: "fail",
            against: { piece_id: "you", property: "driving" },
            narrative: "The wheel jerks under you and the interceptor goes sideways. Smoke. The world tilts.",
            ritual_hints: { skip_label: "Skip", duration_ms: 1800,
              auto_skip_after_seen: false, allow_replay: true } },

          { uid: "c-after", fragment_type: "content", content_format: "md",
            content: "You skid into the shoulder. Front armor gouged. *Crew morale: rattled.*" },

          { uid: "ch-continue", fragment_type: "choice", edge_id: "e-continue",
            text: "Get out and check the damage.",
            available: true,
            accepts: { kind: "pick" },
            ui_hints: { hotkey: "1" } },

          { uid: "ch-cmd", fragment_type: "choice", edge_id: "interpret_command",
            text: "Try a command.", available: true,
            accepts: { kind: "raw_command" },
            ui_hints: { hotkey: ">", reserved: "command_bar" } },
        ],
      },
      projected_state: { sections: [] },
    },

    post_crit: {
      envelope: {
        cursor_id: "gravel-post",
        step: 161,
        fragments: [
          { uid: "g-scene", fragment_type: "group", group_type: "scene",
            member_ids: ["r-drive", "c-after"] },

          { uid: "r-drive", fragment_type: "roll",
            label: "Driving check",
            kind: "dice",
            inputs: { dice: "2d6", rolled: [6, 6], modifier: 0, total: 12, target: 12 },
            outcome: "crit_success",
            against: { piece_id: "you", property: "driving" },
            narrative: "The interceptor holds. Tires bite. You shave the apex by an inch." },

          { uid: "c-after", fragment_type: "content", content_format: "md",
            content: "Open road ahead. The radio crackles back to life." },
        ],
      },
      projected_state: { sections: [] },
    },

    // Interpretation transcript samples — what the parser returns on
    // ambiguous / unknown / blocked inputs.
    interp_samples: [
      { uid: "i-1", fragment_type: "interpretation",
        result: "ambiguous",
        text: "take key",
        message: "Which key — brass or iron?",
        candidates: ["e-take#brass_key", "e-take#iron_key"] },
      { uid: "i-2", fragment_type: "interpretation",
        result: "blocked",
        text: "climb to attic",
        message: "The hatch is bolted from above.",
        blocked_reason: "Locked — no obvious key.",
        hint: "Find another way up." },
      { uid: "i-3", fragment_type: "interpretation",
        result: "unknown_verb",
        text: "fly away",
        message: "Nothing here takes flight." },
      { uid: "i-4", fragment_type: "interpretation",
        result: "validation_failed",
        text: "pay 200 silver",
        message: "You only have 63 silver." },
    ],
  };

  // ===========================================================================
  // 4) MANOR — sandbox scenario (Tier P2 + new v1.2 conventions)
  //    Demonstrates: info affordances, world_time section, agenda section,
  //                  location/presence, map zone with goto links,
  //                  choice provenance (ui_hints.source / contribution),
  //                  per-turn metadata.info_state.dirty_kinds.
  // ===========================================================================

  const manor = (() => {
    // Locations are pieces of kind="location" in the map zone.
    const locations = [
      { piece_id: "loc-bedroom", name: "bedroom",  state: "here",       period_cost: 0, x: 1, y: 1 },
      { piece_id: "loc-hall",    name: "hall",     state: "visited",    period_cost: 1, x: 2, y: 1 },
      { piece_id: "loc-yard",    name: "yard",     state: "visited",    period_cost: 2, x: 3, y: 1 },
      { piece_id: "loc-cellar",  name: "cellar",   state: "unexplored", period_cost: 2, x: 1, y: 2 },
      { piece_id: "loc-attic",   name: "attic",    state: "locked",     period_cost: 3, x: 2, y: 2 },
    ];
    const locPieces = locations.map(l => ({
      uid: "pc-" + l.piece_id.slice(4),
      fragment_type: "piece",
      piece_id: l.piece_id,
      kind: "location",
      realized: true,
      zone_ref: "z-map",
      // §7.1 position — interpreted against the parent zone's layout_hints.
      // The map zone uses free-form spatial layout, so {x, y}.
      position: { x: l.x, y: l.y },
      properties: { name: l.name, state: l.state, period_cost: l.period_cost },
      hints: { label_text: l.name },
    }));

    return {
      envelope: {
        cursor_id: "manor-bedroom-t22",
        step: 22,
        fragments: [
          { uid: "g-scene", fragment_type: "group", group_type: "scene",
            member_ids: [
              "c-prose",
              "z-room", "z-inv", "z-map",
              "ch-look", "ch-walk-hall", "ch-walk-cellar",
              "ch-take", "ch-open-mailbox", "ch-give", "ch-name",
              "ch-wait", "ch-cmd",
            ] },

          // recent transcript (echo + an earlier blocked interpretation)
          { uid: "echo-1", fragment_type: "content", content_format: "md",
            content: "_> walk to bedroom_",
            hints: { style_tags: ["echo"] } },
          { uid: "echo-2", fragment_type: "content", content_format: "md",
            content: "You step through the dripping doorway. The bedroom is colder than the hall." },
          { uid: "i-prev", fragment_type: "interpretation",
            result: "blocked",
            text: "climb to attic",
            message: "The hatch is bolted from above.",
            blocked_reason: "Locked — no obvious key." },

          { uid: "c-prose", fragment_type: "content", content_format: "md",
            content: "**The bedroom.** Damp curtains. A brass lamp on the writing-desk. A small mailbox bolted by the door, closed. A water-stained painting above the bed. The guard is at his post in the hall, just through the doorway." },

          // ---- Room zone (visible things in this location) -----------------
          { uid: "z-room", fragment_type: "group", group_type: "zone",
            member_ids: ["pc-lamp", "pc-mailbox", "pc-painting", "pc-guard"],
            layout_hints: { orientation: "row", reveal: "all", zone_role: "field" },
            hints: { label_text: "here" } },

          // ---- Inventory zone (carried) ------------------------------------
          { uid: "z-inv", fragment_type: "group", group_type: "zone",
            member_ids: ["pc-brass-key", "pc-iron-key", "pc-coin-purse"],
            layout_hints: { orientation: "row", reveal: "all", zone_role: "hand" },
            hints: { label_text: "carrying" } },

          // ---- Map zone (locations as pieces) ------------------------------
          // §7.2 GraphLayout.edges are first-class addressable adjacencies
          // — each carries a uid; PlaceAccepts.edge_ref points at them.
          { uid: "z-map", fragment_type: "group", group_type: "zone",
            member_ids: locPieces.map(p => p.uid),
            layout_hints: {
              zone_role: "field",
              graph: {
                nodes: locPieces.map(p => p.uid),
                edges: [
                  { uid: "edge-bedroom-hall",    a: "loc-bedroom", b: "loc-hall",   label: "hall door" },
                  { uid: "edge-hall-yard",      a: "loc-hall",    b: "loc-yard",   label: "yard door" },
                  { uid: "edge-bedroom-cellar", a: "loc-bedroom", b: "loc-cellar", label: "cellar stair" },
                  { uid: "edge-hall-attic",     a: "loc-hall",    b: "loc-attic",  label: "attic hatch",
                    properties: { locked: true } },
                ],
              },
            },
            hints: { label_text: "the manor" } },

          // ---- Pieces (room) ----------------------------------------------
          { uid: "pc-lamp", fragment_type: "piece",
            piece_id: "lamp", kind: "item", realized: true, zone_ref: "z-room",
            properties: { name: "brass lamp", weight: 1, takeable: true },
            hints: { label_text: "brass lamp" } },
          { uid: "pc-mailbox", fragment_type: "piece",
            piece_id: "mailbox", kind: "fixture", realized: true, zone_ref: "z-room",
            properties: { name: "small mailbox", state: "closed", fixed: true },
            hints: { label_text: "small mailbox" } },
          { uid: "pc-painting", fragment_type: "piece",
            piece_id: "painting", kind: "fixture", realized: true, zone_ref: "z-room",
            properties: { name: "framed painting", fixed: true },
            hints: { label_text: "framed painting" } },
          { uid: "pc-guard", fragment_type: "piece",
            piece_id: "guard", kind: "actor", realized: true,
            zone_ref: "z-room",
            properties: { name: "the guard", current_location_ref: "loc-hall" },
            hints: { label_text: "the guard" } },

          // ---- Pieces (inventory) -----------------------------------------
          { uid: "pc-brass-key", fragment_type: "piece",
            piece_id: "brass_key", kind: "item", realized: true,
            zone_ref: "z-inv", owner: "player_a",
            properties: { name: "brass key" }, hints: { label_text: "brass key" } },
          { uid: "pc-iron-key", fragment_type: "piece",
            piece_id: "iron_key", kind: "item", realized: true,
            zone_ref: "z-inv", owner: "player_a",
            properties: { name: "iron key" }, hints: { label_text: "iron key" } },
          { uid: "pc-coin-purse", fragment_type: "piece",
            piece_id: "coin_purse", kind: "counter", realized: true,
            zone_ref: "z-inv", owner: "player_a",
            properties: { name: "coin purse", unit: "coin", count: 7 },
            hints: { label_text: "coin purse · 7" } },

          // ---- Pieces (locations) -----------------------------------------
          ...locPieces,

          // ---- Choices (with provenance hints on every one) ---------------
          { uid: "ch-look", fragment_type: "choice", edge_id: "e-look",
            text: "Look around.",
            available: true, accepts: { kind: "pick" },
            ui_hints: { hotkey: "1",
              source: "location.bedroom", source_kind: "location",
              contribution: "interaction" } },

          { uid: "ch-walk-hall", fragment_type: "choice", edge_id: "e-walk#loc-hall",
            text: "Walk to the hall.",
            available: true, accepts: { kind: "pick" },
            ui_hints: { hotkey: "2",
              source: "location.hall", source_kind: "location",
              contribution: "movement", direction: "north",
              cost_previews: [{ ledger_key: "periods", delta: -1, unit: "period" }] } },

          { uid: "ch-walk-cellar", fragment_type: "choice", edge_id: "e-walk#loc-cellar",
            text: "Descend to the cellar.",
            available: true, accepts: { kind: "pick" },
            ui_hints: { hotkey: "3",
              source: "location.cellar", source_kind: "location",
              contribution: "movement", direction: "down",
              cost_previews: [{ ledger_key: "periods", delta: -2, unit: "periods" }] } },

          { uid: "ch-take", fragment_type: "choice", edge_id: "e-take",
            text: "Take something.",
            available: true,
            accepts: { kind: "pieces", min: 1, max: 1,
              constraints: { target_zone_ref: "z-room",
                             predicate_ref: "is_takeable" } },
            ui_hints: { hotkey: "4",
              source: "asset", source_kind: "asset",
              contribution: "transfer" } },

          { uid: "ch-open-mailbox", fragment_type: "choice", edge_id: "e-open#mailbox",
            text: "Open the mailbox.",
            available: true, accepts: { kind: "pick" },
            ui_hints: { hotkey: "5",
              source: "fixture.mailbox", source_kind: "fixture",
              contribution: "unlock" } },

          { uid: "ch-give", fragment_type: "choice", edge_id: "e-give",
            text: "Give coins to the guard.",
            available: true,
            accepts: { kind: "compose", parts: [
              { role: "amount", accepts: { kind: "quantity",
                  min: 1, max: 7, step: 1, unit: "coin",
                  ledger_ref: "purse" } },
              { role: "target", accepts: { kind: "pieces", min: 1, max: 1,
                  constraints: { target_zone_ref: "z-room",
                                 predicate_ref: "is_actor" } } },
            ] },
            ui_hints: { hotkey: "6",
              source: "mob.guard", source_kind: "mob",
              contribution: "transfer" } },

          { uid: "ch-name", fragment_type: "choice", edge_id: "e-name#sword",
            text: "Name your sword.",
            available: true,
            accepts: { kind: "text",
              required: true,
              placeholder: "e.g. Hopebreaker",
              validators: [
                { kind: "length", min: 2, max: 24 },
                { kind: "regex", pattern: "^[A-Za-z][A-Za-z '-]*$",
                  message: "Letters, spaces, ' and - only." },
              ] },
            ui_hints: { hotkey: "7",
              source: "asset.sword", source_kind: "asset",
              contribution: "interaction" } },

          { uid: "ch-wait", fragment_type: "choice", edge_id: "e-wait#evening",
            text: "Wait until evening.",
            available: true, accepts: { kind: "pick" },
            ui_hints: { hotkey: "8",
              source: "schedule", source_kind: "schedule",
              contribution: "wait",
              time_delta: { periods: 2, arrives_at: "evening" },
              cost_previews: [{ ledger_key: "periods", delta: -2, unit: "periods" }] } },

          { uid: "ch-cmd", fragment_type: "choice", edge_id: "interpret_command",
            text: "Try a command.",
            available: true,
            accepts: { kind: "raw_command" },
            ui_hints: { hotkey: ">", reserved: "command_bar" } },
        ],

        metadata: {
          world: "manor",
          // v1.3 sandbox info-channel — typed metadata.info_state
          info_affordances: [
            { kind: "world_time", label: "Watch",      shortcuts: ["t", "time"],
              query: { kinds: ["world_time"] } },
            { kind: "presence",   label: "Here",       shortcuts: ["h", "look"],
              query: { kinds: ["location", "presence"] } },
            { kind: "inventory",  label: "Carrying",   shortcuts: ["i", "inv"],
              query: { kinds: ["inventory"] } },
            { kind: "map",        label: "Map",        shortcuts: ["m", "map"],
              // hand-it-back: bundle decides what `format` means
              query: { type: "map", format: "graph" } },
            { kind: "agenda",     label: "Schedule",   shortcuts: ["a"],
              query: { kinds: ["agenda"] } },
            { kind: "objectives", label: "Objectives", shortcuts: ["o"],
              query: { kinds: ["objectives"] } },
            { kind: "help",       label: "Help",       shortcuts: ["?"],
              query: null },  // null = default info kind = the channel itself
          ],
          info_state: {
            version: 17,
            dirty_kinds: ["location", "inventory", "agenda"],
            available_kinds: ["status", "inventory", "map", "world_time",
                              "agenda", "presence", "objectives", "help"],
          },
          grammar: {
            verbs: [
              { verb: "look", aliases: ["l"], frames: ["look", "look at {noun}"] },
              { verb: "take", aliases: ["get", "grab"], frames: ["take {noun}"] },
              { verb: "open", aliases: [], frames: ["open {noun}"] },
              { verb: "walk", aliases: ["go"], frames: ["walk to {noun}"] },
              { verb: "give", aliases: [], frames: ["give {n} {noun} to {noun}"] },
              { verb: "name", aliases: [], frames: ["name {noun} {text}"] },
              { verb: "wait", aliases: [], frames: ["wait until {noun}"] },
            ],
            nouns: [
              { noun: "lamp",     aliases: ["lantern"],   piece_ids: ["lamp"] },
              { noun: "mailbox",  aliases: ["box"],       piece_ids: ["mailbox"] },
              { noun: "painting", aliases: ["picture"],   piece_ids: ["painting"] },
              { noun: "guard",    aliases: ["soldier"],   piece_ids: ["guard"] },
              { noun: "hall",     aliases: ["hallway"],   piece_ids: ["loc-hall"] },
              { noun: "yard",     aliases: ["courtyard"], piece_ids: ["loc-yard"] },
              { noun: "cellar",   aliases: ["basement"],  piece_ids: ["loc-cellar"] },
              { noun: "attic",    aliases: [],            piece_ids: ["loc-attic"] },
              { noun: "coin",     aliases: ["coins"],     piece_ids: ["coin_purse"] },
              { noun: "sword",    aliases: ["blade"],     piece_ids: [] },
              { noun: "evening",  aliases: [],            piece_ids: [] },
            ],
            placeholder: "try: take lamp · walk to hall · wait until evening",
            examples: ["look", "take lamp", "give 1 coin to guard"],
          },
        },
      },

      projected_state: {
        sections: [
          // ----- WORLD TIME (Tier S kv_list w/ kind:"world_time", v1.2 convention)
          { section_id: "world_time", title: "Time", kind: "world_time",
            value: { value_type: "kv_list", items: [
              { key: "turn",   value: 22 },
              { key: "period", value: "afternoon" },
              { key: "day",    value: 3 },
              { key: "phase",  value: "waxing crescent" },
            ] },
            hints: { style_tags: ["clock"] } },

          // ----- Periods budget (renders as bar)
          { section_id: "periods", title: "Periods", kind: "resource",
            value: { value_type: "kv_list", items: [
              { key: "remaining", value: 13, max: 24, unit: "periods", hint: "bar" },
            ] } },

          // ----- LOCATION / PRESENCE (Tier S item_list w/ kind:"location")
          { section_id: "location", title: "Here", kind: "location",
            value: { value_type: "item_list", items: [
              { label: "Bedroom",        detail: "manor · north wing", tags: ["place"] },
              { label: "brass lamp",     detail: "on the desk",        tags: ["fixture", "takeable"] },
              { label: "small mailbox",  detail: "closed",             tags: ["fixture", "locked"] },
              { label: "framed painting", detail: "water-stained",     tags: ["fixture"] },
              { label: "north to hall",  detail: "guard visible",      tags: ["exit"] },
              { label: "down to cellar", detail: "unexplored",         tags: ["exit"] },
            ] } },

          // ----- AGENDA (kv_list with kind:"agenda" — disclosed schedule)
          { section_id: "agenda", title: "Schedule", kind: "agenda",
            value: { value_type: "item_list", items: [
              { label: "Barn dance",       detail: "evening, at the barn",  tags: ["upcoming", "known"] },
              { label: "Guard rotation",   detail: "next period",           tags: ["soon"] },
              { label: "Tide receding",    detail: "midnight",              tags: ["natural", "tentative"] },
            ] } },

          // ----- Resources
          { section_id: "purse", title: "Purse", kind: "wallet",
            value: { value_type: "kv_list", items: [
              { key: "coin", value: 7, unit: "coin" },
            ] } },

          { section_id: "weight", title: "Carried", kind: "score",
            value: { value_type: "kv_list", items: [
              { key: "weight", value: 3, max: 12, unit: "stone", hint: "bar" },
            ] } },

          // ----- Objectives
          { section_id: "objectives", title: "Objectives", kind: "objectives",
            value: { value_type: "item_list", items: [
              { label: "Find a way into the attic", detail: "hatch bolted from above", tags: ["open"] },
              { label: "Deliver Captain Ros's letter", detail: "to the garrison",      tags: ["open"] },
            ] } },
        ],
      },
    };
  })();

  return { crossroads, garage, gravel, manor };
})();
