from tangl33.core import Graph, HandlerCache, ProviderRegistry, Journal, CursorDriver
from tangl33.story import Domain

def display_journal(journal, entries=-5):
    """Display the most recent journal entries."""
    for frag in journal[-entries:]:
        print(frag.text)
    print("---")

def get_player_choice(choices):
    """Get player input for available choices."""
    for i, choice in enumerate(choices):
        print(f"{i + 1}. {choice.text}")

    while True:
        try:
            selection = int(input("> ")) - 1
            if 0 <= selection < len(choices):
                return choices[selection]
            print("Invalid choice, try again.")
        except ValueError:
            print("Please enter a number.")

def run_story(entry_node, domain=None):
    """Run a minimal story from the given entry node."""
    graph = Graph()
    graph.add(entry_node)
    domain = domain or Domain()

    # Set up runtime components
    cap_cache = HandlerCache()
    prov_reg = ProviderRegistry()
    journal = Journal()

    # Create driver
    driver = CursorDriver(graph, cap_cache, prov_reg, domain, journal)
    driver.cursor_uid = entry_node.uid

    # Initialize any global capabilities
    register_base_capabilities(cap_cache)

    # Main loop
    while True:
        # Step the cursor
        driver.step()

        # Show the latest journal entries
        display_journal(journal)

        # Get player input if needed
        if not driver.auto_advance:
            choice = get_player_choice(driver.available_choices)
            driver.choose(choice)
