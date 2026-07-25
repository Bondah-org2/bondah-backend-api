from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class BondmakerPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class BondmakerPublicPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50


class PendingRequestListPagination(PageNumberPagination):
    """
    Clean page-number pagination for bondmaker views.

    Default: 12 items per page
    Client can change with ?page_size=
    Hard cap at 50
    """

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "total_pages": self.page.paginator.num_pages,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


class UserSwipeDeckPagination(PageNumberPagination):
    page_size = 10
    page_query_param = "page_size"
    max_page_size = 50


class BondmakerSearchPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class BondCirclePostPagination(PageNumberPagination):
    page_size = 10  # default items per page
    page_size_query_param = "page_size"  # allow client to override
    max_page_size = 50  # max limit


class ChatMessagePagination(PageNumberPagination):
    page_size = 20  # default items per page
    page_size_query_param = "page_size"  # allow client to override
    max_page_size = 50  # max limit


class ActivityFeedPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50
