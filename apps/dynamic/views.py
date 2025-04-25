from apps.dynamic.models import Dynamic
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from apps.dynamic.serializers import (
    DynamicSerializer, AdjacentDynamicSerializer,
    HotDynamicSerializer, RecentDynamicSerializer,
    AdminDynamicSerializer, SimpleDynamicSerializer,
    DynamicCreateSerializer
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


class DynamicPagination(PageNumberPagination):
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
                'list' if self.request.path.startswith('/blog') else 'items': data
            }
        })


class DynamicViewSet(ModelViewSet):
    queryset = Dynamic.objects.all()
    pagination_class = DynamicPagination
    
    def get_permissions(self):
        if self.request.path.startswith('/blog'):
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_serializer_class(self):
        # 对于创建操作，使用DynamicCreateSerializer
        if self.action == 'create':
            return DynamicCreateSerializer
            
        # 检查是否请求简化版数据格式
        if self.request.query_params.get('format') == 'simple':
            return SimpleDynamicSerializer
        
        if self.request.path.startswith('/api'):
            return AdminDynamicSerializer
        return DynamicSerializer
    
    def get_queryset(self):
        queryset = self.queryset
        
        # 前台API只能看到已发布的动态
        if self.request.path.startswith('/blog'):
            queryset = queryset.filter(status='published')
        
        # 后台API可以根据状态筛选
        elif 'status' in self.request.query_params:
            status = self.request.query_params.get('status')
            queryset = queryset.filter(status=status)
        
        # 根据类型筛选
        if 'type' in self.request.query_params:
            type_val = self.request.query_params.get('type')
            queryset = queryset.filter(type=type_val)
        
        # 关键词搜索
        if 'keyword' in self.request.query_params:
            keyword = self.request.query_params.get('keyword')
            queryset = queryset.filter(
                Q(title__icontains=keyword) | 
                Q(content__icontains=keyword)
            )
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'total': queryset.count(),
                'list' if request.path.startswith('/blog') else 'items': serializer.data
            }
        })
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({
                'code': 200,
                'message': 'success',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'code': 404,
                'message': '动态不存在或已被删除',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response({
            'code': 200,
            'message': '创建动态成功',
            'data': {'id': instance.id}
        })
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # 如果请求包含mediaUrls、categoryId或tags字段，则使用DynamicCreateSerializer
        if any(field in request.data for field in ['mediaUrls', 'categoryId', 'tags']):
            serializer = DynamicCreateSerializer(instance, data=request.data, partial=partial, context={'request': request})
        else:
            serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
            
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'code': 200,
            'message': '更新动态成功',
            'data': None
        })
    
    def destroy(self, request, *args, **kwargs):
        # 如果是前台API，禁止删除操作
        if request.path.startswith('/blog'):
            return Response({
                'code': 403,
                'message': '前台API不支持删除操作'
            }, status=status.HTTP_403_FORBIDDEN)
            
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'code': 200,
            'message': '删除动态成功',
            'data': None
        })
    
    @action(detail=True, methods=['get'])
    def adjacent(self, request, pk=None):
        dynamic = self.get_object()
        prev_dynamic = Dynamic.objects.filter(
            status='published',
            create_time__lt=dynamic.create_time
        ).order_by('-create_time').first()
        
        next_dynamic = Dynamic.objects.filter(
            status='published',
            create_time__gt=dynamic.create_time
        ).order_by('create_time').first()
        
        serializer = AdjacentDynamicSerializer({
            'prev': prev_dynamic,
            'next': next_dynamic
        })
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        dynamic = self.get_object()
        dynamic.views = F('views') + 1
        dynamic.save()
        return Response({
            'code': 200,
            'message': 'success',
            'data': None
        })


class RecentDynamicsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        # 获取limit参数，默认为5
        limit = int(request.query_params.get('limit', 5))
        if limit > 20:  # 限制最大数量
            limit = 20
            
        # 获取最近的动态
        recent_dynamics = Dynamic.objects.filter(status='published').order_by('-create_time')[:limit]
        
        serializer = RecentDynamicSerializer(recent_dynamics, many=True)
        return Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data
        })


class HotDynamicsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        limit = int(request.query_params.get('limit', 5))
        if limit > 20:
            limit = 20
            
        hot_dynamics = Dynamic.objects.filter(status='published').order_by('-views')[:limit]
        serializer = HotDynamicSerializer(hot_dynamics, many=True)
        
        return Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data
        })


class CategoryDynamicsView(APIView):
    permission_classes = [AllowAny]
    pagination_class = DynamicPagination
    
    def get(self, request, categoryId):
        try:
            category = Category.objects.get(pk=categoryId)
            dynamics = Dynamic.objects.filter(category=category).order_by('-create_time')
            paginator = self.pagination_class()
            result = paginator.paginate_queryset(dynamics, request)
            serializer = DynamicSerializer(result, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Category.DoesNotExist:
            return Response({'code': 404, 'message': '分类不存在'}, status=status.HTTP_404_NOT_FOUND)


class TagDynamicsView(APIView):
    permission_classes = [AllowAny]
    pagination_class = DynamicPagination
    
    def get(self, request, tagId):
        try:
            tag = Tag.objects.get(pk=tagId)
            dynamics = Dynamic.objects.filter(tags=tag).order_by('-create_time')
            paginator = self.pagination_class()
            result = paginator.paginate_queryset(dynamics, request)
            serializer = DynamicSerializer(result, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Tag.DoesNotExist:
            return Response({'code': 404, 'message': '标签不存在'}, status=status.HTTP_404_NOT_FOUND)