from rest_framework.permissions import IsAuthenticated
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
    permission_classes = [IsAuthenticated]
    pagination_class = AccessLogPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        ip = self.request.query_params.get('ip')
        status_code = self.request.query_params.get('status')
        path = self.request.query_params.get('path')
        if ip:
            queryset = queryset.filter(ip_address__icontains=ip.strip())
        if status_code and status_code.strip() in {'2', '3', '4', '5'}:
            family = int(status_code.strip()) * 100
            queryset = queryset.filter(status_code__gte=family, status_code__lt=family + 100)
        if path:
            queryset = queryset.filter(path__icontains=path.strip())
        return queryset
