from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Category
from .serializers import CategorySerializer, SimpleCategorySerializer
from rest_framework.response import Response

class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
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
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 200,
            'data': serializer.data,
            'message': 'success'
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            'code': 200,
            'data': {'id': serializer.instance.id},
            'message': '创建分类成功'
        })
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'code': 200,
            'message': '更新分类成功'
        })
        
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # 检查是否有关联的动态
        if hasattr(instance, 'dynamics') and instance.dynamics.exists():
            return Response({
                'code': 400,
                'message': '该分类下有动态，不能删除'
            })
        self.perform_destroy(instance)
        return Response({
            'code': 200,
            'message': '删除分类成功'
        })


class BlogCategoriesView(ViewSet):
    """
    前台获取分类列表API
    """
    permission_classes = [AllowAny]
    
    def list(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        response = Response({
            'code': 200,
            'message': 'success',
            'data': serializer.data
        })
        # 添加缓存控制头
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response