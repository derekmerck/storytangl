from __future__ import annotations
import pickle

from tangl.core.graph import Graph, Node
from tangl.story.concept import Location, Setting


def test_setting():
    loc = Setting(label="set1", location_ref="dummy")
    assert loc.label == "se-set1"
    assert loc.location is None

def test_loc1():
    loc = Location(label="loc1", name="Location Name")
    assert loc.name == "Location Name"

def test_loc2():
    graph = Graph()

    location = Location(label="hither", name="Hither", graph=graph)
    setting = Setting(location_ref="hither", graph=graph)

    print( graph )
    print( location.graph )
    print( location.graph )

    assert graph, "Graph not created"
    assert location.graph is graph, "Location graph is not set properly"
    assert setting.graph is graph, "Loc graph is not set properly"
    assert location.graph is setting.graph, "Graphs not the same"

    assert location.label in graph, "Location key fails"
    assert location in graph, "Location not in graph"
    assert setting in graph, "Loc not in graph"


def test_loc_pickles():

    a = Location(name="Hither")

    s = pickle.dumps( a )
    print( s )
    res = pickle.loads( s )
    print( res )
    assert a == res

    r = Setting(location_ref=a.uid, graph=a.graph)
    # assert r.scout()

    s = pickle.dumps( r )
    print( s )
    res = pickle.loads( s )
    print( res )
    assert r == res

