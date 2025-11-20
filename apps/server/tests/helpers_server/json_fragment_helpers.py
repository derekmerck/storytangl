
def extract_choices_from_fragments(fragments: list[dict]) -> list[dict]:
    """Extract all choice fragments from a fragment stream."""

    choices: list[dict] = []

    def _normalize(choice: dict) -> dict:
        normalized = dict(choice)
        if "source_id" in normalized:
            normalized["uid"] = normalized["source_id"]
        elif "uid" in normalized:
            normalized["uid"] = normalized["uid"]
        if "source_label" in normalized and not normalized.get("label"):
            normalized["label"] = normalized["source_label"]
        return normalized

    for fragment in fragments:
        if fragment.get("fragment_type") == "block":
            embedded = fragment.get("choices", [])
            choices.extend(_normalize(choice) for choice in embedded)
        elif fragment.get("fragment_type") == "choice":
            choices.append(_normalize(fragment))

    return choices

