Media
=====

Media - images, audio, videos, animations - are referenced in the script, then that reference is converted to a URL by the backend server.  However, the client still has to collect the media and decide if and how to use it locally.

For example, the command-line UI used for testing simply discards media references.  The provided web client supports images, but (currently v3.7) doesn't handle video or audio.

The backend server includes a media server component, which makes it seem like the media _is_ part of the backend.  But the media server is distinct and independent from the story api.  It can be easily swapped out for a CDS, for example, by updating a couple of path variables.

To further further confuse things, the backend can *create* certain types of media either as a preprocess during development or dynamically while updating the story.

World Media
-----------

This is media that comes with the world and is shared by every story.

There are two type of world media: *static* and *generated*.

Static world media are just files, their name reference is to their file name.

Generated world media are also 'just' files, but they are created by the backend using an illustration service.

For example, if an author has access to a Stable Diffusion service, the media reference can be a description/prompt for the image, and the backend will help create and organize the corresponding files as an offline process.

Story Media
-----------

Story media is, by its nature, dynamically generated on-demand, based on a particular story-state such as the location or weather or the clothes that a character is currently wearing.

Story media is described *procedurally*.  That is, a process for mapping story-state-variables to an image space.

For example, an author can describe an NPC avatar in terms of body features, and then regenerate a matching SVG as the avatar terms are updated in the story to reflect things like clothes and equipment changes.

Media Forges
------------

:StableForge:


:SvgForge:

