from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from apps.dynamic.models import Dynamic
from apps.category.models import Category
from apps.tag.models import Tag
from apps.comment.models import Comment

# Create your views here.
class StatsView(APIView):
    """
    获取博客统计数据API
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # 获取总数统计
        total_dynamics = Dynamic.objects.count()
        total_categories = Category.objects.count()
        total_tags = Tag.objects.count()
        total_comments = Comment.objects.count()
        
        # 获取最近7天的动态统计
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)
        daily_dynamics = Dynamic.objects.filter(
            create_time__gte=seven_days_ago
        ).extra(
            select={'day': 'date(create_time)'}
        ).values('day').annotate(count=Count('id')).order_by('day')
        
        # 获取分类统计
        category_stats = Category.objects.annotate(
            dynamic_count=Count('dynamic')
        ).values('name', 'dynamic_count')
        
        # 获取标签统计
        tag_stats = Tag.objects.annotate(
            dynamic_count=Count('dynamic')
        ).values('name', 'dynamic_count')
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'total': {
                    'dynamics': total_dynamics,
                    'categories': total_categories,
                    'tags': total_tags,
                    'comments': total_comments
                },
                'daily': list(daily_dynamics),
                'categories': list(category_stats),
                'tags': list(tag_stats)
            }
        })
