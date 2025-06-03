
from tangl.cli.app import TanglShell
from tangl.world.world import World

from cmd2 import CommandResult
from cmd2_ext_test import ExternalTestMixin
import pytest

# Test the StoryCLI application
class TestStoryCLI(ExternalTestMixin, TanglShell):
    pass

@pytest.fixture
def client():
    app = TestStoryCLI()
    app.fixture_setup()
    yield app
    app.fixture_teardown()


# @pytest.mark.skip(reason="Not working yet")
def test_controllers(client):
    # execute a command
    out = client.app_cmd("story")
    print(out)
    # validate the command output and result data
    assert isinstance(out, CommandResult)
    print( out.stdout.strip() )
    assert( not out.stderr )

    assert """The Spire has fallen.  Your treasonous confederate, TinkerBell,
led your troop of catchers straight to the wild-sprite hive, just 
as she had promised.""" in out.stdout

    out = client.app_cmd("do 1")
    print(out)
    assert( not out.stderr )

    out = client.app_cmd("system_info")
    print(out)
    assert( not out.stderr )

    out = client.app_cmd("status")
    print(out)
    assert( not out.stderr )

    out = client.app_cmd("apply 'player.cash=10000'")
    print( out )
    assert( not out.stderr )

    out = client.app_cmd("check 'player.cash'")
    print(out)
    assert( not out.stderr )
    assert "10000" in out.stdout

