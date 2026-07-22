from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.category.models import Category
from apps.comment.models import Comment
from apps.dynamic.models import Dynamic
from apps.tag.models import Tag


class StatsView(APIView):
    """Return content totals and the latest seven-day publishing trend."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        seven_days_ago = timezone.now() - timedelta(days=7)
        daily_dynamics = (
            Dynamic.objects.filter(created_at__gte=seven_days_ago)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'total': {
                    'dynamics': Dynamic.objects.count(),
                    'categories': Category.objects.count(),
                    'tags': Tag.objects.count(),
                    'comments': Comment.objects.count(),
                },
                'daily': list(daily_dynamics),
                'categories': list(
                    Category.objects.annotate(dynamic_count=Count('dynamics'))
                    .values('name', 'dynamic_count')
                ),
                'tags': list(
                    Tag.objects.annotate(dynamic_count=Count('dynamics'))
                    .values('name', 'dynamic_count')
                ),
            },
        })
