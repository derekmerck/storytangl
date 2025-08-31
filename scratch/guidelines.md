# StoryTangl Project Guidelines

## Project Overview

StoryTangl is an Abstract Narrative Graph Library for Interactive Fiction. It provides a framework for creating, managing, and navigating interactive stories by representing them as abstract graphs that "collapse" into linear narratives based on user or system choices.

### Core Concepts

StoryTangl separates narrative concerns into four distinct layers:

1. **Story World** - The domain of possibility that houses templates, logic, and constraints shaping potential narratives
2. **Story Graph (ANG)** - The semantic instance representing nodes (scenes, characters, items) and edges (relationships, triggers)
3. **Story Navigator** - The component that traverses the graph to produce particular sequences of events
4. **Story Representer** - The presentation layer that converts the story line into concrete output (text, images, audio, etc.)

### Key Features

- **Flexible Story Structure**: Supports traditional linear novels, branching choose-your-own-adventures, sandbox RPGs, and beyond
- **Storydown DSL**: A Markdown+YAML hybrid domain-specific language for authoring interactive stories
- **Transformation Pipeline**: Processes from source input through parsing, compilation, instantiation, and presentation
- **Multi-World Server**: Can host multiple story worlds simultaneously and manage multiple user sessions
- **Extensible Architecture**: Designed with loose coupling to allow for various implementations and extensions

### Use Cases

- **Single Story Apps**: Load, compile, create, navigate, and render individual stories
- **Multi-World Servers**: Serve many distinct story worlds simultaneously with multiple user sessions
- **Linear or Single-Path**: Straightforward compilation for ebook-like or static website experiences
- **Classic CYOA**: Handcrafted branching for discrete forks leading to unique outcomes
- **Sandbox RPG**: Large dynamic graphs with side quests, concurrency, and advanced state logic

## Project Structure

### Main Components

- **tangl/**: Core package containing all framework code
  - **apps/**: Application entry points (CLI and REST API)
  - **business/**: Core business logic
    - **content/**: Content generation and management
    - **core/**: Core domain models and logic
    - **mechanics/**: Game mechanics and interaction rules
    - **story/**: Story graph implementation
    - **world/**: Story world management
  - **data/**: Data storage and retrieval
  - **service/**: Service layer components
  - **utils/**: Utility functions and helpers

### Story World Structure

Story worlds follow this organization:
- **config.toml**: Configuration file with metadata and resource paths
- **resources/**: Directory containing assets and content
  - **script.yaml**: Story script defining scenes, actors, locations, and content blocks
  - **media/**: Directory for images, audio, and other media assets

## Development Workflow

### Setting Up the Environment

1. Install Python 3.11 or higher
2. Install Poetry: `pip install poetry`
3. Install dependencies: `poetry install`
4. Activate virtual environment: `poetry shell`

### Running the Application

- CLI mode: `poetry run cli`
- Server mode: `poetry run serve`
- Build documentation: `poetry run docs`

### Running Tests

- Run all tests: `pytest`
- Run specific test file: `pytest tests/path/to/test_file.py`
- Run with coverage: `pytest --cov --cov-report=html`
- View coverage report: Open `html_cov/index.html` in a browser

## Best Practices

### Code Organization

- Follow the established package structure
- Keep related functionality in appropriate modules
- Use type hints for better code clarity

### Story World Development

- Create a new directory for each story world
- Configure story worlds using config.toml
- Define story content in YAML format
- Store media assets in the media directory
- Use templating syntax for dynamic content

### Testing

- Write tests for all new functionality
- Organize tests to mirror the package structure
- Use fixtures from conftest.py for common test setup
- Aim for high test coverage

### Version Control

- Make atomic commits with clear messages
- Create feature branches for new functionality
- Submit pull requests for code review
- Keep the main branch stable
