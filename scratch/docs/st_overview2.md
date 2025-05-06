StoryTangl Framework
====================

Core 
----

The basic managed object in the framework is the **Entity**.

All Entities have uids, labels, and tags.  Their core abilities are to **match(\*\*features)** for self-identification, and to **structure/unstructure** into subclasses using an _obj\_cls_ parameter.

Helper classes like **Singleton**, **Registry**, **Handler**, **Node**, and **Fragment** are all entity subclasses.

Graphs and Nodes
----------------

**Story World**: a registry of templates and handlers that act as a factory and plug-able handler manager for a story domain

**Story Graph**: a registry of concept, structure, and journal nodes related to a particular story world

**Concept Layer**: concept nodes are usually mutable and serve to carry scoped state through the story, such as themes, places, events, schedules, actors, props, quests

**Structural Layer (Plot)**: structure nodes are specialized story nodes grouped in dag-like subgraphs (scenes), they can be mutable, but generally refer scope to their parents or other linked concepts, the structure layer can be traversed by choices or other motivator edges which moves a cursor, triggers a state update, and generates a projection update

**Projection Layer (Journal)**: the journal is an embedded linear manifold of 'projected' plot nodes (chunk/entry nodes) that carry immutable content fragments.  The journal can be indexed by the client by entry or section/bookmark.  Entry nodes are parented by their source in the graph, so they can manage their fragments, but the fragment stream is completely independent of the graph other than optional annotations.  One structure node can parent multiple projection nodes at different places in the sequence (a repeating event, for example).


Links
-----

**Parent**: nodes may have at most one parent, but any number of children and associates

**Children**: nodes with parents are _owned_, usually they will be referenced as part of a named component ('actor look', 'scene blocks')

**Associates**: some nodes are _associated_ with other nodes dynamically, for example, an inventory node may link to a discrete sword node until it is unlinked by dropping it.  The sword's _parent_ may actually some abstract asset manager like a quest, but the node can be associated with an inventory or place dynamically.

**Edges**: edges are *indirect links*, they are themselves nodes with a parent/predecessor and a successor, where the successor is the actual node of interest.  Motivators between structure nodes are edges (choices, actions, etc).  Dynamic edges can be used to link roles in structure nodes to concepts, like the shopkeeper today is the bard, but tomorrow the shopkeeper role will be linked to the princess.


Story Scripts
-------------

Story scripts may have any format but should compile into a set of templates and handlers as expected by the general world manager.

The simplest script is a snapshot or serialized version of the initial graph state, a domain plugin handler class using the common entry points, and any domain-specific subclasses referenced in the script


Story Lifecycle
---------------

1. scripts are compiled into a story world

2. story graph is factoried by the world (copied or structured from unstructured data)

3. service manager initializes the graph (sets entry point, state update triggers first journal entry)

4. automatically triggered edges (motivators) are followed (each state update triggers additional journal entries) until the traversal logic blocks on client interaction

5. client requests content, journal entries are formatted into an appropriate fragment stream response 

6. client submits an action/choice and optional payload

7. selected choice edge is followed (state update triggers journal entry) and returrn to 4

8. at some point, the story content will be exhausted or otherwise terminate without providing a blocking interaction, at which point we can archive the story



