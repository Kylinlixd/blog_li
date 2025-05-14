from apps.dynamic.models import Dynamic
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from apps.dynamic.serializers import (
    DynamicSerializer, AdjacentDynamicSerializer,
    HotDynamicSerializer, RecentDynamicSerializer,
    AdminDynamicSerializer, SimpleDynamicSerializer,
    DynamicCreateSerializer, DynamicUpdateSerializer, DynamicListSerializer
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
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django.conf import settings
import os
from apps.category.serializers import CategorySerializer


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
                'items': data
            }
        })


class DynamicViewSet(ModelViewSet):
    queryset = Dynamic.objects.all()
    pagination_class = DynamicPagination
    permission_classes = [IsAuthenticated]  # 默认需要认证
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]  # 列表和详情允许所有用户访问
        return super().get_permissions()
    
    def dispatch(self, request, *args, **kwargs):
        """重载dispatch方法，确保绕过认证"""
        # 对于GET请求，我们跳过认证
        if request.method.lower() == 'get':
            self.authentication_classes = []
        return super().dispatch(request, *args, **kwargs)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DynamicCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DynamicUpdateSerializer
        elif self.action == 'list':
            return DynamicListSerializer
        return DynamicSerializer
    
    def get_queryset(self):
        # 如果是获取单个动态，直接返回所有动态
        if self.action == 'retrieve':
            return Dynamic.objects.all()
            
        queryset = super().get_queryset()
        
        # 过滤条件
        type = self.request.query_params.get('type')
        status = self.request.query_params.get('status')
        content = self.request.query_params.get('content')
        
        if type:
            queryset = queryset.filter(type=type)
        if status:
            queryset = queryset.filter(status=status)
        if content:
            queryset = queryset.filter(content__icontains=content)  # 使用 icontains 进行模糊搜索
        
        # 排序
        sort = self.request.query_params.get('sort') or self.request.query_params.get('params[sort]')
        if sort:
            field, order = sort.split(':')
            if field == 'createdAt':
                field = 'created_at'
            if order == 'desc':
                field = f'-{field}'
            queryset = queryset.order_by(field)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = DynamicSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = DynamicSerializer(queryset, many=True)
            return Response({
                'code': 200,
                'message': 'success',
                'data': {
                    'total': queryset.count(),
                    'items': serializer.data
                }
            })
        except Exception as e:
            print(f"获取动态列表错误: {str(e)}")  # 打印错误信息
            return Response({
                'code': 500,
                'message': str(e),
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, *args, **kwargs):
        try:
            # 获取动态ID
            pk = kwargs.get('pk')
            print(f"尝试获取动态 ID: {pk}")
            
            # 直接从数据库查询
            instance = Dynamic.objects.filter(id=pk).first()
            if not instance:
                print(f"动态不存在: ID={pk}")
                return Response({
                    'code': 404,
                    'message': '动态不存在或已被删除',
                    'data': None
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 序列化数据
            serializer = self.get_serializer(instance)
            return Response({
                'code': 200,
                'message': '获取动态成功',
                'data': serializer.data
            })
        except Exception as e:
            print(f"获取动态详情错误: {str(e)}")
            return Response({
                'code': 500,
                'message': f'获取动态详情失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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
        current = self.get_object()
        prev = Dynamic.objects.filter(
            created_at__lt=current.created_at,
            status='published'
        ).order_by('-created_at').first()
        
        next = Dynamic.objects.filter(
            created_at__gt=current.created_at,
            status='published'
        ).order_by('created_at').first()
        
        return Response({
            'code': 200,
            'data': {
                'prev': DynamicListSerializer(prev).data if prev else None,
                'next': DynamicListSerializer(next).data if next else None
            },
            'message': '获取相邻动态成功'
        })
    
    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        dynamic = self.get_object()
        dynamic.view_count += 1
        dynamic.save()
        return Response({
            'code': 200,
            'message': '浏览量增加成功'
        })


class HotDynamicsView(ReadOnlyModelViewSet):
    queryset = Dynamic.objects.filter(status='published').order_by('-view_count')
    serializer_class = DynamicListSerializer
    permission_classes = []
    
    def list(self, request, *args, **kwargs):
        limit = int(request.query_params.get('limit', 5))
        queryset = self.get_queryset()[:limit]
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'data': serializer.data,
            'message': '获取热门动态成功'
        })


class RecentDynamicsView(ReadOnlyModelViewSet):
    queryset = Dynamic.objects.filter(status='published').order_by('-created_at')
    serializer_class = DynamicListSerializer
    permission_classes = []
    
    def list(self, request, *args, **kwargs):
        limit = int(request.query_params.get('limit', 5))
        queryset = self.get_queryset()[:limit]
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'data': serializer.data,
            'message': '获取最新动态成功'
        })


class CategoryDynamicsView(APIView):
    permission_classes = [AllowAny]
    pagination_class = DynamicPagination
    
    def get(self, request, categoryId):
        try:
            # 获取分类
            category = Category.objects.get(pk=categoryId)
            
            # 获取该分类下已发布的动态
            dynamics = Dynamic.objects.filter(
                category=category,
                status='published'
            ).order_by('-created_at')
            
            # 序列化分类信息
            category_serializer = CategorySerializer(category)
            
            # 序列化动态列表
            dynamics_serializer = DynamicListSerializer(dynamics, many=True)
            
            # 返回数据
            return Response({
                'code': 200,
                'message': 'success',
                'data': {
                    'category': category_serializer.data,
                    'dynamics': dynamics_serializer.data
                }
            })
            
        except Category.DoesNotExist:
            return Response({
                'code': 404,
                'message': '分类不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'code': 500,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TagDynamicsView(APIView):
    permission_classes = [AllowAny]
    pagination_class = DynamicPagination
    
    def get(self, request, tagId):
        try:
            tag = Tag.objects.get(pk=tagId)
            dynamics = Dynamic.objects.filter(tags=tag).order_by('-created_at')
            paginator = self.pagination_class()
            result = paginator.paginate_queryset(dynamics, request)
            serializer = DynamicSerializer(result, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Tag.DoesNotExist:
            return Response({'code': 404, 'message': '标签不存在'}, status=status.HTTP_404_NOT_FOUND)


class DynamicListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # 获取查询参数
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            dynamic_type = request.GET.get('type')
            status = request.GET.get('status')
            
            # 构建查询
            queryset = Dynamic.objects.all()
            
            # 根据类型过滤
            if dynamic_type:
                queryset = queryset.filter(type=dynamic_type)
            
            # 根据状态过滤
            if status:
                queryset = queryset.filter(status=status)
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            
            # 获取总数
            total = queryset.count()
            
            # 获取当前页数据
            dynamics = queryset[start:end]
            
            # 序列化数据
            data = {
                'items': DynamicSerializer(dynamics, many=True).data,
                'total': total
            }
            
            return Response({
                'code': 200,
                'data': data,
                'message': 'success'
            })
            
        except Exception as e:
            return Response({
                'code': 500,
                'message': f'获取动态列表失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)