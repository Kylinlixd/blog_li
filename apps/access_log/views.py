from apps.user.permissions import IsContentEditor
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Max
from .models import AccessLog, IpSecurityRule
from .profile import build_ip_profile
from .rules import revoke_rule
from .serializers import AccessLogSerializer, IpSecurityRuleSerializer


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
    permission_classes = [IsContentEditor]
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

    @action(detail=False, methods=['get'])
    def profiles(self, request):
        rows = AccessLog.objects.values('ip_address').annotate(
            total=Count('id'),
            last_seen=Max('created_at'),
        ).filter(ip_address__isnull=False).order_by('-last_seen')
        ip_filter = request.query_params.get('ip', '').strip()
        if ip_filter:
            rows = rows.filter(ip_address__icontains=ip_filter)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(rows, request, view=self)
        profiles = [
            build_ip_profile(row['ip_address'])
            for row in page
        ]
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'list': profiles,
                'total': paginator.page.paginator.count,
                'page': paginator.page.number,
                'pageSize': paginator.page_size,
            }
        })

    @action(detail=False, methods=['get'])
    def profile(self, request):
        ip_address = request.query_params.get('ip', '').strip()
        profile = build_ip_profile(ip_address)
        logs = AccessLog.objects.filter(ip_address=profile['ip_address']).order_by('-created_at')[:30]
        profile['recent_logs'] = AccessLogSerializer(logs, many=True).data
        return Response({
            'code': 200,
            'message': 'success',
            'data': profile,
        })


class IpSecurityRuleViewSet(ModelViewSet):
    queryset = IpSecurityRule.objects.select_related('created_by', 'revoked_by').all()
    serializer_class = IpSecurityRuleSerializer
    permission_classes = [IsContentEditor]
    pagination_class = None

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        revoke_rule(instance, request.user)
        return Response({'code': 200, 'message': '规则已撤销', 'data': None})

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        instance = self.get_object()
        revoke_rule(instance, request.user)
        return Response({'code': 200, 'message': '规则已撤销', 'data': None})
