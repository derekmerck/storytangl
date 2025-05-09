from tangl33.core import Requirement, Graph, EdgeKind, Template
from tangl33.story import StoryNode, CharacterStrategy, Domain
from tangl33.service.mini_cli import run_story

def create_sample_story():
    """Create a tiny sample story to test the system."""
    # Create nodes
    start = StoryNode(label="start", locals={"text": "You stand at a crossroads."})
    forest = StoryNode(label="forest", locals={"text": "The forest is dark and foreboding."})
    village = StoryNode(label="village", locals={"text": "A small village comes into view."})

    # Requirements
    village.requires = {
        Requirement("character",
                    strategy=CharacterStrategy(),
                    params={"template": "villager"},
                    criteria={"role": "elder"})
    }

    # Create a graph and add nodes
    graph = Graph()
    for node in [start, forest, village]:
        graph.add(node)

    # Link nodes
    graph.link(start, forest, EdgeKind.CHOICE, text="Enter the forest")
    graph.link(start, village, EdgeKind.CHOICE, text="Go to the village")

    # Create domain with templates
    domain = Domain()
    domain.character_templates = {
        "villager": Template(
            provides={"character"},
            build=lambda params: StoryNode(
                label="villager",
                locals={"name": "Elder Tom", "role": "elder"}
            )
        )
    }

    return start, domain

def main():
    """Run the StoryTangl proof of concept."""
    print("StoryTangl Proof of Concept")
    print("============================")

    # Create the sample story
    start_node, domain = create_sample_story()

    # Run the story
    run_story(start_node, domain)


if __name__ == "__main__":
    main()
