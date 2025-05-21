from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
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
            'message': 'success',
            'data': {
                'list': data,
                'total': self.page.paginator.count,
                'page': self.page.number,
                'pageSize': self.page_size
            }
        })

class CommentViewSet(ModelViewSet):
    queryset = Comment.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CommentPagination
    
    def get_permissions(self):
        # 如果是前台请求，允许匿名访问列表和创建
        if self.request.path.startswith('/blog'):
            return [AllowAny()]
        # 如果是后台请求，需要认证
        return super().get_permissions()
    
    def dispatch(self, request, *args, **kwargs):
        """重载dispatch方法，对前台请求跳过认证"""
        if request.path.startswith('/blog'):
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
        
        # 如果是前台请求，只返回已审核通过的评论
        if self.request.path.startswith('/blog'):
            queryset = queryset.filter(status='approved')
        
        # 过滤条件
        dynamic_id = self.request.query_params.get('dynamic_id')
        if dynamic_id:
            queryset = queryset.filter(dynamic_id=dynamic_id)
        
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
                'list': serializer.data,
                'total': queryset.count(),
                'page': 1,
                'pageSize': self.pagination_class.page_size
            }
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'code': 200,
                'message': 'success',
                'data': serializer.data
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
                'message': 'success',
                'data': serializer.data
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
            'message': 'success'
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

class BlogCommentView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        """获取评论列表"""
        dynamic_id = request.query_params.get('dynamic_id')
        if not dynamic_id:
            return Response({
                'code': 400,
                'message': 'dynamic_id 是必需的'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        queryset = Comment.objects.filter(
            dynamic_id=dynamic_id,
            status__in=['approved', 'pending']  # 同时获取已审核和待审核的评论
        ).order_by('-created_at')  # 按创建时间倒序排列
        
        serializer = CommentSerializer(queryset, many=True)
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'list': serializer.data,
                'total': queryset.count()
            }
        })
    
    def post(self, request):
        """创建评论"""
        print("收到 POST 请求:", request.data)  # 添加调试信息
        serializer = CommentCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                comment = serializer.save()
                return Response({
                    'code': 200,
                    'message': '评论提交成功',
                    'data': CommentSerializer(comment).data
                })
            except Exception as e:
                print("保存评论时出错:", str(e))  # 添加调试信息
                return Response({
                    'code': 500,
                    'message': f'保存评论失败: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        print("序列化器验证失败:", serializer.errors)  # 添加调试信息
        return Response({
            'code': 400,
            'message': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
