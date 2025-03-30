from typing import Optional, Self

from .content_response import ContentResponse, AnyContentFragment


class MultipartResponse(ContentResponse):
    # Minimal support for paged or streaming responses
    page: Optional[int] = None

    @property
    def is_paged(self) -> bool:
        return self.page is not None

    @classmethod
    def gather_pages(cls, *pages: Self) -> Self:
        """Combine multiple paged responses back into a single response"""
        if not pages:
            return

        # Sort by page number and extract fragments
        sorted_pages = sorted(pages, key=lambda r: r.page)
        all_fragments = []
        for page in sorted_pages:
            all_fragments.extend(page.data)

        # Use the first page's metadata for the combined response
        return sorted_pages[0].copy_model(update={'data': all_fragments})

    is_streaming: Optional[bool] = False
    is_complete: Optional[bool] = None

    def gather_fragments(self, *fragments: AnyContentFragment):
        if not self.is_streaming:
            raise ValueError("Cannot gather fragments without streaming.")
        filtered_fragments = filter(lambda x: x.ref_id == self.uid, fragments)
        self.data += list(filtered_fragments)
        self.data = self.get_ordered_fragments()
