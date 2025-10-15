Graph Untangling as Story Telling
=================================

Consider "feature untangling" as a virtual machine for telling story programs.

- **Fabula** -- the tangled story space, all _possible_ events and concepts for a given story domain, noumenal story (kant), the story itself (schoppenhaur)
- **Episodic Process** -- flow control along structural nodes and edges, realizing and ordering events and concepts from the fabula into a stable configuration, and updating the syuzhet, the story resolved by will
- **Syuzhet** -- the trace content or journal of an episodic process given a set of choices, phenomenal story, the story at hand

Structure
---------
- **Books, acts, scenes** -- structural subgraphs corresponding to journal subsequences
- **Events, descriptions, monologs, dialogs** -- structural nodes that generate journal updates when traversed by the flow control cursor
- **Roles, settings, props** -- resource dependencies required as indirect context for rendering journal entries; a villain, a castle, a sword
- **Actors, locations, assets** -- resolved anchor resources that can fulfill dependencies
- **Choice Points** -- exclusive gateways requiring user input
- **Consequence Propagation** -- how choices affect downstream provisioning

Chronology
----------
- Structure and flow control mediate between story-time and discourse-time
- **Story Time** -- temporal coordinates in the realized fabula  
- **Discourse Time** -- position in the trace journal  
- **Narrative Velocity** -- ratio of story time to discourse time per node
- **Temporal Edges** -- structural flashback/flashforward links that violate chronology

Style and Output
----------------
- **Pacing, motifs, voice** -- trace content generation handlers that can be attached to events or concepts/resources
- **Media** -- data resource dependencies that can be filled by a DataProvisioner and rendered to DataFragment trace nodes

Emotional Architecture
----------------------
- **Emotional State** -- mutable resource tracking reader/character feelings
- **Beats** -- micro-nodes that modify emotional state
- **Arcs** -- subgraphs with required emotional trajectories
- **Catharsis** -- special nodes that resolve accumulated emotional tension
- **Motivations, relationships** -- mutable resource subgraphs that provide indirect context for gating and other handlers
- **Stakes** -- weight values on edges that determine consequence magnitude
- **Conflicts** -- incompatible requirement sets that force choices
- **Tension** -- unresolved dependencies that create suspense

Meta-Properties
---------------
- **Hidden State** -- context not exposed to trace journal
- **Narrative Contracts** -- predicate constraints ensuring genre expectations
- **Dramatic Irony** -- context available to journal but not to character resources
- **Reveals** -- resolved but gated context that becomes available later at specific nodes
- **Mysteries** -- requirement chains with hidden intermediate nodes
- **Foreshadowing** -- partial context leaks from future/hidden/linked but gated nodes
- **Chekhov's Gun** -- backward process showing that every resource introduced is consumed
- **Red Herrings** -- "unnecessary" dependency chains that are consumed by a decoy sink
- **Continuity** -- forward process showing that every requirement is satisfied

Example
-------
•	Domain: Abstract “Hero’s Journey”
•	Nodes: Hero, Mentor, Antagonist, Treasure, Dragon, Quest
•	Requirements/Dependencies:
	•	“Hero meets Mentor before Dragon”
	•	“Treasure requires Dragon defeated”
	•	“Dragon requires Hero has Sword”
•	Provisions:
	•	Sword provided by Mentor
	•	Dragon provided by creating or recruiting existing dragon resource
•	Edit Actions:
	•	Reuse existing dragon, create new sword, modify hero’s attributes

------

Connected entity structure representing the latent story space.

StoryTangl graphs are the backbone of narrative representation, where:
- Story elements (scenes, actors, objects) are nodes
- Relationships (ownership, traversal options) are edges
- State is distributed locally rather than in a global dictionary


----

Story Node Lifecycle
====================

Every story node "class" needs a few things:

1. A data model, this is the keywords that could be in a script yaml document to create/deserialize it
2. A set of flexible/plugable handlers for instances of the class that trigger on different events:
  - new(base cls, kwargs, domain) -> (new cls, new kwargs)     # No context
  - init -> None                                               # No context
  - gather locally scoped context -> dict
  - find or create/render media or narrative content -> content dict (direct or indirect - content/blob id)
  - follow an edge -> None  (do an action)
  - visit/enter a node -> next node or None
  - check conditions, availability -> Any, bool
  - apply effects -> bool
  - associate with another node -> None
  - find or create an associate -> Associate
3. Content creators that know how to generate content for a node content spec, register blobs if required, and return a content dict for a node 
4. Adapters that know how to convert different types of content dicts into appropriate narrative or media journal fragments
5. An adapter that knows how to convert a graph or node into an info model

---

`tangl.story` is a simple application module, its members should ONLY depend on:
- **core**
- **utils**

It is orthogonal to `tangl.vm` and should not have overlapping responsibilities other than providing feature handlers with appropriate phase names and return types.

---

episodic metrics:
- velocity (chronology per discourse entry or step)
- tangents, directness