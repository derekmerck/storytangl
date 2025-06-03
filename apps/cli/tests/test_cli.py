import subprocess

import pytest
from cmd2_ext_test import ExternalTestMixin

from tangl.info import __title__, __version__
from tangl.cli.app import TanglShell

# Test the StoryCLI application
class TestStoryCLI(ExternalTestMixin, TanglShell):

    def __init__(self, *args, service_manager = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_manager = service_manager

@pytest.fixture
def client(mock_service_manager):
    # inject the mock service manager
    app = TestStoryCLI(service_manager = mock_service_manager)
    app.fixture_setup()
    yield app
    app.fixture_teardown()

# Story

def test_get_update(client):
    out = client.app_cmd('story')
    print( out.stdout, out.stderr )
    assert 'You are in a dark room.' in out.stdout
    assert 'Turn on the light.' in out.stdout

def test_get_status(client):
    out = client.app_cmd('status')
    print( out.stdout, out.stderr )
    assert 'status: ongoing' in out.stdout

def test_do_action(client):
    client.app_cmd("set debug true")
    out = client.app_cmd('story')  # setup update todo: should initialize this in cli
    out = client.app_cmd('do 1')
    print( out.stdout, out.stderr )
    assert 'The room is now bright.' in out.stdout

# Story Dev

def test_check_expr(client):
    out = client.app_cmd('check "1+2"')
    print( out.stdout )
    assert "condition" in out.stdout and "result" in out.stdout

def test_apply_effect(client):
    out = client.app_cmd('apply "my_var=2"')
    print( out.stdout )
    assert "apply ok" in out.stdout

def test_get_scene_list(client):
    out = client.app_cmd('scenes my_world')
    print( "worlds:")
    print( out.stdout )
    assert "key" in out.stdout and "value" in out.stdout

# Public

def test_get_world_list(client):
    out = client.app_cmd('worlds')
    print( "worlds:")
    print( out.stdout )

def test_get_world_info(client):
    out = client.app_cmd('world_info')
    print( "world info:")
    print( out.stdout )

def test_get_system_info(client):
    out = client.app_cmd('system_info')
    assert __title__ in out.stdout and __version__ in out.stdout
    print( out.stdout )

# System Dev

def test_reset_system(client):
    client.app_cmd("set debug True")
    out = client.app_cmd('reset')
    print( 'resetting:')
    print( out.stdout )

# Runs independently

def test_afc_cli():
    # Try to open a cli session and get the game engine status
    cli_process = subprocess.run(['python', '-m', 'tangl.cli', 'system_info', 'quit'])
    assert cli_process.returncode == 0
    print( cli_process.stdout )
