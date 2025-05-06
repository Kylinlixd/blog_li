from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Count
from .models import Tag
from .serializers import TagSerializer

# Create your views here.
class TagViewSet(ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]  # 允许所有用户访问列表
        return super().get_permissions()
    
    def dispatch(self, request, *args, **kwargs):
        """重载dispatch方法，对list请求跳过认证"""
        if request.method.lower() == 'get' and self.action_map.get(request.method.lower()) == 'list':
            self.authentication_classes = []
        return super().dispatch(request, *args, **kwargs)
    
    def list(self, request, *args, **kwargs):
        # 添加动态计数
        queryset = self.filter_queryset(self.get_queryset()).annotate(
            dynamic_count=Count('dynamics')
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'data': {
                'items': serializer.data,
                'total': queryset.count()
            },
            'message': 'success'
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            'code': 200,
            'data': {'id': serializer.instance.id},
            'message': '创建标签成功'
        })
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'code': 200,
            'message': '更新标签成功'
        })
        
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # 检查是否有关联的动态
        if hasattr(instance, 'dynamics') and instance.dynamics.exists():
            return Response({
                'code': 400,
                'message': '该标签下有动态，不能删除'
            })
        self.perform_destroy(instance)
        return Response({
            'code': 200,
            'message': '删除标签成功'
        })
