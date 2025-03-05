from pydantic import Field

from tangl.business.core import Entity
from tangl.utils.bookmarked_list import BookmarkedList
# from tangl.service.response import BaseFragment

class ContentFragment: pass

class HasJournal(Entity):

    journal: BookmarkedList[ContentFragment] = Field(default_factory=BookmarkedList)
