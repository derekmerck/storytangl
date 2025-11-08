# engine/tests/test_package_distribution.py
"""
Tests for package distribution and namespace merging.

These tests verify that:
1. Poetry correctly merges tangl subpackages from multiple source dirs
2. Console script entry points reference the correct paths
3. The installed scripts are invokable

Run these against an installed package:
    pip install -e .
    pytest engine/tests/test_package_distribution.py
"""
import subprocess
import sys
import pytest


class TestNamespaceMerge:
    """Verify packages from engine/apps merge into tangl namespace."""

    def test_engine_packages_importable(self):
        import tangl.core
        import tangl.vm
        import tangl.story
        import tangl.service

    def test_cli_app_importable(self):
        import tangl.cli
        from tangl.cli.__main__ import main
        assert callable(main)

    def test_rest_app_importable(self):
        import tangl.rest
        from tangl.rest.__main__ import main
        assert callable(main)

    def test_no_apps_namespace_exists(self):
        """Ensure legacy tangl.apps doesn't exist."""
        with pytest.raises(ModuleNotFoundError):
            import tangl.apps


class TestEntryPoints:
    """Verify console script entry points are correct."""

    def test_entry_points_defined(self):
        """Check that cli and serve scripts are registered."""
        from importlib.metadata import entry_points

        eps = entry_points()
        console_scripts = eps.select(group='console_scripts')
        script_names = {s.name for s in console_scripts}

        assert 'tangl-cli' in script_names
        assert 'tangl-serve' in script_names

    def test_cli_entry_point_loads(self):
        """Verify cli entry point resolves and is callable."""
        from importlib.metadata import entry_points

        eps = entry_points().select(group='console_scripts', name='tangl-cli')
        cli_ep = next(iter(eps))

        # Should be tangl.cli.__main__:main, not tangl.apps.cli...
        assert 'tangl.cli' in cli_ep.value
        assert 'tangl.apps' not in cli_ep.value

        main_func = cli_ep.load()
        assert callable(main_func)

    def test_serve_entry_point_loads(self):
        """Verify serve entry point resolves and is callable."""
        from importlib.metadata import entry_points

        eps = entry_points().select(group='console_scripts', name='tangl-serve')
        serve_ep = next(iter(eps))

        assert 'tangl.rest' in serve_ep.value
        assert 'tangl.apps' not in serve_ep.value

        main_func = serve_ep.load()
        assert callable(main_func)


class TestScriptInvocation:
    """Test that installed scripts actually run."""

    def test_cli_script_exists(self):
        """Verify 'cli' is on PATH."""
        result = subprocess.run(
            ['which', 'tangl-cli'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "cli script not found on PATH"

    @pytest.mark.skip(reason="cmd2 has no command line args")
    def test_cli_help_works(self):
        """Verify 'cli --help' runs without error."""
        result = subprocess.run(
            ['cli', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        # Basic smoke test - should mention tangl or storytangl
        assert 'tangl' in result.stdout.lower() or 'story' in result.stdout.lower()

    def test_cli_module_invocation_fallback(self):
        """Ensure python -m tangl.cli still works."""
        result = subprocess.run(
            [sys.executable, '-m', 'tangl.cli'],
            capture_output=True,
            text=True,
            timeout=2
        )
        assert result.returncode == 0

    def test_serve_script_exists(self):
        """Verify 'serve' is on PATH."""
        result = subprocess.run(
            ['which', 'tangl-serve'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "serve script not found on PATH"

    @pytest.mark.skip(reason="fastapi app has no help func defined")
    def test_serve_help_works(self):
        """Verify 'serve --help' runs without error."""
        result = subprocess.run(
            ['tangl-serve', '--help'],
            capture_output=True,
            text=True,
            timeout=2
        )
        assert result.returncode == 0

    @pytest.mark.skip(reason="fastapi app does not return, needs an info func")
    def test_serve_module_invocation_fallback(self):
        """Ensure python -m tangl.serve still works."""
        result = subprocess.run(
            [sys.executable, '-m', 'tangl.rest'],
            capture_output=True,
            text=True,
            timeout=2
        )
        assert result.returncode == 0