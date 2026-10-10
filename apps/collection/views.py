from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django.db.models import Count, Q

from .models import Collection
from .serializers import CollectionDetailSerializer, CollectionListSerializer


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
