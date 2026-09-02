"""
Pagination tuned for slow connections.

Students open this on cheap phones over weak signal, so pages stay small and
the client is told the total up front to render progress without a second
request.
"""
from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("page", self.page.number),
                    ("pages", self.page.paginator.num_pages),
                    ("page_size", self.get_page_size(self.request)),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )


class SmallPagination(StandardPagination):
    """For notification feeds and activity timelines."""

    page_size = 10


class LargePagination(StandardPagination):
    """For export screens and the archive browser."""

    page_size = 50
    max_page_size = 500
