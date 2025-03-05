Roles
-----

we want is a definition for a high dimensional story-shape space and plan to implement various tools for different interactions with it.  One interaction role is creator, an agent that defines a potential story space.  One role is navigator, an agent that can collapse a potential story space into one or more realized story threads, either interactively or according to algorithmic rules.  The final role is presenter, an agent that can format a realized story thread according to the capabilities of the reader (actual media, language, markup, metadata for a client to consume).

We need two or three models/apis for members of this space at different phases of their lifecycle.  

- First, a model for a bounded abstract story-space.  This could range from a trivial example of a pre-navigated novel or short story, to a discrete story model like a cyoa, with discrete possible paths and consequences pre-determined, to a continuous story model, like an rpg with a set of rules and maps that can generate an infinite number of stories, or various combinations thereof.  A single model need not cover all possible representations, more important is what the api is, in particular, how we can sample from a space to navigate within a story.  In practice, I imagine this is a database of templates for story concepts annotated with links between them.

- Second is a data model for tracking the state of a story path being navigated/already navigated through the space.  What story space it belongs to, what navigation choices have been made, how the story world has been effected, what roles/places/events/scenes/choices have been created/sampled/seen/discarded/modified.  I imagine this is an abstract graph derived from elements sampled from the story space, then represented as data models and rules that can be manipulated by an interpreter.  This should be serializable or otherwise amenable to stateless access.  

- Third, we need a model for the presenter to use in communicating with a client.  This can be a json schema, but it should also include a negotiation where the client can declare its features/restrictions, and probably a (separate?) communication protocol for the presenter to request media or narrative creation for a story-state update, either from the interpreter holding the story model, or from federated services like an LLM or gen ai image service or resolved link from a media server.

