# utils/pagination.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        """
        Override to provide better error messages for invalid page/page_size
        """
        try:
            return super().paginate_queryset(queryset, request, view)
        except Exception as exc:
            # Catch common pagination errors (invalid page, page_size, etc.)
            raise ValidationError({
                "success": False,
                "message": "Invalid pagination parameters. 'page' and 'page_size' must be valid positive integers.",
                "error": str(exc)
            }) from exc

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'meta': {
                'total': self.page.paginator.count,
                'page': self.page.number,
                'pages': self.page.paginator.num_pages,
                'per_page': self.page_size,
            },
            'data': data
        })