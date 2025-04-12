"""
Strategy Handlers

This module implements a flexible, MRO- and domain-aware plugin system for Python applications.
It provides a mechanism for defining, registering, and executing hooks with priority ordering and
MRO- and domain-specific behaviors.

Key Features:
- Task-based plugin architecture
- Inherited hook discovery
- Domain-specific hooks
- Priority-based execution ordering
- Support for various execution modes (e.g., return first, return all, merge results, iterate)
- Decorator-based strategy registration
- Singleton pattern for domain strategy management
- Caching of strategy collection for improved performance

Core Components:
1. Entity: Base class for objects that can be processed by the plugin system
2. StrategyHandler: Base class and utility for defining tasks and managing their execution
3. DomainStrategyManager: Singleton class for managing domain-specific strategies
4. StrategyRegistry: Base class for strategy registration and storage

Execution Flow:
1. Strategies are registered using decorators or explicit registration methods
2. Tasks are executed through the StrategyHandler.execute_task method
3. Relevant domain strategies are merged with MRO strategies before execution
4. Hooks are called in priority order with support for various return modes

Usage:
1. Define your tasks by subclassing Entity and using the @StrategyHandler.strategy decorator
2. Implement domain-specific plugins using the @DomainStrategyManager.strategy decorator
3. Execute tasks using StrategyHandler.execute_task(entity, 'task_name', result_mode='desired_mode')

Considerations:
- Thread Safety: The current implementation is not guaranteed to be thread-safe.
  Consider adding synchronization if used in a multi-threaded environment.
- Dependency Injection: The current design doesn't include a dependency injection system.
  This could be a valuable addition for managing complex plugin dependencies.

This plugin system provides flexibility and ease of use, making it suitable for
applications where extensible behavior is desired. It combines the power of Python's
method resolution order (MRO) with a domain-specific plugin system, allowing for
highly customizable and context-aware behavior.
"""
# todo: spec/impl type checking, and automatic "on_task" decorator creation from "on_task_spec" functions

from .strategy_handler import StrategyHandler, DomainStrategyManager
