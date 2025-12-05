"""Tests for :class:`~tangl.story.episode.menu_block.MenuBlock`."""

from tangl.vm import Affordance, Dependency, Frame, ProvisioningPolicy, Requirement
from tangl.vm import ResolutionPhase as P
from tangl.story.episode import Action, Block, MenuBlock, Scene
from tangl.journal.discourse import ChoiceFragment
from tangl.story.story_graph import StoryGraph


class TestMenuBlockDependencies:
    """Pull pattern: menu creates dependencies during PLANNING."""

    def test_creates_dependencies_for_matching_blocks(self):
        """MenuBlock creates dependencies for blocks matching ``selection_criteria``."""

        graph = StoryGraph(label="test")

        menu = MenuBlock(graph=graph, label="lobby", selection_criteria={"has_tags": {"shop"}})

        shop1 = Block(graph=graph, label="clothing", tags={"shop"})
        shop2 = Block(graph=graph, label="food", tags={"shop"})
        Block(graph=graph, label="parking", tags={"parking"})

        frame = Frame(graph=graph, cursor_id=menu.uid)
        frame.run_phase(P.PLANNING)

        dependencies = list(graph.find_edges(source_id=menu.uid, is_instance=Dependency))
        assert len(dependencies) == 2

        dep_targets = {dep.destination.uid for dep in dependencies}
        assert shop1.uid in dep_targets
        assert shop2.uid in dep_targets

    def test_respects_within_scene_flag(self):
        """MenuBlock with ``within_scene=True`` only targets members of the same scene."""

        graph = StoryGraph(label="test")

        scene = Scene(graph=graph, label="scene1", member_ids=[])
        menu = MenuBlock(
            graph=graph,
            label="lobby",
            selection_criteria={"has_tags": {"shop"}},
            within_scene=True,
        )

        local_shop = Block(graph=graph, label="local", tags={"shop"})
        Block(graph=graph, label="remote", tags={"shop"})

        scene.member_ids = [menu.uid, local_shop.uid]

        frame = Frame(graph=graph, cursor_id=menu.uid)
        frame.run_phase(P.PLANNING)

        dependencies = list(graph.find_edges(source_id=menu.uid, is_instance=Dependency))
        assert len(dependencies) == 1
        assert dependencies[0].destination.uid == local_shop.uid

    def test_skips_blocks_with_existing_actions(self):
        """MenuBlock does not create dependencies when an action already exists."""

        graph = StoryGraph(label="test")
        menu = MenuBlock(graph=graph, label="lobby", selection_criteria={"has_tags": {"shop"}})
        shop = Block(graph=graph, label="shop", tags={"shop"})

        Action(graph=graph, source_id=menu.uid, destination_id=shop.uid, label="Visit shop")

        frame = Frame(graph=graph, cursor_id=menu.uid)
        frame.run_phase(P.PLANNING)

        dependencies = list(graph.find_edges(source_id=menu.uid, is_instance=Dependency))
        assert len(dependencies) == 0

    def test_auto_provision_false_disables_dependencies(self):
        """MenuBlock with ``auto_provision=False`` behaves like a normal block."""

        graph = StoryGraph(label="test")
        menu = MenuBlock(
            graph=graph,
            label="lobby",
            selection_criteria={"has_tags": {"shop"}},
            auto_provision=False,
        )

        Block(graph=graph, label="shop", tags={"shop"})

        frame = Frame(graph=graph, cursor_id=menu.uid)
        frame.run_phase(P.PLANNING)

        dependencies = list(graph.find_edges(source_id=menu.uid, is_instance=Dependency))
        assert len(dependencies) == 0


class TestMenuBlockActionMaterialization:
    """UPDATE phase: converting dependencies and affordances into actions."""

    def test_materializes_actions_from_dependencies(self):
        """MenuBlock converts satisfied dependencies to :class:`Action` edges."""

        graph = StoryGraph(label="test")
        menu = MenuBlock(graph=graph, label="lobby", selection_criteria={"has_tags": {"shop"}})
        shop = Block(graph=graph, label="shop", tags={"shop"}, locals={"action_text": "Visit the shop"})

        frame = Frame(graph=graph, cursor_id=menu.uid)
        frame.run_phase(P.PLANNING)
        frame.run_phase(P.UPDATE)

        actions = list(
            graph.find_edges(
                source_id=menu.uid,
                destination_id=shop.uid,
                is_instance=Action,
            )
        )
        assert len(actions) == 1
        assert actions[0].content == "Visit the shop"
        assert "dynamic" in actions[0].tags
        assert "menu" in actions[0].tags

    def test_materializes_actions_from_affordances(self):
        """MenuBlock converts incoming affordances to :class:`Action` edges."""

        graph = StoryGraph(label="test")
        menu = MenuBlock(graph=graph, label="lobby", selection_criteria={})
        parking = Block(graph=graph, label="parking", locals={"action_text": "Go to parking"})

        requirement = Requirement(
            graph=graph,
            identifier=parking.uid,
            policy=ProvisioningPolicy.EXISTING,
        )
        requirement.provider = parking

        Affordance(
            graph=graph,
            source_id=parking.uid,
            destination_id=menu.uid,
            requirement=requirement,
            label="parking_affordance",
        )

        frame = Frame(graph=graph, cursor_id=menu.uid)
        frame.run_phase(P.PLANNING)
        frame.run_phase(P.UPDATE)

        actions = list(
            graph.find_edges(
                source_id=menu.uid,
                destination_id=parking.uid,
                is_instance=Action,
            )
        )
        assert len(actions) == 1
        assert actions[0].content == "Go to parking"
        assert "affordance" in actions[0].tags

    def test_clears_stale_dynamic_actions(self):
        """MenuBlock clears prior dynamic actions before recreating them."""

        graph = StoryGraph(label="test")
        menu = MenuBlock(graph=graph, label="lobby", selection_criteria={"has_tags": {"shop"}})
        Block(graph=graph, label="shop", tags={"shop"})

        frame = Frame(graph=graph, cursor_id=menu.uid)
        frame.run_phase(P.PLANNING)
        frame.run_phase(P.UPDATE)

        actions_after_first = list(
            graph.find_edges(
                source_id=menu.uid,
                is_instance=Action,
                has_tags={"dynamic", "menu"},
            )
        )
        assert len(actions_after_first) == 1
        first_action_uid = actions_after_first[0].uid

        frame.run_phase(P.PLANNING)
        frame.run_phase(P.UPDATE)

        actions_after_second = list(
            graph.find_edges(
                source_id=menu.uid,
                is_instance=Action,
                has_tags={"dynamic", "menu"},
            )
        )
        assert len(actions_after_second) == 1
        assert actions_after_second[0].uid != first_action_uid

    def test_avoids_duplicate_actions_from_both_patterns(self):
        """Dependency + affordance targeting the same block yield one action."""

        graph = StoryGraph(label="test")
        menu = MenuBlock(graph=graph, label="lobby", selection_criteria={"has_tags": {"shop"}})
        shop = Block(graph=graph, label="shop", tags={"shop"})

        requirement = Requirement(
            graph=graph,
            identifier=shop.uid,
            policy=ProvisioningPolicy.EXISTING,
        )
        requirement.provider = shop

        Affordance(
            graph=graph,
            source_id=shop.uid,
            destination_id=menu.uid,
            requirement=requirement,
            label="shop_affordance",
        )

        frame = Frame(graph=graph, cursor_id=menu.uid)
        frame.run_phase(P.PLANNING)
        frame.run_phase(P.UPDATE)

        actions = list(
            graph.find_edges(
                source_id=menu.uid,
                destination_id=shop.uid,
                is_instance=Action,
            )
        )
        assert len(actions) == 1


class TestMenuBlockSceneIntegration:
    """Integration with scenes and canonical entry points."""

    def test_links_to_scene_source_not_scene_itself(self):
        """MenuBlock navigates to ``scene.source`` when targeting a :class:`Scene`."""

        graph = StoryGraph(label="test")
        menu = MenuBlock(
            graph=graph,
            label="chapter_menu",
            selection_criteria={"is_instance": Scene},
            within_scene=False,
        )

        scene = Scene(graph=graph, label="tavern_scene", member_ids=[])

        frame = Frame(graph=graph, cursor_id=menu.uid)
        frame.run_phase(P.PLANNING)
        frame.run_phase(P.UPDATE)

        actions = list(graph.find_edges(source_id=menu.uid, is_instance=Action))
        assert len(actions) == 1
        assert actions[0].destination_id == scene.source.uid
        assert actions[0].destination_id != scene.uid


class TestMenuBlockJournaling:
    """Ensure dynamic actions render through block journaling handlers."""

    def test_renders_dynamic_choices_via_block_handlers(self):
        """MenuBlock uses :meth:`Block.get_choices` during JOURNAL rendering."""

        graph = StoryGraph(label="test")
        menu = MenuBlock(
            graph=graph,
            label="lobby",
            content="Welcome to the mall.",
            selection_criteria={"has_tags": {"shop"}},
        )
        Block(graph=graph, label="shop", tags={"shop"}, locals={"action_text": "Browse the shop"})

        frame = Frame(graph=graph, cursor_id=menu.uid)
        frame.run_phase(P.PLANNING)
        frame.run_phase(P.UPDATE)
        fragments = frame.run_phase(P.JOURNAL)
        choice_fragments = [fragment for fragment in fragments if isinstance(fragment, ChoiceFragment)]

        assert choice_fragments
        assert "Browse the shop" in [fragment.content for fragment in choice_fragments]


class TestMenuBlockHelperMethods:
    """Unit coverage for MenuBlock helper methods."""

    def test_get_action_label_precedence(self):
        """``_get_action_label`` prefers ``action_text`` then ``menu_text`` then the label."""

        graph = StoryGraph(label="test")
        menu = MenuBlock(graph=graph, label="menu", selection_criteria={})

        block1 = Block(graph=graph, label="default", locals={"action_text": "Custom action"})
        assert menu._get_action_label(block1) == "Custom action"

        block2 = Block(graph=graph, label="default", locals={"menu_text": "Menu text"})
        assert menu._get_action_label(block2) == "Menu text"

        block3 = Block(graph=graph, label="just_label")
        assert menu._get_action_label(block3) == "just_label"
