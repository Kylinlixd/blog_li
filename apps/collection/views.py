from django.db import transaction
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from apps.user.permissions import IsContentEditor
from blog.pagination import StandardPagination

from .models import Collection, CollectionItem
from .serializers import (
    CollectionAdminSerializer,
    CollectionDetailSerializer,
    CollectionItemAdminSerializer,
    CollectionListSerializer,
)


def sync_dynamic_collections(dynamic, collection_ids):
    """把文章的合集归属差量同步到 collectionIds。

    只增删变化项，已在合集里的文章保留原章节序号；新加入的追加到末尾。
    """
    desired = {int(value) for value in collection_ids or []}
    existing = {
        item.collection_id: item
        for item in CollectionItem.objects.filter(dynamic=dynamic)
    }

    removable = [item.pk for cid, item in existing.items() if cid not in desired]
    if removable:
        CollectionItem.objects.filter(pk__in=removable).delete()

    for collection_id in desired - set(existing):
        collection = Collection.objects.filter(pk=collection_id).first()
        if collection is None:
            continue
        last_sort = (
            CollectionItem.objects.filter(collection=collection)
            .order_by('-sort')
            .values_list('sort', flat=True)
            .first()
        ) or 0
        CollectionItem.objects.create(
            collection=collection, dynamic=dynamic, sort=last_sort + 1
        )


class BlogCollectionViewSet(ViewSet):
    """前台合集接口：列表 + 目录详情（仅收录已发布文章）。"""

    permission_classes = [AllowAny]

    def list(self, request):
        collections = Collection.objects.filter(status='active').annotate(
            item_count=Count('items', filter=Q(items__dynamic__status='published'))
        ).order_by('sort', 'id')
        serializer = CollectionListSerializer(collections, many=True)
        response = Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data,
        })
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

    def retrieve(self, request, pk=None):
        collection = Collection.objects.filter(pk=pk, status='active').first()
        if collection is None:
            return Response({'code': 404, 'message': '合集不存在', 'data': None}, status=404)
        items = (
            collection.items
            .filter(dynamic__status='published')
            .select_related('dynamic')
            .order_by('sort', 'id')
        )
        serializer = CollectionDetailSerializer(collection)
        data = serializer.data
        data['itemCount'] = len(items)
        data['items'] = [
            {
                'sort': item.sort,
                'id': item.dynamic_id,
                'title': item.dynamic.title,
                'createdAt': item.dynamic.created_at,
                'viewCount': item.dynamic.view_count,
            }
            for item in items
        ]
        response = Response({'code': 200, 'message': 'success', 'data': data})
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response


class CollectionAdminViewSet(ModelViewSet):
    """后台合集管理：CRUD + 章节排序。公开读取仍走 /api/blog/collections/。"""

    permission_classes = [IsContentEditor]
    pagination_class = StandardPagination
    serializer_class = CollectionAdminSerializer

    def get_queryset(self):
        queryset = Collection.objects.annotate(
            item_count=Count('items', distinct=True),
            published_count=Count(
                'items', filter=Q(items__dynamic__status='published'), distinct=True
            ),
        )
        keyword = self.request.query_params.get('keyword', '').strip()
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) | Q(series__icontains=keyword)
            )
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.order_by('sort', 'id')

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
            'data': {'total': queryset.count(), 'items': serializer.data},
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            'code': 200,
            'message': '创建合集成功',
            'data': {'id': serializer.instance.id},
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'code': 200,
            'message': '更新合集成功',
            'data': None,
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        has_items = instance.items.exists()
        if has_items:
            if instance.status != 'hidden':
                instance.status = 'hidden'
                instance.save(update_fields=['status', 'updated_at'])
            return Response({
                'code': 200,
                'message': '合集已隐藏；如需彻底删除，请先清空合集',
                'data': {'action': 'hidden'},
            })
        self.perform_destroy(instance)
        return Response({
            'code': 200,
            'message': '合集已删除',
            'data': {'action': 'deleted'},
        })

    @action(detail=False, methods=['get'])
    def options(self, request):
        collections = Collection.objects.filter(status='active').annotate(
            item_count=Count('items', distinct=True)
        ).order_by('sort', 'id')
        return Response({
            'code': 200,
            'message': 'success',
            'data': [
                {
                    'id': collection.id,
                    'title': collection.title,
                    'series': collection.series,
                    'itemCount': collection.item_count,
                }
                for collection in collections
            ],
        })

    @action(detail=True, methods=['get', 'put'])
    def items(self, request, pk=None):
        collection = self.get_object()
        if request.method == 'PUT':
            return self._replace_items(collection, request)

        items = (
            collection.items.select_related('dynamic', 'dynamic__category')
            .order_by('sort', 'id')
        )
        serializer = CollectionItemAdminSerializer(items, many=True)
        return Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data,
        })

    def _replace_items(self, collection, request):
        from apps.dynamic.models import Dynamic

        raw_items = request.data.get('items')
        if not isinstance(raw_items, list):
            return Response({
                'code': 400,
                'message': 'items 必须是数组',
                'data': None,
            }, status=status.HTTP_400_BAD_REQUEST)

        dynamic_ids = []
        for entry in raw_items:
            try:
                dynamic_ids.append(int(entry.get('dynamicId') or entry.get('id')))
            except (AttributeError, TypeError, ValueError):
                return Response({
                    'code': 400,
                    'message': 'items 中存在无效的文章 ID',
                    'data': None,
                }, status=status.HTTP_400_BAD_REQUEST)

        if len(set(dynamic_ids)) != len(dynamic_ids):
            return Response({
                'code': 400,
                'message': '同一篇文章不能在合集里重复',
                'data': None,
            }, status=status.HTTP_400_BAD_REQUEST)

        existing_ids = set(
            Dynamic.objects.filter(pk__in=dynamic_ids).values_list('id', flat=True)
        )
        missing = [pk for pk in dynamic_ids if pk not in existing_ids]
        if missing:
            return Response({
                'code': 400,
                'message': f'文章不存在：{missing}',
                'data': None,
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            CollectionItem.objects.filter(collection=collection).delete()
            CollectionItem.objects.bulk_create([
                CollectionItem(collection=collection, dynamic_id=dynamic_id, sort=index + 1)
                for index, dynamic_id in enumerate(dynamic_ids)
            ])

        items = (
            collection.items.select_related('dynamic', 'dynamic__category')
            .order_by('sort', 'id')
        )
        serializer = CollectionItemAdminSerializer(items, many=True)
        return Response({
            'code': 200,
            'message': '章节顺序已保存',
            'data': serializer.data,
        })
