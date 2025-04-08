from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum

from apps.post.models import Post
from apps.category.models import Category
from apps.tag.models import Tag

# Create your views here.
class StatsView(APIView):
    """
    获取博客统计数据API
    """
    # permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # 获取文章总数
        post_count = Post.objects.count()
        
        # 获取分类总数
        category_count = Category.objects.count()
        
        # 获取标签总数
        tag_count = Tag.objects.count()
        
        # 获取总浏览量
        total_views = Post.objects.aggregate(total_views=Sum('views'))['total_views'] or 0
        
        return Response({
            'code': 200,
            'message': '获取统计数据成功',
            'data': {
                'postCount': post_count,
                'categoryCount': category_count,
                'tagCount': tag_count,
                'totalViews': total_views
            }
        })
