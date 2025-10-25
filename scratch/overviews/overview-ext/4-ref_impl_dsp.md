
Data Layer
----------

Under the business layer we have the data layer.  The service is assumed to be stateless, so we need a robust and flexible serialization strategy.

There are two main serialization concerns:
- stories
- users

A story includes several components: the ASG state, the user (a shared namespace between multiple stories for tracking achievements, etc), the ASG undo/redo history, and the ASG story journal.

The user object provides a shared namespace for tracking multiple stories, sharing achievements, and authorization, if required.

For simplicity, the ASG, user, history, and journal can be represented as graph nodes and all supported by a unified serialization process.

Service Layer
-------------

RESTful and federated to share media and narrative content generation and world definitions.

Basic client interactions are in 3 domains:
- client: request the current journal for a story ('read'), submit a choice/action for a story ('post'), or request metadata about the story state like a map, sidebar summary, etc.  
- account: auth as user, get user status, or create/drop story for user
- system: advertise worlds and features, request handler for feature, get system status

Presentation Layer
------------------

Assume various levels of capability, from a CLI with limited media handling, to a web interface, to a ren'py plugin, for example.  Bundled CLI, web server, and basic web client are provided with lib.

=======


A service and data layer work together to provide a RESTful user facing api, which has basically the same features, but allows a user to indirectly call the story api on their "current story".  The data layer then loads the current story and the service layer invokes the appropriate library api call on it.

Service Layer API
-----------------

user account:
- set user api key
- get info about user (achievements, global story stats) (ro)
- drop a story (rw)
- change current story (rw)

user world:
- list all world instances (ro)
- get info about a world (ro)
- create new story from a world (rw)

user story:
- read entries from the current story journal (ro)
- get info about current story (ro)
- resolve a traversal step in current story (rw)
- undo a step in the current story (rw) (*optional*)

*Note*: Authentication is beyond the scope of the project.  At this level, we allow an api key to be assigned or automatically create one when a _User_ Entity is created merely as a way of distinguishing requests from different users.  For a single user client, it's not necessary to use this feature at all.  For a public multi-user server, the server itself should require its own authentication before allowing an api key to be used with its internal library service interface.

The service layer has an additional job beyond orchestrating users and current stories and passing requests along.  Critically, it is also responsible for finalizing journal entries into their final presentation shape.  For example, text fragments may be saved in markdown, the response finalizer would convert these into html for a web client, or ansi for a cli.  Media fragments may indicate a path to a file on the server, the response finalizer would publish this file at a media endpoint url for a web client, or perhaps convert the image to ansi art for a cli, or load the image as a PIL object to return to a tkinter client.

We will add that as a separate system api category:

system:
- get response capabilities
- set client repsonse preferences

Service federation capabilities could be added in here as well, for example, a service running on a gpu workstation that can create ai generated images from content forge adapters or a service running remotely that can generate unique character nodes and dialog for certain types of stories.


Service
-------
Interface between the story and the game client, intended to support multiple active users each with multiple active story worlds

**Configuration handler**
- Uses DynaBox

**Persistence**
- Presents as a mapping
- Supports various text/binary serializers (json/yaml, pickle)
- Supports various backends (in-memory, files, _redis_, _mongo_)

**Users**
- User api: `create user`, `get user info`, `update user`

**System**
- system api: `get system info`
- system dev api: `reset system`

**Service Manager**
- Wraps story and user api with persistence manager
- Provides world and system api
- Response handler remaps media resources to server locations and converts markdown to html in response objects


REST Server
-----------

- Uses _fastapi_
- Creates a local service manager
- Routers map http calls to service api
- Provide secondary apps for serving static media and web client files


Clients
-------

**Cli**
- Uses _cmd2_ interpreter
- Controllers map statements to service api
- May create a local service manager
- or - may connect to a remote rest server using _requests_

**Tcl**
- Simple graphical interface

**Web**
- Uses _vue3_, _vuetify_
- Connects to a remote rest server using _axios_

