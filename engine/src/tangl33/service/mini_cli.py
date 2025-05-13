from tangl33.core import Graph, Journal, CursorDriver, EdgeKind, Domain
from tangl33.core.graph.edge import ChoiceTrigger
from tangl33.story import register_base_capabilities

import logging
logger = logging.getLogger(__name__)

def display_journal(journal, entries=5):
    """Display the most recent journal entries."""
    for frag in journal[-entries:]:
        print(frag.text)
    print("---")

def get_player_choice(choices):
    """Get player input for available choices."""
    for i, choice in enumerate(choices):
        print(f"{i + 1}. {choice.locals.get('text')}")

    while True:
        try:
            selection = int(input("> ")) - 1
            if 0 <= selection < len(choices):
                return choices[selection]
            print("Invalid choice, try again.")
        except ValueError:
            print("Please enter a number.")

def _collect_choices(graph, node_uid):
    """Return CHOICE edges currently live for *node_uid*."""
    return [e for e in graph.edges_out.get(node_uid, [])
            if getattr(e, "kind", None) is EdgeKind.CHOICE and e.trigger is ChoiceTrigger.MANUAL]

def run_story(entry_node, graph=None, domain=None):
    """Run a minimal story from the given entry node."""
    # graph = graph or Graph()
    if entry_node.uid not in graph:
        graph.add(entry_node)
    domain = domain or Domain()

    # Set up runtime components
    journal = Journal()

    # Create driver
    driver = CursorDriver(graph, domain, journal)
    driver.cursor_uid = entry_node.uid
    logger.debug(f"graph keys: {list(graph.keys())}")
    logger.debug(f"d.graph keys: {list(driver.graph.keys())}")

    # Initialize any global capabilities
    register_base_capabilities()

    # Main loop
    while True:
        # Step the cursor
        cursor_uid = driver.cursor_uid
        journal_len = len(journal)
        driver.step()

        # Show the latest journal entries
        new_entries = len(journal) - journal_len
        display_journal(journal, new_entries)

        # If the cursor did not advance automatically, ask player
        if driver.cursor_uid == cursor_uid:
            choices = _collect_choices(graph, cursor_uid)
            if not choices:
                print("~ End of content ~")
                break
            choice_edge = get_player_choice(choices)
            # advance cursor to the selected destination
            logger.debug("Made choice: %s", choice_edge)
            driver.cursor_uid = choice_edge.dst_uid
            assert choice_edge.dst_uid in driver.graph
            continue          # loop immediately to render next node

        # otherwise, cursor advanced automatically; loop to render next node
