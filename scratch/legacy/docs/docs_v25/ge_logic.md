StoryTangl Game Engine
======================

Story Generator
---------------
Query story context (game instances) and render results

- story teller/api
  - set/reset player
  - set/reset context for player
  - get status for context
  - get scene for context -> sc update
  - get resource/img for world/player/context
  - put/do action for context -> sc update

- player/story context
  - narrative node index with globals
  - metadata for player, other contexts
  - player account/story context manager

- narrator
  - role to voice
    - adopts
  - strings from NILF (jinja2)
    - word/syn
    - phrase/syn_expr
    - nom/word/pronoun 
    - conj/conj_word
  - prereading->NILF

- illustrator
  - pix from DILF
  - predrafting->DILF

- preflight logic and api testing


Narrative Structure
-------------------
Generate and update contexts from structure elements

In *STRIPS* terms, a narrative consists of a set of nodes with preconditions and effects, an initial game state, and conditional goals/end game states.

- scene

  - place/loc/env/setting
    - stage (instance)
    - viewpoint (narrator, illustrator)
    - local rules/ns
  - roles
    - actors (instance, subject or object of actions)
    - casting
    - global p role is implicit in every scene
  - assets
    - local props (world singleton, "object of actions")
    - prop wallet
  
  - games
    - driven by update logic to conditional outcome
    - table (place)
      - update rules, strategy, chance
    - opponent/s (role)
    - game tokens (assets, token wallet)

  - passages/blocks

    - redirects
      - conditionally force logic to a different block
      - optional return

    - actions
      - update state/game
      - direct to new passage/block
        - direct to block
        - direct to scene done block
        - direct to game end scene/block

    - may be dynamically generated at init or at get

  - roles, places, props are shared across blocks
  - blocks form a tree from the root block ("start") and have paths to multiple possible leafs ("done") depending on action selection and game outcomes
  - typically reaching a leaf results in a scene outcome and prevents the scene from being replayed
  - actions may route to blocks in other scenes at any point
  - scene from loc for interaction at a menu/hub

- world
  - manages scenes, roles, places, props
  - creates new contexts from templates
  - ui direction
  - narrator hints
  - illustrtor hints

- common/core features
  - tree relationships
  - node index
  - uid/eid/label
  - automorphic/kwargs templates
  - preconditions
  - effects

- preflight story logic testing


Scripting Language
------------------
Generate structural elements from content

- narrative
  - natural language
  - narrative intermediate langauge format (NILF) refers to roles, places, assets

  - Consider `He looks at her hands`

    - Enumerated NILF: `{{ p.nom(PT.S) }} {{ p.conj('looks') }} at {{ w0.nom(PT.PA) }} {{ w0.prop('hands') }}`
    - Abbreviated NAIF: `{{ p.subj }} {{ p.looks }} at {{ w0.pa }} {{ w0.hands }}`
    - Inline NAIF: `{{ he(p) }} {{ looks(p) }} at {{ her_(w0) }} {{ hands(w0) }}`
    - Inline NAIF (default gender map, hands in actor assets): `{{ he() }} {{ looks() }} at {{ her_() }} {{ hands(w0) }}`
    - Inferred NAIF (default gender map, hands in actor assets): `he looks@ at her_ hands@w0`

- illustrative
  - refer to svg, png w special naming
  - dynamic illustration language format (DILF) refers to roles, places, assets
    - generates images and image update deltas (show/hide, change colors, animate)

- runtime
  - variables/local namespace
  - conditions
  - effects

- enumerated quantifiers
  - traits like strength, int, etc., map to attrs, props, other features
  - incremental quality scale divided into 5 classes for display and logic
    (poor, ok, average, good, excellent)
  - quality operators (incr, decr, set(v|q), min, max)

- preflight content testing
  - spell checking
  - connectivity (graphing)
  - completeness
  - ensure completable


Content
-----------
- world spec
- libraries
  - new classes
  - hooks (on_init, on_new_ctx, on_new_obj, on_get, on_do, on_ns, on_status)
  - NILF/DILF extensions
- narrative script files
  - yaml (could be xml or other)
  - markdown
  - markdown + NILF hints
  - dilf
  - templates
- illustration source
  - svg, png
- dictionaries (for spell checking)
- ui assets


Clients
-----------
Access story elements through API, render output/updates, accept player interactivity

- REST server
- web client
- cli
- renpy
- ebook


Refs
-----------

Kim, Seok Kyoo et al. “Programming the Story: Interactive Storytelling System.” Informatica (Slovenia) 35 (2011): 221-229.

Richard E. Fikes, Nils J. Nilsson (Winter 1971). "STRIPS: A New Approach to the Application of Theorem Proving to Problem Solving" (PDF). Artificial Intelligence. 2 (3–4): 189–208. CiteSeerX 10.1.1.78.8292. doi:10.1016/0004-3702(71)90010-5.


