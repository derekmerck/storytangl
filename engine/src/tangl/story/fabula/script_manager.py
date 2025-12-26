from __future__ import annotations
import logging
from collections.abc import Iterator, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any, Self, Optional

from pydantic import ConfigDict, ValidationError

from tangl.core.factory import TemplateFactory
from tangl.core.graph import Node
from tangl.ir.core_ir import BaseScriptItem, MasterScript
from tangl.ir.story_ir import StoryScript
from tangl.ir.story_ir.actor_script_models import ActorScript
from tangl.ir.story_ir.location_script_models import LocationScript
from tangl.ir.story_ir.scene_script_models import BlockScript, SceneScript
from tangl.type_hints import StringMap, UnstructuredData

from tangl.core import Entity
from tangl.story.concepts.actor import Actor
from tangl.story.concepts.location import Location
from tangl.story.episode import Scene

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class ScriptManager(Entity):
    """ScriptManager(master_script: MasterScript | None, template_factory: TemplateFactory)

    Script-to-world coordinator for template lookup and materialization.

    Why
    ----
    Centralizes access to compiled story scripts so world construction and
    traversal helpers can query templates, metadata, and globals consistently.

    Key Features
    ------------
    * **Template factory** – flattens hierarchical script templates for lookups.
    * **Anchored lookup** – ranks templates by proximity to a selector node.
    * **Metadata access** – exposes story metadata and global locals.
    * **Scoped ordering** – prefers scope-aware matches via ``scope_rank``.

    API
    ---
    - :meth:`from_master_script` / :meth:`from_data` – build from script inputs.
    - :meth:`find_template` / :meth:`find_templates` – scoped template searches.
    - :meth:`find_scenes` – scene template discovery.
    - :meth:`get_story_metadata` / :meth:`get_story_globals` – script metadata access.

    Notes
    -----
    Template selection prefers templates closer to the selector node::

        block = graph.get("village.tavern.main")
        guard = manager.find_template("guard", selector=block)

    Without a selector, templates are ranked by pattern specificity::

        guard = manager.find_template("guard")
    """

    master_script: Optional[MasterScript] = None  # for reference
    template_factory: TemplateFactory = TemplateFactory(label="templates")

    model_config = ConfigDict(extra="allow")

    # === CONSTRUCTORS ===

    @classmethod
    def from_master_script(cls, master_script: MasterScript) -> Self:
        factory = TemplateFactory.from_root_templ(master_script)

        manager = cls(
            master_script=master_script,
            template_factory=factory  # Store factory instead of registry
        )
        return manager

    @classmethod
    def from_script(cls, master_script: MasterScript) -> Self:
        return cls.from_master_script(master_script=master_script)

    @classmethod
    def from_data(cls, data: UnstructuredData) -> Self:
        try:
            ms: MasterScript = StoryScript(**data)
        except ValidationError:
            ms = MasterScript(**data)
        # todo: Want to call "on new script" here too.
        return cls.from_master_script(master_script=ms)

    @classmethod
    def from_files(cls, fp: Path) -> Self:
        # todo: implement a file reader
        data = {}
        return cls.from_data(data)

    # === METADATA ===

    def get_story_metadata(self) -> UnstructuredData:
        return self.master_script.metadata.model_dump()

    def get_story_globals(self) -> StringMap:
        if self.master_script.locals is not None:
            return deepcopy(self.master_script.locals)
        return {}

    # === FACTORY SEARCH ===

    # this is just a slightly different api for find-all with sort
    def find_template(
        self,
        identifier: str | None = None,
        selector: Node | None = None,
        **criteria: Any
    ) -> BaseScriptItem | None:
        """Return the first template matching identifier/criteria within scope.

        Args:
            identifier: Template identifier/label to search for.
            selector: Node providing context for scope-aware ranking.
            **criteria: Additional selection criteria.

        Returns:
            Best matching template, or None if no match found.

        Notes:
            When selector is provided, templates are ranked by
            :meth:`~tangl.core.graph.scope_selectable.ScopeSelectable.scope_rank`,
            which prefers templates closer to the selector in the hierarchy.
        """
        sort_key = lambda template: template.scope_specificity(selector)
        qualified = isinstance(identifier, str) and "." in identifier

        if qualified:
            script_label = getattr(self.master_script, "label", None)
            path_candidates = []
            if script_label:
                path_candidates.append(f"{script_label}.{identifier}")
            path_candidates.append(identifier)
            for path_value in path_candidates:
                template = self.template_factory.find_one(
                    sort_key=sort_key,
                    path=path_value,
                    **criteria,
                )
                if template is not None:
                    return template
            if identifier is not None:
                criteria.setdefault("has_identifier", identifier)
            return self.template_factory.find_one(
                sort_key=sort_key,
                **criteria,
            )

        if selector is not None:
            criteria.setdefault("selector", selector)
        if identifier is not None:
            criteria.setdefault("has_identifier", identifier)
        # anchored lookup is just sort by ancestry and then return first
        return self.template_factory.find_one(
            sort_key=sort_key,
            **criteria,
        )

    def find_templates(
        self,
        *,
        identifier: str | None = None,
        selector: Node | None = None,
        **criteria: Any,
    ) -> list[BaseScriptItem]:
        """Return all templates matching identifier/criteria.

        Args:
            identifier: Template identifier/label to search for.
            selector: Node providing context for scope-aware ranking.
            **criteria: Additional selection criteria.

        Returns:
            List of matching templates, sorted by scope rank.

        Notes:
            Results are sorted with most specific/closest templates first.
        """
        sort_key = lambda template: template.scope_specificity(selector)
        results: list[BaseScriptItem] = []
        qualified = isinstance(identifier, str) and "." in identifier

        if qualified:
            script_label = getattr(self.master_script, "label", None)
            path_candidates = []
            if script_label:
                path_candidates.append(f"{script_label}.{identifier}")
            path_candidates.append(identifier)
            seen: set[Any] = set()
            for path_value in path_candidates:
                for template in self.template_factory.find_all(
                    sort_key=sort_key,
                    path=path_value,
                    **criteria,
                ):
                    if template.uid in seen:
                        continue
                    seen.add(template.uid)
                    results.append(template)
            if results:
                return results
            if identifier is not None:
                criteria.setdefault("has_identifier", identifier)
            return list(
                self.template_factory.find_all(
                    sort_key=sort_key,
                    **criteria,
                )
            )

        if selector is not None:
            criteria.setdefault("selector", selector)
        if identifier is not None:
            criteria.setdefault("has_identifier", identifier)
        return list(
            self.template_factory.find_all(
                sort_key=sort_key,
                **criteria,
            )
        )

    # This is similar api to how core.Graph wraps convenience accessors for
    # various sub-types of GraphItem
    def find_scenes(
        self,
        selector: Node | None = None,
        **criteria: Any,
    ) -> Iterator[SceneScript]:
        """Find scene templates.

        Args:
            selector: Optional node for context-aware ranking.
            **criteria: Selection criteria.

        Returns:
            Iterator of matching scene templates.
        """
        criteria.setdefault("is_instance", Scene)
        sort_key = lambda template: template.scope_specificity(selector)
        return iter(
            self.template_factory.find_all(
                sort_key=sort_key,
                **criteria,
            )
        )

    def find_actors(self, **criteria: Any) -> Iterator[ActorScript]:
        criteria.setdefault("is_instance", Actor)
        return self.find_templates(**criteria)

    def find_locations(self, **criteria: Any) -> Iterator[LocationScript]:
        criteria.setdefault("is_instance", Location)
        return self.find_templates(**criteria)

    def find_items(self, **criteria: Any) -> Iterator[BaseScriptItem]:
        """Return item templates if present (defaults to empty)."""
        return iter(())

    def find_flags(self, **criteria: Any) -> Iterator[BaseScriptItem]:
        """Return flag templates if present (defaults to empty)."""
        return iter(())

    # todo: find blocks, actions, roles, settings similarly if useful

    @staticmethod
    def _is_qualified(identifier: str) -> bool:
        """Return ``True`` when identifier includes a scope separator."""

        return "." in identifier

    def _get_scope_chain(self, selector: Node) -> list[str]:
        """Return the selector's scope chain from most specific to global."""

        labels: list[str] = []
        current: Any | None = selector

        while current is not None:
            label = getattr(current, "label", None)
            if isinstance(label, str) and label:
                labels.append(label)
            current = getattr(current, "parent", None)

        labels.reverse()

        paths: list[str] = []
        for index in range(len(labels), 0, -1):
            path = ".".join(labels[:index])
            paths.append(path)

        paths.append("")

        return paths

    # NOTE: _compile_templates() and _register_scoped_templates() were removed.
    # Template registration now happens automatically via:
    # - TemplateFactory.from_root_templ() which calls root_templ.visit()
    # - HierarchicalTemplate.visit() traverses all visit_field=True fields
    # - templates are aliased to BaseScriptItem.children and marked visit_field

    def get_unstructured(self, key: str) -> Iterator[UnstructuredData]:
        if not hasattr(self.master_script, key):
            return

        logger.debug("Starting node data %s", key)
        section = getattr(self.master_script, key)
        if not section:
            return

        # Supposed to carry typing defaults, unnecessary
        # config = None

        if isinstance(section, dict):
            for label, item in section.items():
                payload = self._export_item(item)
                payload.setdefault("label", label)
                self._apply_defaults(key, payload)
                logger.debug(payload)
                yield payload
            return

        for item in section:
            payload = self._export_item(item)
            self._apply_defaults(key, payload)
            logger.debug(payload)
            yield payload


    @classmethod
    def _export_item(
        cls,
        item: Any,
        # config: _DefaultClassConfig | None,
    ) -> dict[str, Any]:
        payload = cls._dump_item(item)
        return payload
        # if config is None:
        #     return payload
        # return cls._apply_default_classes(payload, config)

    @staticmethod
    def _dump_item(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return dict(item)

        if hasattr(item, "model_dump"):
            rebuild = getattr(item.__class__, "model_rebuild", None)
            if callable(rebuild):
                rebuild()
            try:
                payload = item.model_dump(exclude_none=True, exclude_defaults=True)
            except TypeError:
                payload = dict(item.__dict__)

            return {key: value for key, value in payload.items() if value is not None}

        return dict(item)

    @staticmethod
    def _apply_defaults(key: str, payload: dict[str, Any]) -> None:
        if key == "actors":
            obj_cls = payload.get("obj_cls")
            if (
                obj_cls is None
                or (isinstance(obj_cls, type) and issubclass(obj_cls, BaseScriptItem))
            ):
                payload["obj_cls"] = "tangl.story.concepts.actor.actor.Actor"
            return
        if key == "locations":
            obj_cls = payload.get("obj_cls")
            if (
                obj_cls is None
                or (isinstance(obj_cls, type) and issubclass(obj_cls, BaseScriptItem))
            ):
                payload["obj_cls"] = "tangl.story.concepts.location.location.Location"
            return
        if key == "scenes":
            obj_cls = payload.get("obj_cls")
            if (
                obj_cls is None
                or (isinstance(obj_cls, type) and issubclass(obj_cls, BaseScriptItem))
            ):
                payload["obj_cls"] = "tangl.story.episode.scene.Scene"
            blocks = payload.get("blocks")
            if isinstance(blocks, dict):
                for block_label, block in blocks.items():
                    if not isinstance(block, dict):
                        continue
                    block.setdefault("label", block_label)
                    block_cls = block.get("block_cls")
                    if block_cls and "obj_cls" not in block:
                        block["obj_cls"] = block_cls
                    block.setdefault("obj_cls", "tangl.story.episode.block.Block")
                    block.setdefault("block_cls", "tangl.story.episode.block.Block")
                    for edge_key in ("actions", "continues", "redirects"):
                        entries = block.get(edge_key)
                        if not isinstance(entries, list):
                            continue
                        for entry in entries:
                            if isinstance(entry, dict):
                                entry.setdefault(
                                    "obj_cls",
                                    "tangl.story.episode.action.Action",
                                )
    #
    # @classmethod
    # def _apply_default_classes(
    #     cls,
    #     data: dict[str, Any],
    #     config: _DefaultClassConfig,
    # ) -> dict[str, Any]:
    #     payload = dict(data)
    #
    #     class_path = config.class_path
    #     if class_path and not payload.get("obj_cls"):
    #         payload["obj_cls"] = class_path
    #     if config.alias and not payload.get(config.alias):
    #         payload[config.alias] = class_path
    #
    #     if not config.children:
    #         return payload
    #
    #     for field_name, child_config in config.children.items():
    #         value = payload.get(field_name)
    #         if not value:
    #             continue
    #
    #         if isinstance(value, dict):
    #             child_payload: dict[str, dict[str, Any]] = {}
    #             for child_label, child_value in value.items():
    #                 child_dict = cls._dump_item(child_value)
    #                 enriched = cls._apply_default_classes(child_dict, child_config)
    #                 enriched.setdefault("label", child_dict.get("label", child_label))
    #                 child_payload[child_label] = enriched
    #             payload[field_name] = child_payload
    #             continue
    #
    #         if isinstance(value, list):
    #             enriched_list = [
    #                 cls._apply_default_classes(cls._dump_item(child), child_config)
    #                 for child in value
    #             ]
    #             payload[field_name] = enriched_list
    #
    #     return payload

    # def get_story_text(self) -> list[tuple[str, str]]:
    #
    #     result = []
    #
    #     def _get_text_fields(path: str, item: list | dict):
    #         nonlocal result
    #         if not item:
    #             return
    #         if isinstance(item, list) and isinstance( item[0], dict ):
    #             [ _get_text_fields(path + f'.{i}', v) for i, v in enumerate(item) ]
    #         elif isinstance(item, dict):
    #             if 'text' in item:
    #                 data = {"path": path,
    #                         # "hash": key_for_secret(item['text'])[:6],
    #                         "text": item['text']}
    #                 result.append(data)
    #             [ _get_text_fields( path + f'.{k}', v) for k, v in item.items() ]
    #
    #     _get_text_fields(self.master_script.label, self.master_script.model_dump())
    #     return result
