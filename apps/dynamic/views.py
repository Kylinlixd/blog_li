from apps.dynamic.models import Dynamic
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from apps.dynamic.serializers import (
    DynamicSerializer, AdjacentDynamicSerializer,
    HotDynamicSerializer, RecentDynamicSerializer,
    AdminDynamicSerializer, SimpleDynamicSerializer,
    DynamicCreateSerializer, DynamicUpdateSerializer, DynamicListSerializer
)
from django.db.models import Q, F, Count
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
from django.db.models import Case, When, Value, FloatField


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
        if self.action in ['list', 'retrieve', 'like', 'view']:
            return [AllowAny()]  # 列表、详情、点赞和浏览允许所有用户访问
        return super().get_permissions()
    
    def dispatch(self, request, *args, **kwargs):
        """重载dispatch方法，确保绕过认证"""
        # 对于GET请求，我们跳过认证
        if request.method.lower() == 'get':
            self.authentication_classes = []
        # 对于点赞和浏览请求，我们跳过认证
        elif request.path.endswith('/like/') or request.path.endswith('/view/'):
            self.authentication_classes = []
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 如果是前台请求，只返回已发布的动态
        if self.request.path.startswith('/blog'):
            queryset = queryset.filter(status='published')
            
        # 搜索条件
        keyword = self.request.query_params.get('keyword', '')
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) | 
                Q(content__icontains=keyword)
            )
            
        # 类型过滤
        dynamic_type = self.request.query_params.get('type')
        if dynamic_type:
            queryset = queryset.filter(type=dynamic_type)
            
        # 状态过滤
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # 分类过滤
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        # 标签过滤
        tag_ids = self.request.query_params.getlist('tags')
        if tag_ids:
            queryset = queryset.filter(tags__id__in=tag_ids).distinct()
            
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DynamicCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DynamicUpdateSerializer
        elif self.action == 'list':
            return DynamicListSerializer
        return DynamicSerializer
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'code': 200,
                'message': 'success',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'code': 500,
                'message': str(e),
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            
            # 使用F表达式原子性地增加浏览量
            from django.db.models import F
            from django.db import transaction
            
            with transaction.atomic():
                # 原子性地增加浏览量
                Dynamic.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
                # 重新获取最新值
                instance.refresh_from_db()
            
            # 序列化数据
            serializer = self.get_serializer(instance)
            
            # 返回数据
            return Response({
                'code': 200,
                'message': 'success',
                'data': {
                    'id': instance.id,
                    'title': instance.title,
                    'content': instance.content,
                    'created_at': instance.created_at,
                    'views': instance.view_count,
                    'likes': instance.like_count,
                    'category': {
                        'id': instance.category.id,
                        'name': instance.category.name
                    } if instance.category else None,
                    'tags': [{
                        'id': tag.id,
                        'name': tag.name
                    } for tag in instance.tags.all()]
                }
            })
            
        except Exception as e:
            return Response({
                'code': 500,
                'message': str(e),
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
    
    @action(detail=True, methods=['post', 'put'])
    def view(self, request, pk=None):
        try:
            dynamic = self.get_object()
            ip_address = request.META.get('REMOTE_ADDR', '')
            
            # 使用F表达式原子性地增加浏览量
            from django.db.models import F
            from django.db import transaction
            
            with transaction.atomic():
                # 获取更新前的值
                old_view_count = dynamic.view_count
                # 原子性地增加浏览量
                Dynamic.objects.filter(pk=dynamic.pk).update(view_count=F('view_count') + 1)
                # 重新获取最新值
                dynamic.refresh_from_db()
            
            return Response({
                'code': 200,
                'message': '浏览量增加成功',
                'data': {
                    'id': dynamic.id,
                    'title': dynamic.title,
                    'old_view_count': old_view_count,
                    'view_count': dynamic.view_count
                }
            })
        except Exception as e:
            return Response({
                'code': 500, 
                'message': f'增加浏览量失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        try:
            dynamic = self.get_object()
            ip_address = request.META.get('REMOTE_ADDR')
            
            # 检查 IP 是否已经点赞
            if dynamic.ip_likes.filter(ip_address=ip_address).exists():
                return Response({
                    'code': 400,
                    'message': '您已经点过赞了',
                    'data': {
                        'liked': True,
                        'like_count': dynamic.like_count
                    }
                })
            
            # 检查用户是否已登录
            if request.user.is_authenticated:
                # 检查用户是否已点赞
                if dynamic.liked_by.filter(id=request.user.id).exists():
                    # 取消点赞
                    dynamic.liked_by.remove(request.user)
                    dynamic.like_count = max(0, dynamic.like_count - 1)
                    dynamic.save()
                    # 删除 IP 点赞记录
                    dynamic.ip_likes.filter(ip_address=ip_address).delete()
                    return Response({
                        'code': 200,
                        'message': '取消点赞成功',
                        'data': {
                            'liked': False,
                            'like_count': dynamic.like_count
                        }
                    })
                else:
                    # 添加点赞
                    dynamic.liked_by.add(request.user)
                    dynamic.like_count += 1
                    dynamic.save()
                    # 创建 IP 点赞记录
                    dynamic.ip_likes.create(ip_address=ip_address)
                    return Response({
                        'code': 200,
                        'message': '点赞成功',
                        'data': {
                            'liked': True,
                            'like_count': dynamic.like_count
                        }
                    })
            else:
                # 未登录用户只能点赞一次
                dynamic.like_count += 1
                dynamic.save()
                # 创建 IP 点赞记录
                dynamic.ip_likes.create(ip_address=ip_address)
                return Response({
                    'code': 200,
                    'message': '点赞成功',
                    'data': {
                        'liked': True,
                        'like_count': dynamic.like_count
                    }
                })
                
        except Exception as e:
            return Response({
                'code': 500,
                'message': str(e),
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            
            # 分页
            paginator = self.pagination_class()
            result = paginator.paginate_queryset(dynamics, request)
            
            # 序列化动态列表
            dynamics_serializer = DynamicListSerializer(result, many=True)
            
            # 返回数据
            return Response({
                'code': 200,
                'message': 'success',
                'data': {
                    'category': category_serializer.data,
                    'dynamics': dynamics_serializer.data,
                    'total': paginator.page.paginator.count
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
            # 获取标签
            tag = Tag.objects.get(pk=tagId)
            
            # 获取该标签下已发布的动态
            dynamics = Dynamic.objects.filter(
                tags=tag,
                status='published'
            ).order_by('-created_at')
            
            # 分页
            paginator = self.pagination_class()
            result = paginator.paginate_queryset(dynamics, request)
            
            # 序列化数据
            serializer = DynamicListSerializer(result, many=True)
            
            # 返回数据
            return Response({
                'code': 200,
                'message': 'success',
                'data': {
                    'tag': {
                        'id': tag.id,
                        'name': tag.name,
                        'description': tag.description if hasattr(tag, 'description') else '',
                        'count': tag.dynamics.filter(status='published').count()
                    },
                    'dynamics': serializer.data,
                    'total': paginator.page.paginator.count
                }
            })
            
        except Tag.DoesNotExist:
            return Response({
                'code': 404,
                'message': '标签不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'code': 500,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


class SearchView(APIView):
    permission_classes = [AllowAny]
    pagination_class = DynamicPagination
    
    def get(self, request):
        try:
            # 获取查询参数
            keyword = request.GET.get('keyword', '')
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('pageSize', 10))
            search_type = request.GET.get('searchType', 'all')
            include_tags = request.GET.get('includeTags', 'true').lower() == 'true'
            include_categories = request.GET.get('includeCategories', 'true').lower() == 'true'
            sort_by = request.GET.get('sortBy', 'relevance')
            
            results = []
            
            # 搜索动态（只返回已发布的）
            dynamics = Dynamic.objects.filter(
                Q(title__icontains=keyword) | 
                Q(content__icontains=keyword),
                status='published'
            ).annotate(
                relevance=Case(
                    When(title__icontains=keyword, then=Value(0.9)),
                    When(content__icontains=keyword, then=Value(0.7)),
                    default=Value(0.5),
                    output_field=FloatField(),
                )
            )
            
            # 添加动态结果
            for dynamic in dynamics:
                results.append({
                    'id': dynamic.id,
                    'type': 'dynamic',
                    'title': dynamic.title,
                    'content': dynamic.content,
                    'excerpt': dynamic.content[:200] + '...' if len(dynamic.content) > 200 else dynamic.content,
                    'createdAt': dynamic.created_at,
                    'updatedAt': dynamic.updated_at,
                    'views': dynamic.view_count,
                    'likes': dynamic.like_count,
                    'comments': dynamic.comments.count() if hasattr(dynamic, 'comments') else 0,
                    'relevance': dynamic.relevance,
                    'tags': [{
                        'id': tag.id,
                        'name': tag.name,
                        'count': tag.dynamics.filter(status='published').count()
                    } for tag in dynamic.tags.all()],
                    'category': {
                        'id': dynamic.category.id,
                        'name': dynamic.category.name,
                        'count': dynamic.category.dynamics.filter(status='published').count()
                    } if dynamic.category else None
                })
            
            # 搜索标签
            if include_tags:
                tags = Tag.objects.filter(
                    name__icontains=keyword
                ).annotate(
                    count=Count('dynamics', filter=Q(dynamics__status='published')),
                    relevance=Case(
                        When(name__icontains=keyword, then=Value(0.85)),
                        default=Value(0.5),
                        output_field=FloatField(),
                    )
                )
                
                for tag in tags:
                    results.append({
                        'id': tag.id,
                        'type': 'tag',
                        'title': tag.name,
                        'name': tag.name,
                        'relevance': tag.relevance,
                        'count': tag.count,
                        'description': f"{tag.name} 相关文章标签"
                    })
            
            # 搜索分类
            if include_categories:
                categories = Category.objects.filter(
                    name__icontains=keyword
                ).annotate(
                    count=Count('dynamics', filter=Q(dynamics__status='published')),
                    relevance=Case(
                        When(name__icontains=keyword, then=Value(0.75)),
                        default=Value(0.5),
                        output_field=FloatField(),
                    )
                )
                
                for category in categories:
                    results.append({
                        'id': category.id,
                        'type': 'category',
                        'title': category.name,
                        'name': category.name,
                        'relevance': category.relevance,
                        'count': category.count,
                        'description': f"{category.name} 相关文章"
                    })
            
            # 按相关度排序
            if sort_by == 'relevance':
                results.sort(key=lambda x: x['relevance'], reverse=True)
            
            # 分页
            total = len(results)
            start = (page - 1) * page_size
            end = start + page_size
            paginated_results = results[start:end]
            
            return Response({
                'code': 200,
                'message': 'success',
                'data': {
                    'list': paginated_results,
                    'total': total,
                    'page': page,
                    'pageSize': page_size
                }
            })
            
        except Exception as e:
            return Response({
                'code': 500,
                'message': str(e),
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)