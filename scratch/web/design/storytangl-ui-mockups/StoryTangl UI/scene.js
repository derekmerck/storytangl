// Fake StoryTangl backend: crossroads_inn mini-flow mirroring the real fragment stream.
// Each block returns the fragments the engine would emit + the action list + state.

window.SCENE = (() => {
  const blocks = {
    start: {
      id: "prologue.start",
      scene: "prologue",
      title: "The Crossroads Inn",
      media: { role: "narrative_im", label: "tavern.svg — landscape", kind: "landscape" },
      text:
        "The Crossroads Inn sits at the junction of three ancient roads. " +
        "Rain patters against the windows as you push open the heavy oak door.\n\n" +
        "The common room is warm and inviting, lit by a crackling fireplace. " +
        "A few patrons sit scattered at wooden tables.",
      actions: [
        { id: "a1", text: "Approach the fireplace", to: "meet_aria" },
        { id: "a2", text: "Talk to the innkeeper", to: "innkeeper" },
      ],
      stateDelta: { visited: ["prologue.start"] },
    },
    meet_aria: {
      id: "prologue.meet_aria",
      scene: "prologue",
      title: "By the fire",
      speaker: { name: "Aria", role: "companion", avatar: "companion.svg" },
      media: { role: "avatar_im", label: "companion.svg — portrait", kind: "portrait" },
      text:
        "You approach the fireplace. The cloaked figure looks up, revealing " +
        "sharp eyes and a weathered face.\n\n" +
        "\"Aria,\" she introduces herself simply. \"Looking for work, or just " +
        "passing through?\"",
      actions: [
        { id: "a1", text: "I'm looking for the Northern Pass", to: "request_help" },
        { id: "a2", text: "Just warming up before moving on", to: "start" },
      ],
      stateDelta: { met: ["Aria"], visited: ["prologue.meet_aria"] },
    },
    request_help: {
      id: "prologue.request_help",
      scene: "prologue",
      title: "A guide's offer",
      speaker: { name: "Aria", role: "companion", avatar: "companion.svg" },
      text:
        "Aria's expression softens slightly. \"The Northern Pass? " +
        "Dangerous this time of year.\" She pauses. \"But I know the way. " +
        "For the right price, I could guide you.\"",
      actions: [
        { id: "a1", text: "Offer to split any treasure found", to: "trail_start" },
        { id: "a2", text: "Politely decline", to: "start" },
      ],
      stateDelta: { flags: ["aria_offered_guide"], visited: ["prologue.request_help"] },
    },
    innkeeper: {
      id: "prologue.innkeeper",
      scene: "prologue",
      title: "Behind the bar",
      speaker: { name: "Innkeeper", role: "npc", avatar: null },
      text:
        "The innkeeper, a portly man with a bushy mustache, greets you warmly. " +
        "\"Welcome, traveler! What'll it be?\"",
      actions: [
        { id: "a1", text: "Ask about rumors", to: "rumors" },
        { id: "a2", text: "Return to the common room", to: "start" },
      ],
      stateDelta: { met: ["Innkeeper"], visited: ["prologue.innkeeper"] },
    },
    rumors: {
      id: "prologue.rumors",
      scene: "prologue",
      title: "Rumors of the Pass",
      speaker: { name: "Innkeeper", role: "npc", avatar: null },
      text:
        "\"Well,\" the innkeeper leans in conspiratorially, \"they say the old " +
        "fortress in the Northern Pass holds treasure beyond measure. But the " +
        "way is treacherous, and strange things have been seen in those " +
        "mountains...\"",
      actions: [
        { id: "a1", text: "Thank him and return", to: "start" },
      ],
      stateDelta: { knowledge: ["fortress_rumor"], visited: ["prologue.rumors"] },
    },
    trail_start: {
      id: "chapter1.trail_start",
      scene: "chapter1",
      title: "On the forest path",
      media: { role: "narrative_im", label: "forest.svg — landscape", kind: "landscape" },
      text:
        "You and Aria set out at dawn. The forest path is narrow and overgrown, " +
        "but she navigates it with practiced ease.",
      actions: [
        { id: "a1", text: "Continue deeper into the forest", to: "forest_encounter" },
      ],
      stateDelta: { visited: ["chapter1.trail_start"], locations: ["Forest path"] },
    },
    forest_encounter: {
      id: "chapter1.forest_encounter",
      scene: "chapter1",
      title: "A fork in the path",
      text:
        "A fork in the path appears ahead. Aria pauses, studying both options " +
        "carefully.",
      actions: [
        { id: "a1", text: "Left path — faster, riskier", to: "left_path" },
        { id: "a2", text: "Right path — safer, longer", to: "right_path" },
      ],
      stateDelta: { visited: ["chapter1.forest_encounter"] },
    },
    left_path: {
      id: "epilogue.left_path",
      scene: "epilogue",
      title: "The treacherous way",
      text:
        "The left path proves treacherous. After a harrowing climb, you reach " +
        "the Pass, but Aria is impressed by your courage.",
      actions: [
        { id: "a1", text: "Enter the fortress", to: "end" },
      ],
      stateDelta: { visited: ["epilogue.left_path"], flags: ["aria_impressed"] },
    },
    right_path: {
      id: "epilogue.right_path",
      scene: "epilogue",
      title: "The long way around",
      text:
        "The right path is longer but safer. You arrive at the Pass as the sun " +
        "sets, exhausted but unharmed.",
      actions: [
        { id: "a1", text: "Make camp", to: "end" },
      ],
      stateDelta: { visited: ["epilogue.right_path"] },
    },
    end: {
      id: "epilogue.end",
      scene: "epilogue",
      title: "Before the fortress",
      text:
        "The ancient fortress looms before you, silhouetted against the evening sky. " +
        "Your adventure is just beginning...\n\n[To be continued]",
      actions: [],
      terminal: true,
      stateDelta: { visited: ["epilogue.end"] },
    },
  };

  return {
    blocks,
    start: "start",
    // Placeholder "card" widget data — the speculative CCG idea for later.
    cards: [
      { id: "c1", name: "Rain on Oak", cost: "II", kind: "omen", text: "Reveal a companion at an inn." },
      { id: "c2", name: "Aria's Compass", cost: "I", kind: "relic", text: "Shift the path one step safer." },
      { id: "c3", name: "Fortress Rumor", cost: "—", kind: "knowledge", text: "Peek the next fork's risk." },
    ],
  };
})();
