from apps.post.models import Post 
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from apps.post.serializers import (
    PostSerializer, AdjacentPostSerializer,
    HotPostSerializer, RecentPostSerializer
)
from django.db.models import Q, F
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from apps.category.models import Category
from apps.tag.models import Tag


class PostPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'pageSize'
    max_page_size = 100
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'total': self.page.paginator.count,
                'items': data
            }
        })


class PostViewSet(ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [AllowAny]
    pagination_class = PostPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        # 如果是前台接口，只返回已发布的文章
        if self.request.path.startswith('/api/blog'):
            queryset = queryset.filter(status='published')
        return queryset

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response({
                'code': 200,
                'message': '创建文章成功',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'code': 500,
                'message': f'创建文章失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({
                'code': 200,
                'message': '更新文章成功',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'code': 500,
                'message': f'更新文章失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        # 如果是前台API，禁止删除操作
        if request.path.startswith('/api/blog'):
            return Response({
                'code': 403,
                'message': '前台API不支持删除操作'
            }, status=status.HTTP_403_FORBIDDEN)
            
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'code': 200,
            'message': '删除文章成功'
        })
    
    @action(detail=True, methods=['get'])
    def adjacent(self, request, pk=None):
        post = self.get_object()
        prev_post = Post.objects.filter(
            status='published',
            create_time__lt=post.create_time
        ).order_by('-create_time').first()
        
        next_post = Post.objects.filter(
            status='published',
            create_time__gt=post.create_time
        ).order_by('create_time').first()
        
        serializer = AdjacentPostSerializer({
            'prev': prev_post,
            'next': next_post
        })
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        post = self.get_object()
        post.views = F('views') + 1
        post.save()
        return Response({
            'code': 200,
            'message': 'success',
            'data': None
        })


class RecentPostsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        # 获取limit参数，默认为5
        limit = int(request.query_params.get('limit', 5))
        if limit > 20:  # 限制最大数量
            limit = 20
            
        # 获取最近的文章
        recent_posts = Post.objects.filter(status='published').order_by('-create_time')[:limit]
        
        serializer = RecentPostSerializer(recent_posts, many=True)
        return Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data
        })


class HotPostsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        limit = int(request.query_params.get('limit', 5))
        if limit > 20:
            limit = 20
            
        hot_posts = Post.objects.filter(status='published').order_by('-views')[:limit]
        serializer = HotPostSerializer(hot_posts, many=True)
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data
        })


class CategoryPostsView(APIView):
    permission_classes = [AllowAny]
    pagination_class = PostPagination
    
    def get(self, request, categoryId):
        try:
            category = Category.objects.get(pk=categoryId)
            posts = Post.objects.filter(category=category).order_by('-create_time')
            paginator = self.pagination_class()
            result = paginator.paginate_queryset(posts, request)
            serializer = PostSerializer(result, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Category.DoesNotExist:
            return Response({'code': 404, 'message': '分类不存在'}, status=status.HTTP_404_NOT_FOUND)


class TagPostsView(APIView):
    permission_classes = [AllowAny]
    pagination_class = PostPagination
    
    def get(self, request, tagId):
        try:
            tag = Tag.objects.get(pk=tagId)
            posts = Post.objects.filter(tags=tag).order_by('-create_time')
            paginator = self.pagination_class()
            result = paginator.paginate_queryset(posts, request)
            serializer = PostSerializer(result, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Tag.DoesNotExist:
            return Response({'code': 404, 'message': '标签不存在'}, status=status.HTTP_404_NOT_FOUND)