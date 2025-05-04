from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from apps.dynamic.models import Dynamic
from apps.category.models import Category
from apps.tag.models import Tag
from apps.comment.models import Comment
from rest_framework import status
from django.conf import settings

# Create your views here.
class StatsView(APIView):
    """
    获取博客统计数据API
    """
    permission_classes = [AllowAny]  # 允许所有用户访问
    authentication_classes = []  # 不进行任何认证
    
    def get(self, request):
        try:
            # 如果是前台请求，只统计已发布的动态
            dynamics_filter = {}
            if request.path.startswith('/blog'):
                dynamics_filter['status'] = 'published'
            
            # 获取总数统计
            total_dynamics = Dynamic.objects.filter(**dynamics_filter).count()
            total_categories = Category.objects.count()
            total_tags = Tag.objects.count()
            
            # 评论统计
            # 如果是前台请求，只统计已发布动态的评论
            if request.path.startswith('/blog'):
                total_comments = Comment.objects.filter(dynamic__status='published').count()
            else:
                total_comments = Comment.objects.count()
            
            # 获取最近7天的动态统计
            now = timezone.now()
            seven_days_ago = now - timedelta(days=7)
            daily_dynamics = Dynamic.objects.filter(
                created_at__gte=seven_days_ago,
                **dynamics_filter
            ).extra(
                select={'day': 'date(created_at)'}
            ).values('day').annotate(count=Count('id')).order_by('day')
            
            # 获取分类统计
            # 如果是前台请求，只统计已发布的动态
            from django.db.models import Q
            if request.path.startswith('/blog'):
                category_stats = Category.objects.annotate(
                    dynamic_count=Count('dynamics', filter=Q(dynamics__status='published'))
                ).values('name', 'dynamic_count')
                
                tag_stats = Tag.objects.annotate(
                    dynamic_count=Count('dynamics', filter=Q(dynamics__status='published'))
                ).values('name', 'dynamic_count')
            else:
                # 获取分类统计
                category_stats = Category.objects.annotate(
                    dynamic_count=Count('dynamics')
                ).values('name', 'dynamic_count')
                
                # 获取标签统计
                tag_stats = Tag.objects.annotate(
                    dynamic_count=Count('dynamics')
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
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"统计接口错误: {str(e)}")  # 打印错误信息
            print(f"错误堆栈: {error_traceback}")  # 打印完整堆栈
            return Response({
                'code': 500,
                'message': f"服务器内部错误: {str(e)}",
                'data': None,
                'debug': {
                    'exception': str(e),
                    'traceback': error_traceback.split('\n') if settings.DEBUG else None
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
