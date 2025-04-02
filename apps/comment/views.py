from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Comment
from .serializers import CommentSerializer

# Create your views here.
class CommentPagination(PageNumberPagination):
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
            'message': '获取评论列表成功'
        })

class CommentViewSet(ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CommentPagination
    
    def get_queryset(self):
        queryset = Comment.objects.all().select_related('post')
        params = self.request.query_params
        
        # 过滤条件
        if 'postTitle' in params and params['postTitle']:
            queryset = queryset.filter(post__title__icontains=params['postTitle'])
        if 'author' in params and params['author']:
            queryset = queryset.filter(author__icontains=params['author'])
        if 'status' in params and params['status']:
            queryset = queryset.filter(status=params['status'])
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'data': serializer.data,
            'message': '获取评论列表成功'
        })
    
    @action(detail=True, methods=['put'])
    def approve(self, request, pk=None):
        comment = self.get_object()
        comment.status = 'approved'
        comment.save()
        return Response({
            'code': 200,
            'message': '评论已批准'
        })
    
    @action(detail=True, methods=['put'])
    def reject(self, request, pk=None):
        comment = self.get_object()
        comment.status = 'rejected'
        comment.save()
        return Response({
            'code': 200,
            'message': '评论已拒绝'
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'code': 200,
            'message': '评论已删除'
        })
