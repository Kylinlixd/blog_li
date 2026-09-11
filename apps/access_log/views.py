import ipaddress
from django.utils import timezone
from datetime import timedelta
from rest_framework.exceptions import ValidationError
from apps.user.permissions import IsContentEditor
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Max, Q
from .models import AccessLog, IpSecurityRule
from .profile import build_ip_profile, build_ip_profiles
from .geo import lookup_geo
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
        window = self.request.query_params.get('window', '')
        security_group = self.request.query_params.get('securityGroup', '')
        if window and window != '7d':
            raise ValidationError({'window': '仅支持 7d 时间窗口'})
        if security_group and security_group != 'blocked':
            raise ValidationError({'securityGroup': '无效安全分组'})
        if ip:
            queryset = queryset.filter(ip_address__icontains=ip.strip())
        if status_code and status_code.strip() in {'2', '3', '4', '5'}:
            family = int(status_code.strip()) * 100
            queryset = queryset.filter(status_code__gte=family, status_code__lt=family + 100)
        if path:
            queryset = queryset.filter(path__icontains=path.strip())
        if window == '7d':
            cutoff = timezone.now() - timedelta(days=7)
            queryset = queryset.filter(created_at__gte=cutoff, created_at__lte=timezone.now())
        if security_group == 'blocked':
            queryset = queryset.filter(security_action__in=('blocked', 'rate_limited'))
        return queryset

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Return global seven-day security counters independent of list filters."""
        now = timezone.now()
        cutoff = now - timedelta(days=7)
        addresses = list(
            AccessLog.objects.filter(
                created_at__gte=cutoff,
                created_at__lte=now,
                ip_address__isnull=False,
            ).values_list('ip_address', flat=True).distinct()
        )
        profiles = build_ip_profiles(addresses, now=now, since=cutoff)
        active_rules = IpSecurityRule.objects.filter(status='active').filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).count()
        blocked_requests = AccessLog.objects.filter(
            created_at__gte=cutoff,
            created_at__lte=now,
            security_action__in=('blocked', 'rate_limited'),
        ).count()
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'active_ips': len(profiles),
                'high_risk_ips': sum(profile['risk_level'] in ('high', 'critical') for profile in profiles),
                'active_rules': active_rules,
                'blocked_requests': blocked_requests,
                'window_start': cutoff.isoformat(),
                'window_end': now.isoformat(),
                'generated_at': now.isoformat(),
            },
        })

    @action(detail=False, methods=['get'])
    def profiles(self, request):
        window = request.query_params.get('window', '')
        if window and window != '7d':
            raise ValidationError({'window': '仅支持 7d 时间窗口'})
        now = timezone.now()
        cutoff = now - timedelta(days=7) if window == '7d' else None
        log_queryset = AccessLog.objects.all()
        if cutoff:
            log_queryset = log_queryset.filter(created_at__gte=cutoff, created_at__lte=now)
        rows = log_queryset.values('ip_address').annotate(
            total=Count('id'),
            last_seen=Max('created_at'),
        ).filter(ip_address__isnull=False).order_by('-last_seen')
        ip_filter = request.query_params.get('ip', '').strip()
        network = None
        if '/' in ip_filter:
            try:
                network = ipaddress.ip_network(ip_filter, strict=False)
            except ValueError:
                raise ValidationError({'ip': '请输入有效的 IP 或 CIDR'})
        elif ip_filter:
            rows = rows.filter(ip_address__icontains=ip_filter)
        risk = request.query_params.get('risk', '')
        risk_group = request.query_params.get('riskGroup', '')
        scope = request.query_params.get('network', '')
        region = request.query_params.get('region', '').strip().casefold()
        if risk and risk not in {'low', 'medium', 'high', 'critical'}:
            raise ValidationError({'risk': '无效风险等级'})
        if risk_group and risk_group != 'high_plus':
            raise ValidationError({'riskGroup': '无效风险分组'})
        if scope and scope not in {'private', 'public'}:
            raise ValidationError({'network': '请选择内网或公网'})
        profiles = []
        addresses = [row['ip_address'] for row in rows if not network or ipaddress.ip_address(row['ip_address']) in network]
        for profile in build_ip_profiles(addresses, now=now, since=cutoff):
            if scope and profile['is_public'] != (scope == 'public'):
                continue
            if region and region not in ' '.join(str(profile['geo'].get(key, '')) for key in ('country', 'region', 'city', 'location')).casefold():
                continue
            profiles.append(profile)
        cutoff = timezone.now() - timedelta(days=7)
        summary = {
            'high_risk': sum(p['risk_level'] in ('high', 'critical') for p in profiles),
            'blocked_requests': AccessLog.objects.filter(created_at__gte=cutoff, security_action__in=('blocked', 'rate_limited')).count(),
            'tracking_started_at': cutoff.isoformat(),
        }
        if risk_group == 'high_plus':
            profiles = [profile for profile in profiles if profile['risk_level'] in ('high', 'critical')]
        elif risk:
            profiles = [profile for profile in profiles if profile['risk_level'] == risk]
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(profiles, request, view=self)
        # Only resolve the visible page online; region filters use the persisted geo cache.
        # Cached ownership is already available; missing/new public IPs resolve in the detail view
        # and in the scheduled refresh command, never blocking the whole list on a provider outage.
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'list': page,
                'summary': summary,
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
