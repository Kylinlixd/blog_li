from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.pagination import PageNumberPagination
from .models import AccessLog
from .serializers import AccessLogSerializer


class AccessLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'pageSize'
    max_page_size = 100

    def get_paginated_response(self, data):
        from rest_framework.response import Response
        return Response({'code': 200, 'message': 'success', 'data': {'list': data, 'total': self.page.paginator.count, 'page': self.page.number, 'pageSize': self.page_size}})


class AccessLogViewSet(ReadOnlyModelViewSet):
    queryset = AccessLog.objects.select_related('user').all()
    serializer_class = AccessLogSerializer
    permission_classes = [IsAdminUser]
    pagination_class = AccessLogPagination
