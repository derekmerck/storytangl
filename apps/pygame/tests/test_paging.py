"""Measured local pages preserve ordered backend visuals and gate all action paths."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

pygame = pytest.importorskip("pygame")

from tangl.core import Selector
from tangl.journal.fragments import ChoiceFragment, ContentFragment, MediaFragment
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.persistence import PersistenceManagerFactory
from tangl.prose.naming import NamedActor, ProseBlock, naming_dispatch
from tangl.prose.portraits import HasPortraits, portrait_dispatch
from tangl.pygame_client.__main__ import _apply, _frame, _keyed
from tangl.pygame_client.bridge import PygameSessionBridge
from tangl.pygame_client.models import (
    BeginText, Choice, Commit, Line, MapPlate, MapRegion, PassagePage, ScrollText,
    Piece, StageImage, Surface, SurfaceSlot, TogglePacing, TogglePreference, Turn,
)
from tangl.pygame_client.presentation import visual_passages
from tangl.pygame_client.stage import Stage
from tangl.presentation.intent import TextAccepts
from tangl.presentation.hints import PresentationHints
from tangl.service import ServiceManager
from tangl.service.response import RuntimeEnvelope
from tangl.service.user.user import User
from tangl.service.world_registry import register_manual_world, pop_manual_world
from tangl.story import Action
from tangl.story.fabula.builder import WorldBuilder
from tangl.story.fabula.compiler import StoryCompiler
from tangl.vm import ResolutionPhase

class PagingSpeaker(HasPortraits, NamedActor):
    pass


ROOM = (0, 0, 128)
"""The fixture's first room, solid navy, so any other colour over it is drawn."""


def _washed(stage: Stage, y: int) -> tuple[int, int] | None:
    """The first and last columns drawn over the room on one pixel row."""
    columns = [x for x in range(stage.logical_size[0])
               if tuple(stage.surface.get_at((x, y)))[:3] != ROOM]
    return (columns[0], columns[-1]) if columns else None


@pytest.fixture(params=[1, 2], ids=["320", "640"])
def exchange(request: pytest.FixtureRequest, tmp_path: Path):
    density = request.param
    for name, face in (("base", "yellow"), ("happy", "green"), ("dry", "red")):
        image = pygame.Surface((48 * density, 112 * density))
        image.fill("gray")
        image.fill(face, (8 * density, 8 * density, 32 * density, 24 * density))
        for x in (16, 30):
            image.fill("black", (x * density, 17 * density, 3 * density, 3 * density))
        image.fill("black", (20 * density, 27 * density, 10 * density, density))
        pygame.image.save(image, str(tmp_path / f"{name}.png"))
    for name, colour in (("room1", "navy"), ("room2", "purple")):
        image = pygame.Surface((320 * density, 200 * density))
        image.fill(colour)
        pygame.image.save(image, str(tmp_path / f"{name}.png"))
    resources = ResourceManager(tmp_path)
    resources.index_directory(".")
    portraits = {"default_look": "day", "attitudes": {"happy": "happy", "dry": "dry"},
                 "looks": {"day": {"base": "base.png", "expressions": {
                     "happy": "happy.png", "dry": "dry.png",
                 }}}}
    media = [{"name": "room1.png", "media_role": "narrative_im"}, *[
        {"name": "base.png", "media_role": "avatar_im", "speaker": speaker,
         "staging_hints": {"media_x": x}}
        for speaker, x in (("rin", 0.23), ("kai", 0.77))
    ]]
    classes = {"PagingSpeaker": PagingSpeaker, "ProseBlock": ProseBlock}
    script = {"label": "paging_exchange", "metadata": {
        "start_at": "s.one", "stage_extent": {"width": 320 * density, "height": 200 * density},
        "ui_preferences": [{"id": "pacing", "kind": "enum", "label": "Reading",
                            "values": ["scrolling", "paged"], "default": "paged"}],
    }, "actors": {speaker: {"kind": "PagingSpeaker", "name": speaker, "portraits": portraits}
                   for speaker in ("rin", "kai")}, "scenes": {"s": {
        "roles": {speaker: {"actor_ref": speaker} for speaker in ("rin", "kai")}, "blocks": {
            "one": {"kind": "ProseBlock", "media": media, "prose": [
                {"dialog_class": "rin.happy", "text": "Hello, Kai."},
                {"dialog_class": "rin.happy", "text": "Welcome back."},
                {"dialog_class": "rin.dry", "text": "What happened?"},
                {"dialog_class": "kai.happy", "text": "Follow me."},
            ], "actions": [{"text": "Next", "successor": "two"}]},
            "two": {"kind": "ProseBlock", "media": [{"name": "room2.png",
                "media_role": "narrative_im"}, {"name": "base.png", "media_role": "avatar_im",
                "speaker": "kai", "staging_hints": {"media_x": 0.77}}], "prose": [
                {"dialog_class": "kai.dry", "text": "We are in the second room."},
            ], "actions": [{"text": "Return", "successor": "one"}]},
        }}}}
    bundle = StoryCompiler().compile(script, class_registry=classes)
    world = WorldBuilder().build(label="paging_exchange", bundle=bundle, resources=resources,
                                class_registry=classes,
                                extra_authorities=[naming_dispatch, portrait_dispatch])
    persistence = PersistenceManagerFactory.native_in_mem()
    manager = ServiceManager(persistence)
    register_manual_world(world)
    user = User(label="reader")
    persistence.save(user)
    envelope = manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    bridge = PygameSessionBridge(manager, user_id=user.uid)
    bridge.world_id = world.label
    stage = Stage(logical_size=(320 * density, 200 * density), display_scale=1)
    yield world, manager, user, envelope, bridge, stage
    pop_manual_world(world.label)
    pygame.quit()


def test_an_unstationed_speakers_face_follows_the_preference_its_world_declares(
        tmp_path: Path) -> None:
    # Rin is staged; Mia speaks with no portrait on stage to take staging from.
    # Their world says each line's portrait hides with the `faces` preference,
    # so with faces off neither shows, and with faces on Mia's does, too.
    for name, colour in (("room", "navy"), ("rin", "yellow"), ("mia", "green")):
        image = pygame.Surface((48, 112) if name != "room" else (320, 200))
        image.fill(colour)
        pygame.image.save(image, str(tmp_path / f"{name}.png"))
    resources = ResourceManager(tmp_path)
    resources.index_directory(".")
    hide = {"media_visibility": {"preference_id": "faces", "values": [True]}}
    classes = {"PagingSpeaker": PagingSpeaker, "ProseBlock": ProseBlock}
    script = {"label": "unstationed_faces", "metadata": {
        "start_at": "s.one", "stage_extent": {"width": 320, "height": 200},
        "ui_preferences": [{"id": "faces", "kind": "boolean", "label": "Faces", "default": True}],
    }, "actors": {who: {"kind": "PagingSpeaker", "name": who, "portraits": {
        "default_look": "day", "looks": {"day": {"base": f"{who}.png"}}, "staging_hints": hide,
    }} for who in ("rin", "mia")}, "scenes": {"s": {
        "roles": {who: {"actor_ref": who} for who in ("rin", "mia")}, "blocks": {"one": {
            "kind": ProseBlock, "media": [
                {"name": "room.png", "media_role": "narrative_im"},
                {"name": "rin.png", "media_role": "avatar_im", "speaker": "rin",
                 "staging_hints": {"media_x": 0.25, **hide}}],
            "prose": [{"dialog_class": "rin.happy", "text": "Hello."},
                      {"dialog_class": "mia.happy", "text": "Hi, both of you."}],
            "actions": [{"text": "Next", "successor": "one"}]}}}}}
    world = WorldBuilder().build(
        label="unstationed_faces", class_registry=classes, resources=resources,
        bundle=StoryCompiler().compile(script, class_registry=classes),
        extra_authorities=[naming_dispatch, portrait_dispatch])
    register_manual_world(world)
    try:
        bridge = PygameSessionBridge()
        bridge.discover_preferences(world.label)
        envelope = bridge.start(world.label)
        stage = Stage(logical_size=(320, 200), display_scale=1)
        stage.present(_frame(bridge, envelope), visual_passages(bridge, envelope),
                      media_visibility=bridge.media_visibility())
        (page,) = [page for page in stage.pages
                   if any(Path(i.source).name == "mia.png" for i in page.turn.images)]
        for shown, faces in ((True, {"rin.png", "mia.png"}), (False, set())):
            loaded, _ = stage._resolve_images(page.turn, {"faces": shown})
            assert {Path(i.source).name for i, _ in loaded if i.speaker_id} == faces
    finally:
        pop_manual_world(world.label)


def test_actual_journal_pairs_portraits_groups_compatible_lines_and_exposes_faces(
    exchange, tmp_path: Path,
) -> None:
    world, manager, user, envelope, bridge, stage = exchange
    declarations = bridge.discover_preferences(world.label)
    assert declarations[0].preference_id == "pacing"
    stage.paged = bridge.preferences["pacing"] == "paged"
    passages = visual_passages(bridge, envelope)
    frame = _frame(bridge, envelope)
    assert passages[-1].images == frame.images
    stage.present(frame, passages)
    assert len(stage.pages) == 3
    assert [row.text for row in stage.pages[0].rows] == ["Hello, Kai.", "Welcome back."]
    density = stage.density
    expected = [("happy.png", "base.png"), ("dry.png", "base.png"), ("dry.png", "happy.png")]
    for index, page in enumerate(stage.pages):
        stage.page_index = index
        stage.draw(frame)
        portraits = [image for image in page.turn.images if image.speaker_id]
        assert tuple(Path(image.source).name for image in portraits) == expected[index]
        for x, image in zip((0.23, 0.77), portraits):
            point = (round(x * stage.logical_size[0]), 100 * density)
            expected_colour = {"happy.png": (0, 255, 0), "dry.png": (255, 0, 0),
                               "base.png": (255, 255, 0)}[Path(image.source).name]
            assert tuple(stage.surface.get_at(point))[:3] == expected_colour
            assert point[1] < stage.prose_rect.top - stage.row_height
        assert len(page.rows) <= 4
    stage.page(PassagePage(-1))
    stage.draw(frame)
    assert not stage.choices_ready and _keyed(stage, frame, None, 1) is None
    stage.page(PassagePage(end=True))
    stage.draw(frame)
    assert _keyed(stage, frame, None, 1) == Commit(frame.choices[0].edge_id, {})
    pygame.image.save(stage.window, str(tmp_path / "compact-paged.png"))
    _apply(bridge, stage, frame, None, TogglePacing())
    assert not stage.paged and bridge.preferences["pacing"] == "scrolling"
    _apply(bridge, stage, frame, None, TogglePreference("pacing"))
    assert stage.paged and bridge.preferences["pacing"] == "paged"


def test_page_header_is_washed_to_the_margins_of_the_rows_beneath_it(exchange) -> None:
    # The bar, the speaker and the page's controls, spans exactly the columns
    # the page's text washes over, as the scrolling header does.
    _, _, _, envelope, bridge, stage = exchange
    frame = _frame(bridge, envelope)
    stage.paged = True
    stage.present(frame, visual_passages(bridge, envelope))
    stage.draw(frame)
    pitch = stage.row_height
    assert _washed(stage, stage.prose_rect.top - pitch // 2) \
        == _washed(stage, stage.prose_rect.top + pitch // 2)


def test_a_page_reads_from_just_under_its_bar_however_few_its_rows(exchange) -> None:
    # The first row sits under the bar on every page, so the bar and the text
    # keep one distance as a reader turns them, two rows or one.
    _, _, _, envelope, bridge, stage = exchange
    frame = _frame(bridge, envelope)
    stage.paged = True
    stage.present(frame, visual_passages(bridge, envelope))
    assert [len(page.rows) for page in stage.pages] == [2, 1, 1]
    for index, page in enumerate(stage.pages):
        stage.page_index = index
        stage.draw(frame)
        # The rows' left edge, where no figure stands: washed where a row is.
        left, _ = _washed(stage, stage.prose_rect.top - stage.row_height)
        washed = [tuple(stage.surface.get_at((left, stage.prose_rect.top + row * stage.row_height
                                             + stage.row_height // 2)))[:3] != ROOM
                  for row in range(4)]
        assert washed == [row < len(page.rows) for row in range(4)]


def test_narration_reads_from_the_row_under_the_bar_with_no_blank_speaker_row(exchange) -> None:
    # The speaker shares the bar with the page's controls, so a page nobody
    # speaks on starts its text on the next row, as a dialog page does.
    world, _, _, _, _, stage = exchange
    room = StageImage("narrative_im", str(world.resources.resource_path / "room1.png"))
    first = Turn(step=1, images=[room], lines=[Line("The platform is crowded.")])
    last = Turn(step=2, images=[room], lines=[Line("Somebody waves.")],
                choices=[Choice(uuid4(), "Continue")])
    stage.paged = True
    stage.present(last, [first, last])
    stage.draw(last)
    # Each control's own glyph rectangle, not the whole panel that also advances.
    bar = {rect.y for rect, action in stage.hitboxes
           if isinstance(action, (PassagePage, TogglePacing)) and rect.height <= stage.row_height}
    assert bar == {stage.prose_rect.top - stage.row_height}
    left, _ = _washed(stage, stage.prose_rect.top - stage.row_height)
    assert tuple(stage.surface.get_at((left, stage.prose_rect.top + 1)))[:3] != ROOM


def test_a_one_page_response_draws_every_passage_it_combined(exchange, monkeypatch) -> None:
    # Two passages that fit together make one page. Drawn as it would scroll,
    # that page is the whole frame: the second passage's text is not lost.
    _, _, _, _, _, stage = exchange
    first, second = Line("The first sentence."), Line("The second sentence.")
    frame = Turn(step=1, lines=[first, second], choices=[Choice(uuid4(), "Continue")])
    stage.paged = True
    stage.present(frame, [Turn(step=1, lines=[first]), Turn(step=1, lines=[second])])
    assert len(stage.pages) == 1
    drawn: list[str] = []
    draw_rows = stage._draw_rows
    monkeypatch.setattr(stage, "_draw_rows", lambda rows, **kwargs: (
        drawn.extend(row.text for row in rows), draw_rows(rows, **kwargs)))
    stage.draw(frame)
    assert drawn == ["The first sentence.", "The second sentence."]


def test_nothing_to_page_draws_no_bar_and_keeps_the_whole_menu(exchange) -> None:
    # A plate, an encounter, or a menu that fits on one page has nothing to
    # turn: no bar, no switch, and its choices get the room they get scrolling.
    world, _, _, _, _, stage = exchange
    root = world.resources.resource_path
    choices = [Choice(uuid4(), f"Choice {index}") for index in range(12)]
    plate = Turn(step=1, images=[StageImage("narrative_im", str(root / "room1.png"))],
                 choices=choices[:1])
    menu = Turn(step=1, images=[StageImage("narrative_im", str(root / "room1.png"))],
                lines=[Line("Day 3, morning.")], choices=choices)

    def controls() -> list[object]:
        return [action for _, action in stage.hitboxes
                if isinstance(action, (PassagePage, TogglePacing))]

    capacities = {}
    for paged in (False, True):
        stage.paged = paged
        for turn in (plate, menu):
            stage.present(turn, [turn])
            stage.draw(turn)
            assert controls() == [] and stage.choices_ready
        capacities[paged] = stage.choice_capacity
    assert capacities[True] == capacities[False] > 2


def test_multi_room_batch_does_not_reveal_future_staging_and_skip_matches_fold(exchange) -> None:
    world, manager, user, first, bridge, stage = exchange
    # One actual resolution traverses both blocks, as an authored continuation does.
    with manager.open_session(user_id=user.uid, write_back=True) as session:
        edge = session.ledger.graph.find_one(Selector(has_kind=Action, text="Next"))
        edge.trigger_phase = ResolutionPhase.POSTREQS
        before = session.ledger.step
        session.ledger.get_frame().goto_node(edge.predecessor)
    envelope = manager.get_story_update(user_id=user.uid, since_step=before)
    assert len({item.step for item in envelope.fragments}) >= 2
    passages = visual_passages(bridge, envelope)
    frame = _frame(bridge, envelope)
    assert passages[-1].images == frame.images
    stage.present(frame, passages)
    stage.paged = True
    for index, page in enumerate(stage.pages):
        stage.page_index = index
        stage.draw(frame)
        room = next(image for image in page.turn.images if image.role == "narrative_im")
        second_room = any("second room" in row.text for row in page.rows)
        assert Path(room.source).name == ("room2.png" if second_room else "room1.png")
        assert len([image for image in page.turn.images if image.speaker_id]) == (1 if second_room else 2)
    stage.page(PassagePage(end=True))
    assert stage.pages[stage.page_index].turn.images == frame.images
    stage.page(PassagePage(-len(stage.pages)))
    stage.draw(frame)
    assert Path(next(image for image in stage.pages[0].turn.images
                     if image.role == "narrative_im").source).name == "room1.png"


def test_late_explicit_block_staging_is_applied_before_its_own_text(exchange) -> None:
    _, _, _, envelope, bridge, _ = exchange
    explicit = [item for item in envelope.fragments if isinstance(item, MediaFragment)
                and item.media_role in ("avatar_im", "narrative_im")]
    explicit_ids = {item.uid for item in explicit}
    following_and_text = [item for item in envelope.fragments if item.uid not in explicit_ids]
    late = RuntimeEnvelope(fragments=[*following_and_text, *explicit])
    original = visual_passages(bridge, envelope)
    reordered = visual_passages(bridge, late)
    assert [turn.images for turn in reordered] == [turn.images for turn in original]
    assert [turn.lines for turn in reordered] == [turn.lines for turn in original]


def test_long_body_grouping_and_style_boundaries_use_font_geometry(exchange) -> None:
    _, _, _, _, bridge, stage = exchange
    speaker = uuid4()
    text = ("A long paragraph with complete wording. " * 35) + "\n\n" + "abcdef" * 90
    passages = [Turn(step=1, lines=[Line(text, "Rin", "dialog", speaker_id=speaker)]),
                Turn(step=1, lines=[Line("Narration.")]),
                Turn(step=2, lines=[Line("Another step.")])]
    frame = Turn(step=2, lines=[line for turn in passages for line in turn.lines],
                 choices=[Choice(uuid4(), "Done")])
    stage.present(frame, passages)
    assert "".join("".join(row.text.split()) for page in stage.pages for row in page.rows) == (
        "".join((text + "Narration.Another step.").split())
    )
    assert all(len(page.rows) <= 4 for page in stage.pages)
    assert all(stage.font.size(row.text)[0] <= stage.logical_size[0] - 2 * stage.row_text_left
               for page in stage.pages for row in page.rows)
    assert stage.pages[-2].heading is None and stage.pages[-1].turn.step == 2
    assert stage.paged is False  # no world suggestion preserves scrolling
    _apply(bridge, stage, frame, None, TogglePacing())
    assert stage.paged is True
    stage.present(frame, passages)  # redraw/presentation of the same response is idempotent
    stage.page(PassagePage(end=True))
    stage.present(frame, passages)
    assert stage.choices_ready
    stage.present(frame, passages, fresh=False)
    assert not stage.pages and stage.choices_ready  # readback never replays
    styled = [Turn(step=1, lines=[Line("First", "Rin", speaker_id=speaker,
                                      hints=PresentationHints(style_name="soft"))]),
              Turn(step=1, lines=[Line("Second", "Rin", speaker_id=speaker,
                                      hints=PresentationHints(style_name="strong"))]),
              Turn(step=1, lines=[Line("Third", "Rin", speaker_id=speaker, mode="thought")])]
    stage.present(Turn(step=1), styled)
    assert len(stage.pages) == 3


def test_terminal_menu_and_media_only_output_stay_reachable(exchange) -> None:
    world, _, _, _, _, stage = exchange
    choices = [Choice(uuid4(), f"Choice {index}: " + "long wording " * 16,
                      available=index % 3 != 1, payload={"index": index})
               for index in range(45)]
    root = world.resources.resource_path
    first = Turn(step=1, images=[StageImage("narrative_im", str(root / "room1.png"))],
                 lines=[Line("First room.")])
    last = Turn(step=2, images=[StageImage("narrative_im", str(root / "room2.png"))],
                choices=choices)
    stage.present(last, [first, last])
    stage.paged = True
    assert len(stage.pages) == 2
    assert stage.pages[0].turn.images == first.images
    stage.page(PassagePage(end=True))
    stage.draw(last)
    seen = set()
    while True:
        for rect, action in stage.hitboxes:
            if isinstance(action, Commit):
                assert stage.surface.get_rect().contains(rect)
                seen.add(action.edge_id)
        if stage.choice_scroll == stage.max_choice_scroll:
            break
        stage.scroll_text(ScrollText("choices", 1, page=True))
        stage.draw(last)
    assert seen == {choice.edge_id for choice in choices if choice.available}
    stage.present(Turn(step=3, choices=choices), [])
    assert len(stage.pages) == 1 and stage.choices_ready
    stage.draw(stage._presentation_frame)


def test_an_image_that_cannot_be_drawn_is_captioned_once_and_on_a_map_too(
        exchange, tmp_path: Path, monkeypatch) -> None:
    # A failed image leaves its caption on the page it arrives on, and a page
    # with no text that still stages it does not repeat it. A map footer
    # captions one too, rather than dropping it.
    world, _, _, _, _, stage = exchange
    root = world.resources.resource_path
    room = StageImage("narrative_im", str(root / "room1.png"))
    failed = StageImage("avatar_im", str(tmp_path / "missing.png"), alt_text="A guide waits.")
    frame = Turn(step=3, images=[room, failed], lines=[Line("Last.")],
                 choices=[Choice(uuid4(), "Continue")])
    stage.paged = True
    stage.present(frame, [Turn(step=1, images=[room, failed], lines=[Line("First.")]),
                          Turn(step=2, images=[room, failed]),
                          Turn(step=3, images=[room, failed], lines=[Line("Last.")])])
    captions: list[str] = []
    rows = stage._rows

    def spy(*args, **kwargs):
        found = rows(*args, **kwargs)
        captions.extend(row.text for row in found if row.kind == "alt")
        return found

    monkeypatch.setattr(stage, "_rows", spy)
    shown = []
    for index, page in enumerate(stage.pages):
        stage.page_index = index
        captions.clear()
        stage.draw(frame)
        shown.append(bool(captions) or any(row.kind == "alt" for row in page.rows))
    assert shown.count(True) == 1

    plate = StageImage("map_im", str(root / "room1.png"))
    choice = Choice(uuid4(), "Go there", tags=frozenset({"ui:plate:test:place"}))
    atlas = Turn(step=4, images=[plate, failed], choices=[choice],
                 plate=MapPlate("test", plate.source, (MapRegion("place", .1, .1, .2, .2),)))
    stage.paged = False
    stage.present(atlas, [atlas])
    captions.clear()
    stage.draw(atlas)
    assert captions == ["A guide waits."]


def test_a_step_that_only_lays_a_piece_down_keeps_its_page(exchange) -> None:
    # A step with no text and no new image can still put something before the
    # reader -- a card on the desk. It keeps a page of its own, so the card
    # does not appear on the narration before it.
    world, _, _, _, _, stage = exchange
    room = StageImage("narrative_im", str(world.resources.resource_path / "room1.png"))
    card = Piece("card", "id_card", "Card")
    frame = Turn(step=2, images=[room], pieces=[card], choices=[Choice(uuid4(), "Continue")])
    stage.paged = True
    stage.present(frame, [Turn(step=1, images=[room], lines=[Line("A desk.")]),
                          Turn(step=2, images=[room], pieces=[card])])
    assert [page.turn.pieces for page in stage.pages] == [[], [card]]


def test_maps_and_typed_choices_are_gated_until_end(exchange) -> None:
    world, _, _, _, bridge, stage = exchange
    image = StageImage(role="map_im", source=str(world.resources.resource_path / "room1.png"))
    choice = Choice(uuid4(), "Describe the place", accepts=TextAccepts(),
                    tags=frozenset({"ui:plate:test:place"}))
    frame = Turn(step=2, images=[image], choices=[choice],
                 plate=MapPlate("test", image.source, (MapRegion("place", .1, .1, .2, .2),)))
    stage.present(frame, [Turn(step=i, images=[image], lines=[Line(f"Passage {i}")])
                          for i in (1, 2)])
    stage.paged = True
    stage.draw(frame)
    assert _keyed(stage, frame, None, 1) is None
    assert not any(isinstance(action, (Commit, BeginText)) for _, action in stage.hitboxes)
    assert _apply(bridge, stage, frame, None, BeginText(choice)) == (None, None)
    stage.page(PassagePage(end=True))
    stage.draw(frame)
    assert _keyed(stage, frame, None, 1) == BeginText(choice)
    assert any(isinstance(action, BeginText) for _, action in stage.hitboxes)
    surface_frame = replace(frame, plate=None, images=[], pieces=[Piece("card", "id_card", "Card")],
                            surface=Surface("desk", band=(0, .45, 1, .55), slots=(
                                SurfaceSlot("card", "id_card", .1, .5, .3, .4),
                            )))
    stage.present(surface_frame, [Turn(step=i, lines=[Line(f"Passage {i}")]) for i in (1, 2)])
    stage.draw(surface_frame)
    assert not any(isinstance(action, BeginText) for _, action in stage.hitboxes)
    stage.page(PassagePage(end=True))
    stage.draw(surface_frame)
    assert stage.slot_boxes and stage.prose_rect.bottom <= stage.prose_floor
    editor, envelope = _apply(bridge, stage, surface_frame, None, BeginText(choice))
    assert envelope is None
    stage.draw(surface_frame, editor)
    assert stage.surface.get_rect().contains(editor.field_rect)


def test_back_redraw_switch_and_readback_do_not_requeue_audio_or_advance(exchange) -> None:
    _, manager, user, envelope, bridge, stage = exchange

    class MusicCounter:
        def __init__(self):
            self.calls = []

        def synchronize(self, *_args, **kwargs):
            self.calls.append(kwargs)

        def close(self):
            pass

    class VoiceCounter:
        def __init__(self):
            self.calls = []

        def present(self, *_args, **kwargs):
            self.calls.append(kwargs)

        def close(self):
            pass

    music, voice = MusicCounter(), VoiceCounter()
    bridge.music_player, bridge.voice_player = music, voice
    bridge._sync(envelope, opening=True)
    frame = _frame(bridge, envelope)
    stage.present(frame, visual_passages(bridge, envelope))
    for action in (TogglePacing(), PassagePage(), PassagePage(-1), PassagePage(end=True),
                   TogglePacing(), TogglePacing()):
        _apply(bridge, stage, frame, None, action)
        stage.draw(frame)
        stage.draw(frame)
    assert len(music.calls) == len(voice.calls) == 1
    assert music.calls == [{"live": False}] and voice.calls == [{"fresh": True}]
    readback = bridge.refresh()
    stage.present(_frame(bridge, readback), [], fresh=False)
    assert not stage.pages
    assert music.calls[-1] == {"live": False} and voice.calls[-1] == {"fresh": False}
    assert readback.step == envelope.step
    assert readback.to_dto()["fragments"] == envelope.to_dto()["fragments"]


@pytest.mark.parametrize("with_prose", [False, True], ids=["media-only", "with-prose"])
@pytest.mark.parametrize("source", ["missing-url", "bad-file"])
def test_failed_media_text_floor_is_measured_once_in_its_passage(
    exchange, tmp_path: Path, source: str, with_prose: bool,
) -> None:
    _, _, _, _, bridge, stage = exchange
    caption = "A smiling guide waits beside the door. " * 70
    bad = tmp_path / "unreadable.png"
    bad.write_text("not image bytes")
    media = MediaFragment(
        content="https://example.invalid/guide.png" if source == "missing-url" else bad,
        content_format="url" if source == "missing-url" else "path",
        content_type="image", media_role="avatar_im", text=caption,
        source_id=uuid4(), step=1,
    )
    fragments = [media]
    if with_prose:
        fragments.extend([ContentFragment(content="First passage.", source_id=media.source_id, step=1),
                          ContentFragment(content="Next passage.", source_id=media.source_id, step=1)])
    fragments.append(ChoiceFragment(text="Continue", edge_id=uuid4(), step=1))
    envelope = RuntimeEnvelope(fragments=fragments)
    frame = _frame(bridge, envelope)
    passages = visual_passages(bridge, envelope)
    stage.present(frame, passages)
    stage.paged = True
    wording = " ".join(row.text for page in stage.pages for row in page.rows)
    expected = f"First passage. {caption} Next passage." if with_prose else caption
    assert "".join(wording.split()) == "".join(expected.split())
    assert all(len(page.rows) <= 4 for page in stage.pages)
    assert all(stage.font.size(row.text)[0] <= stage.logical_size[0] - 2 * stage.row_text_left
               for page in stage.pages for row in page.rows)
    assert len(stage.pages) > 1 and not stage.choices_ready
    assert _keyed(stage, frame, None, 1) is None
    measured = [[(row.text, row.kind) for row in page.rows] for page in stage.pages]
    for index in (1, 0, len(stage.pages) - 1, 1):
        stage.page_index = index
        stage.draw(frame)
        stage.draw(frame)
        _apply(bridge, stage, frame, None, TogglePacing())
        stage.draw(frame)
        _apply(bridge, stage, frame, None, TogglePacing())
        stage.present(frame, passages)
        assert stage.page_index == index
        assert [[(row.text, row.kind) for row in page.rows] for page in stage.pages] == measured
        for mode in ("scrolling", "paged"):
            stage.present(frame, passages, media_visibility={"pacing": mode})
            assert stage.page_index == index
            assert [[(row.text, row.kind) for row in page.rows] for page in stage.pages] == measured
    stage.page(PassagePage(end=True))
    stage.draw(frame)
    assert isinstance(_keyed(stage, frame, None, 1), Commit)
    _, failed = stage._resolve_images(frame, {})
    scrolling = stage._rows(frame, failed, pixel_width=stage.logical_size[0] - 2 * stage.row_text_left)
    assert "".join(row.text.replace(" ", "") for row in scrolling if row.kind == "alt") == (
        caption.replace(" ", "")
    )


def test_short_media_only_floor_and_hidden_media_follow_existing_resolution(exchange) -> None:
    _, _, _, _, bridge, stage = exchange
    media = MediaFragment(content="https://example.invalid/guide.png", content_format="url",
                          content_type="image", media_role="avatar_im", text="A smiling guide.",
                          staging_hints={"media_visibility": {
                              "preference_id": "portraits", "values": [True],
                          }}, step=1)
    envelope = RuntimeEnvelope(fragments=[media])
    frame = _frame(bridge, envelope)
    passages = visual_passages(bridge, envelope)
    stage.present(frame, passages, media_visibility={"portraits": False})
    stage.paged = True
    stage.draw(frame, media_visibility={"portraits": False})
    assert not any(page.rows for page in stage.pages)
    stage.present(frame, passages, media_visibility={"portraits": True})
    assert [row.text for page in stage.pages for row in page.rows] == ["A smiling guide."]
    stage.present(frame, passages, media_visibility={"portraits": False})
    assert not any(page.rows for page in stage.pages)
    stage.present(replace(frame), [], media_visibility={"portraits": True})
    assert [row.text for page in stage.pages for row in page.rows] == ["A smiling guide."]
