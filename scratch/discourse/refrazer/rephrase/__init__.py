"""
There are two types of rephrasing:

1. static updates that are evaluated and applied immediately to the loaded text
2. dynamic update instructions that can be deferred to later

Data flow:

1. document is loaded
2. document is annotated
   - section by section (pre-tagged sections may be stashed)  # passages
   - statement by statement  # sections
   - word by word
3. text can then be rendered either
   - as static dump with fixed voices -or-
   - into an "intermediate" format where keywords are marked up
     for future transformation with dynamic voices

Document annotation has two editing inputs:

- a post-tagging but pre-annotation phase for fixing lemmas, pos,
  pov, and conjugations
- a post-annotation phase for replacing mis-rendered passages with
  improved verbage
"""

from .word import Word
from .statement import Statement
from .document import Document
