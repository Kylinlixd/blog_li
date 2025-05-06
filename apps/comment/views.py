from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework import status
from .models import Comment
from .serializers import (
    CommentSerializer, CommentCreateSerializer,
    CommentUpdateSerializer
)

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
    permission_classes = [IsAuthenticated]
    pagination_class = CommentPagination
    
    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]  # 允许所有用户访问列表
        return super().get_permissions()
    
    def dispatch(self, request, *args, **kwargs):
        """重载dispatch方法，对list请求跳过认证"""
        if request.method.lower() == 'get' and self.action_map.get(request.method.lower()) == 'list':
            self.authentication_classes = []
        return super().dispatch(request, *args, **kwargs)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CommentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CommentUpdateSerializer
        return CommentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 过滤条件
        author = self.request.query_params.get('author')
        status = self.request.query_params.get('status')
        
        if author:
            queryset = queryset.filter(author__username=author)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'data': {
                'list': serializer.data,
                'total': queryset.count()
            },
            'message': '获取评论列表成功'
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'code': 200,
                'data': serializer.data,
                'message': '创建评论成功'
            })
        return Response({
            'code': 400,
            'message': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'code': 200,
                'data': serializer.data,
                'message': '更新评论成功'
            })
        return Response({
            'code': 400,
            'message': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            'code': 200,
            'message': '删除评论成功'
        })
    
    @action(detail=True, methods=['put'])
    def approve(self, request, pk=None):
        instance = self.get_object()
        instance.status = 'approved'
        instance.save()
        return Response({
            'code': 200,
            'message': '评论审核通过'
        })
    
    @action(detail=True, methods=['put'])
    def reject(self, request, pk=None):
        instance = self.get_object()
        instance.status = 'rejected'
        instance.save()
        return Response({
            'code': 200,
            'message': '评论审核拒绝'
        })
