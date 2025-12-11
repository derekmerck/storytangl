"""
Fragment extraction helpers for test assertions.

Understands the hierarchical structure of journal entries:
- Loose fragments (content, media, etc.) at the top level
- BlockFragments containing embedded choice fragments
- Other potential container types (dialog groups, etc.)

Usage in tests:
    fragments = frame.run_phase(P.JOURNAL)
    
    # Extract all choices (both loose and from blocks)
    choices = extract_fragments(fragments, "choice")
    
    # Extract only block fragments
    blocks = extract_fragments(fragments, "block")
    
    # Extract choices from a specific block
    block_choices = extract_choices_from_block(blocks[0])
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tangl.core import BaseFragment


def extract_fragments(
    fragments: list[BaseFragment],
    fragment_type: str,
    recurse: bool = True
) -> list[BaseFragment]:
    """
    Extract fragments of a given type from journal entry stream.
    
    This is the atomic-block-aware replacement for the old `_by_fragment_type`.
    
    Parameters
    ----------
    fragments : list[BaseFragment]
        The journal entry fragment stream
    fragment_type : str
        The fragment type to extract (e.g., "choice", "block", "content", "media")
    recurse : bool, default=True
        If True, recursively search inside container fragments like BlockFragment
        
    Returns
    -------
    list[BaseFragment]
        All fragments of the requested type, in order of discovery
        
    Examples
    --------
    >>> # Get all choices, including those embedded in blocks
    >>> all_choices = extract_fragments(fragments, "choice")
    >>> 
    >>> # Get only top-level content (not embedded)
    >>> loose_content = extract_fragments(fragments, "content", recurse=False)
    """
    result = []
    
    for fragment in fragments:
        # Direct match at this level
        if hasattr(fragment, 'fragment_type') and fragment.fragment_type == fragment_type:
            result.append(fragment)
        
        # Recurse into container types if requested
        if recurse:
            # BlockFragment contains choices
            if (hasattr(fragment, 'fragment_type') and 
                fragment.fragment_type == "block" and 
                hasattr(fragment, 'choices') and 
                fragment.choices):
                # Recursively extract from embedded choices
                result.extend(extract_fragments(fragment.choices, fragment_type, recurse=True))
            
            # Future: DialogFragment might contain speaker/utterance fragments
            # Future: CardFragment might contain media/text children
            # Add other container types here as they emerge
    
    return result


def extract_choices_from_block(block_fragment: BaseFragment) -> list[BaseFragment]:
    """
    Extract choice fragments from a BlockFragment.
    
    Parameters
    ----------
    block_fragment : BaseFragment
        A fragment with fragment_type="block"
        
    Returns
    -------
    list[BaseFragment]
        The embedded choice fragments, or empty list if none
        
    Examples
    --------
    >>> blocks = extract_fragments(fragments, "block")
    >>> if blocks:
    ...     choices = extract_choices_from_block(blocks[0])
    """
    if (hasattr(block_fragment, 'fragment_type') and 
        block_fragment.fragment_type == "block" and
        hasattr(block_fragment, 'choices')):
        return block_fragment.choices or []
    return []


def extract_all_choices(fragments: list[BaseFragment]) -> list[BaseFragment]:
    """
    Convenience function to extract all choice fragments from entry stream.
    
    Equivalent to `extract_fragments(fragments, "choice", recurse=True)`.
    
    This is the drop-in replacement for:
        `_by_fragment_type(fragments, "choice")`
        
    Parameters
    ----------
    fragments : list[BaseFragment]
        The journal entry fragment stream
        
    Returns
    -------
    list[BaseFragment]
        All choice fragments, including those embedded in blocks
    """
    return extract_fragments(fragments, "choice", recurse=True)


def extract_blocks_with_choices(fragments: list[BaseFragment]) -> list[tuple[BaseFragment, list[BaseFragment]]]:
    """
    Extract blocks and their associated choices as pairs.
    
    Useful for assertions about block-choice relationships.
    
    Parameters
    ----------
    fragments : list[BaseFragment]
        The journal entry fragment stream
        
    Returns
    -------
    list[tuple[BaseFragment, list[BaseFragment]]]
        List of (block, choices) tuples
        
    Examples
    --------
    >>> pairs = extract_blocks_with_choices(fragments)
    >>> for block, choices in pairs:
    ...     assert len(choices) == 2
    ...     assert "Go north" in [c.content for c in choices]
    """
    result = []
    for fragment in fragments:
        if (hasattr(fragment, 'fragment_type') and 
            fragment.fragment_type == "block"):
            choices = extract_choices_from_block(fragment)
            result.append((fragment, choices))
    return result


def count_fragments_by_type(fragments: list[BaseFragment]) -> dict[str, int]:
    """
    Count fragments by type, recursively.
    
    Useful for debugging and comprehensive assertions.
    
    Parameters
    ----------
    fragments : list[BaseFragment]
        The journal entry fragment stream
        
    Returns
    -------
    dict[str, int]
        Mapping of fragment_type to count
        
    Examples
    --------
    >>> counts = count_fragments_by_type(fragments)
    >>> assert counts["block"] == 1
    >>> assert counts["choice"] == 3  # includes embedded ones
    """
    counts: dict[str, int] = {}
    
    def _count(frags: list[BaseFragment]) -> None:
        for frag in frags:
            if hasattr(frag, 'fragment_type'):
                ftype = frag.fragment_type
                counts[ftype] = counts.get(ftype, 0) + 1
                
                # Recurse into blocks
                if ftype == "block" and hasattr(frag, 'choices') and frag.choices:
                    _count(frag.choices)
    
    _count(fragments)
    return counts


# Backward compatibility: drop-in replacement for old _by_fragment_type
def _by_fragment_type(fragments: list[BaseFragment], fragment_type: str) -> list[BaseFragment]:
    """
    DEPRECATED: Use extract_fragments() instead.
    
    Kept for backward compatibility during migration.
    Automatically recurses into blocks to find embedded choices.
    """
    return extract_fragments(fragments, fragment_type, recurse=True)
