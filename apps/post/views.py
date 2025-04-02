from apps.post.models import Post 
from rest_framework.permissions import IsAuthenticated
# Create your views here.
from rest_framework.viewsets import ModelViewSet
from apps.post.serializers import PostSerializer, RecentPostSerializer
from django.db.models import Q, F
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.views import APIView


class PostPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'pageSize'
    max_page_size = 100
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        return Response({
            'code': 200,
            'data': {
                'total': self.page.paginator.count,
                'items': data
            },
            'message': '获取文章列表成功'
        })


class PostViewSet(ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PostPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        
        # 过滤条件
        if 'categoryId' in params:
            queryset = queryset.filter(category_id=params['categoryId'])
        if 'tagId' in params:
            queryset = queryset.filter(tags__id=params['tagId'])
        if 'status' in params:
            queryset = queryset.filter(status=params['status'])
        if 'keyword' in params:
            queryset = queryset.filter(Q(title__icontains=params['keyword']) | 
                                      Q(content__icontains=params['keyword']))
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # 增加浏览量
        Post.objects.filter(pk=instance.pk).update(views=F('views') + 1)
        # 重新获取更新后的实例
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'code': 200,
            'data': serializer.data,
            'message': '获取文章详情成功'
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            'code': 200,
            'data': {'id': serializer.instance.id},
            'message': '创建文章成功'
        })
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'code': 200,
            'message': '更新文章成功'
        })
        
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'code': 200,
            'message': '删除文章成功'
        })


class RecentPostsView(APIView):
    permission_classes = [IsAuthenticated]
    
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
            'message': '获取最近文章成功',
            'data': serializer.data
        })