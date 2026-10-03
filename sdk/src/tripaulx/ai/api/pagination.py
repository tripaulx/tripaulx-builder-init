"""Pagination of the event list (the only large list of the app)."""

from rest_framework.pagination import PageNumberPagination


class EventPagination(PageNumberPagination):
    """20 per page; clients may ask up to 100."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
