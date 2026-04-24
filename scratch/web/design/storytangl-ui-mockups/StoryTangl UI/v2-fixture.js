// Canonical fixture — a single RuntimeEnvelope + ProjectedState that every
// shell in v2 consumes. Shaped to match tangl.journal.fragments and
// tangl.service.response exactly.
//
// Scene: Crossroads Inn, turn 3. Elen has just entered; a stranger at the bar
// is trying to sell the player a map. Media is mixed (narrative_im ready,
// dialog_im pending generation). One choice is locked behind a blocker, one
// accepts a freeform payload, one is a simple edge.

window.FIXTURE = {
  envelope: {
    // RuntimeEnvelope
    cursor_id: "b6e0f3a4-1d5f-4b62-9e1e-aa8101b2d7f1",
    step: 47,
    fragments: [
      // Scene group — ties everything below into one turn
      {
        uid: "f-grp-scene-03",
        fragment_type: "group",
        group_type: "scene",
        member_ids: [
          "f-med-cover", "f-content-open", "f-med-narr",
          "f-grp-dlg", "f-kv-scene", "f-choice-bargain",
          "f-choice-refuse", "f-choice-freeform", "f-choice-sneak",
        ],
      },

      // Cover image for the scene (persists across turns; overlay role)
      {
        uid: "f-med-cover",
        fragment_type: "media",
        content: "assets/crossroads_inn_night.jpg",
        content_format: "url",
        media_role: "cover_im",
        scope: "world",
        staging_hints: {
          media_shape: "banner",
          media_position: "top",
          media_size: "large",
          media_transition: "fade_in",
          media_duration: "medium",
        },
      },

      // Opening prose
      {
        uid: "f-content-open",
        fragment_type: "content",
        content: "Rain drums on the thatch. Inside the Crossroads Inn the air is smoke and peat. A man in a rust-colored cloak beckons from the corner booth, a folded vellum square weighted under his cup.",
        content_format: "md",
        hints: { style_tags: ["narrative", "establishing"] },
      },

      // Narrative inline image
      {
        uid: "f-med-narr",
        fragment_type: "media",
        content: "assets/stranger_booth.jpg",
        content_format: "url",
        media_role: "narrative_im",
        staging_hints: {
          media_shape: "portrait",
          media_position: "right",
          media_size: "medium",
          media_transition: "fade_in",
        },
      },

      // Dialog group (GroupFragment with group_type="dialog")
      {
        uid: "f-grp-dlg",
        fragment_type: "group",
        group_type: "dialog",
        member_ids: ["f-att-1", "f-med-avatar-stranger", "f-att-2", "f-med-dlg-pending"],
      },
      {
        uid: "f-att-1",
        fragment_type: "attributed",
        who: "Stranger",
        how: "low, confidential",
        media: "speech",
        content: "They say you're headed north. I've got something the garrison would pay for and never use.",
      },
      {
        uid: "f-med-avatar-stranger",
        fragment_type: "media",
        content: "assets/stranger_avatar.jpg",
        content_format: "url",
        media_role: "avatar_im",
        staging_hints: { media_shape: "avatar", media_size: "small" },
      },
      {
        uid: "f-att-2",
        fragment_type: "attributed",
        who: "Stranger",
        how: "smiling without teeth",
        media: "speech",
        content: "Forty silver. You look at it, you buy it. No haggle.",
      },
      // Pending generated dialog illustration (engine returned a placeholder)
      {
        uid: "f-med-dlg-pending",
        fragment_type: "media",
        content: "gen:vellum_map_close_up",
        content_format: "rit",
        media_role: "dialog_im",
        staging_hints: { media_shape: "square", media_size: "small" },
        // non-canonical but common hint; v2 shows how client handles it
        generation_status: "pending",
      },

      // KV status fragment (inline, in-turn)
      {
        uid: "f-kv-scene",
        fragment_type: "kv",
        content: [
          ["time", "late evening"],
          ["coin", "63 s"],
          ["companions", "Bram, Elen"],
          ["weather", "rain"],
        ],
        hints: { style_tags: ["status-inline"] },
      },

      // Choice: bargain (simple edge)
      {
        uid: "f-choice-bargain",
        fragment_type: "choice",
        edge_id: "e-crossroads-03-bargain",
        text: "Pay the forty silver.",
        available: true,
        ui_hints: { hotkey: "1", icon: "coin", emphasis: "primary" },
      },
      // Choice: refuse
      {
        uid: "f-choice-refuse",
        fragment_type: "choice",
        edge_id: "e-crossroads-03-refuse",
        text: "Tell him to keep his paper.",
        available: true,
        ui_hints: { hotkey: "2" },
      },
      // Choice: freeform (accepts a typed argument)
      {
        uid: "f-choice-freeform",
        fragment_type: "choice",
        edge_id: "e-crossroads-03-haggle",
        text: "Haggle.",
        available: true,
        accepts: {
          payload_type: "offer_silver",
          input: "integer",
          min: 1,
          max: 63,
          placeholder: "silver to offer",
        },
        ui_hints: { hotkey: "3", icon: "chat" },
      },
      // Choice: unavailable
      {
        uid: "f-choice-sneak",
        fragment_type: "choice",
        edge_id: "e-crossroads-03-steal",
        text: "Lift the map while he drinks.",
        available: false,
        unavailable_reason: "Requires Sleight of Hand ≥ 2",
        blockers: [
          { kind: "skill", key: "sleight_of_hand", need: 2, have: 1 },
          { kind: "flag",  key: "companion_elen_watching", value: true },
        ],
        ui_hints: { hotkey: "4", icon: "hand" },
      },

      // User event — hint the client should stash for this user
      {
        uid: "f-ue-1",
        fragment_type: "user_event",
        event_type: "achievement_progress",
        content: { id: "met_10_strangers", progress: "7/10" },
      },

      // Control fragment — update a prior content fragment (e.g. a glossary gloss)
      {
        uid: "f-ctrl-1",
        fragment_type: "update",
        ref_type: "content",
        ref_id: "glossary:vellum",
        payload: { gloss: "parchment made from calfskin; expensive." },
      },
    ],
    last_redirect: null,
    redirect_trace: [],
    metadata: { world: "crossroads", chapter: "ch01" },
  },

  // ProjectedState — sidecar, one entry per section kind
  projected_state: {
    sections: [
      {
        section_id: "health",
        title: "Wounds",
        kind: "status",
        value: { value_type: "scalar", value: "Sound" },
      },
      {
        section_id: "purse",
        title: "Purse",
        kind: "resource",
        value: {
          value_type: "kv_list",
          items: [
            { key: "silver", value: 63 },
            { key: "copper", value: 11 },
            { key: "favors", value: 1 },
          ],
        },
      },
      {
        section_id: "inventory",
        title: "Satchel",
        kind: "inventory",
        value: {
          value_type: "item_list",
          items: [
            { label: "Hooded lantern",        detail: "half-oil",        tags: ["light"] },
            { label: "Letter, sealed",         detail: "for Captain Ros", tags: ["quest"] },
            { label: "Elen's knife",           detail: "balanced",        tags: ["weapon","borrowed"] },
          ],
        },
      },
      {
        section_id: "party",
        title: "Party",
        kind: "roster",
        value: {
          value_type: "table",
          columns: ["name", "role", "mood"],
          rows: [
            ["Bram", "soldier", "surly"],
            ["Elen", "scout",   "watchful"],
          ],
        },
      },
      {
        section_id: "tags",
        title: "Conditions",
        kind: "tags",
        value: { value_type: "badges", items: ["rain-soaked", "hungry", "hunted"] },
      },
    ],
  },
};
