from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from apps.user.permissions import IsContentEditor
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Case, When, Value, BooleanField, Max, Subquery
from django.db.models.functions import Coalesce
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from .models import Comment, CommentReadReceipt, CommentReadState
from .serializers import (
    CommentSerializer, CommentCreateSerializer,
    CommentUpdateSerializer, PublicCommentSerializer
)
from blog.request_utils import is_public_blog_request

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
    queryset = Comment.objects.select_related('author', 'dynamic')
    permission_classes = [IsContentEditor]
    pagination_class = CommentPagination
    throttle_scope = 'public_comment'
    
    def get_permissions(self):
        if self.action in {'unread_summary', 'mark_read'}:
            return super().get_permissions()
        # 如果是前台请求，允许匿名访问列表和创建
        if is_public_blog_request(self.request):
            return [AllowAny()]
        # 如果是后台请求，需要认证
        return super().get_permissions()

    def get_throttles(self):
        if self.action == 'create' and is_public_blog_request(self.request):
            return [ScopedRateThrottle()]
        return []
    
    def dispatch(self, request, *args, **kwargs):
        """重载dispatch方法，对前台请求跳过认证"""
        if is_public_blog_request(request):
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
    
        # 前台请求只返回已审核的评论
        if is_public_blog_request(self.request):
            queryset = queryset.filter(status='approved', dynamic__status='published')
        else:
            # 后台请求根据 status 参数过滤
            status = self.request.query_params.get('status')
            if status:
                queryset = queryset.filter(status=status)
            state = CommentReadState.objects.filter(user=self.request.user).values('last_seen_comment_id')[:1]
            seen_id = Coalesce(Subquery(state), Value(0))
            queryset = queryset.annotate(is_unread=Case(
                When(author=self.request.user, then=Value(False)),
                When(status='rejected', then=Value(False)),
                When(id__gt=seen_id, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ))
            if self.request.query_params.get('unread') == '1':
                queryset = queryset.filter(is_unread=True)
    
        # 过滤条件
        dynamic_id = self.request.query_params.get('dynamic_id')
        if dynamic_id:
            queryset = queryset.filter(dynamic_id=dynamic_id)
    
        # 作者搜索
        author = self.request.query_params.get('author')
        if author:
            queryset = queryset.filter(
                Q(author__username__icontains=author) |
                Q(nickname__icontains=author)
            )
    
        return queryset

    def _read_state(self, user):
        state, _ = CommentReadState.objects.get_or_create(user=user, defaults={'last_seen_comment_id': 0})
        return state

    def _unread_queryset(self, user):
        state = CommentReadState.objects.filter(user=user).values('last_seen_comment_id')[:1]
        seen_id = Coalesce(Subquery(state), Value(0))
        return Comment.objects.select_related('author', 'dynamic').filter(
            id__gt=seen_id,
            status__in=['pending', 'approved'],
        ).exclude(author=user)

    def _notification_payload(self, user):
        state = self._read_state(user)
        latest_id = self._unread_queryset(user).aggregate(latest=Max('id'))['latest']
        unread_count = self._unread_queryset(user).count()
        return {
            'unread_count': unread_count,
            'latest_comment_id': latest_id or state.last_seen_comment_id or 0,
            'last_seen_comment_id': state.last_seen_comment_id,
            'initialized': bool(state.initialized_at),
        }

    @action(detail=False, methods=['get'], url_path='unread-summary')
    def unread_summary(self, request):
        return Response({'code': 200, 'message': 'success', 'data': self._notification_payload(request.user)})

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        latest_id = request.data.get('latest_comment_id')
        ids = request.data.get('ids', [])
        if latest_id is None:
            if not isinstance(ids, list) or len(ids) > 100:
                return Response({'code': 400, 'message': 'ids 必须是最多 100 个评论 ID 的数组'}, status=status.HTTP_400_BAD_REQUEST)
            latest_id = max([int(value) for value in ids if str(value).isdigit()] or [0])
        try:
            latest_id = int(latest_id)
        except (TypeError, ValueError):
            return Response({'code': 400, 'message': 'latest_comment_id 必须是数字'}, status=status.HTTP_400_BAD_REQUEST)
        if latest_id < 0:
            return Response({'code': 400, 'message': 'latest_comment_id 不能为负数'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            state = self._read_state(request.user)
            previous = state.last_seen_comment_id
            # Capture legacy rows before advancing the cursor; after the update
            # they are intentionally no longer part of the unread queryset.
            visible_ids = set()
            if isinstance(ids, list) and ids:
                visible_ids = set(self._unread_queryset(request.user).filter(id__in=ids).values_list('id', flat=True))
            if latest_id > previous:
                state.last_seen_comment_id = latest_id
                state.initialized_at = state.initialized_at or timezone.now()
                state.save(update_fields=['last_seen_comment_id', 'initialized_at', 'updated_at'])
            # Keep the legacy receipt for older clients/tests during the migration window.
            if visible_ids:
                CommentReadReceipt.objects.bulk_create(
                    [CommentReadReceipt(user=request.user, comment_id=comment_id) for comment_id in visible_ids],
                    ignore_conflicts=True,
                )
        payload = self._notification_payload(request.user)
        payload['marked'] = max(0, latest_id - previous) if latest_id is not None else 0
        return Response({'code': 200, 'message': 'success', 'data': payload})

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
    throttle_scope = 'public_comment'

    def get_throttles(self):
        return [ScopedRateThrottle()] if self.request.method == 'POST' else []
    
    def get(self, request):
        """获取评论列表"""
        dynamic_id = request.query_params.get('dynamic_id')
        if not dynamic_id:
            return Response({
                'code': 400,
                'message': 'dynamic_id 是必需的'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # 待审核评论仅对提交者返回，不进入公开列表。
        queryset = Comment.objects.filter(
            dynamic_id=dynamic_id,
            dynamic__status='published',
            status='approved'
        ).select_related('author').order_by('-created_at')
        
        thread_mode = request.query_params.get('thread') == '1'
        if thread_mode:
            root_queryset = queryset.filter(parent__isnull=True).order_by('-created_at', '-id')
            page_size = min(max(int(request.query_params.get('pageSize', 10)), 1), 50)
            page = max(int(request.query_params.get('page', 1)), 1)
            start = (page - 1) * page_size
            roots = list(root_queryset[start:start + page_size])
            payload = []
            for root in roots:
                item = PublicCommentSerializer(root).data
                replies = list(queryset.filter(parent_id=root.id).order_by('created_at', 'id')[:3])
                item['replies_preview'] = PublicCommentSerializer(replies, many=True).data
                item['reply_count'] = queryset.filter(parent_id=root.id).count()
                payload.append(item)
            total = root_queryset.count()
            return Response({
                'code': 200,
                'message': 'success',
                'data': {
                    'list': payload,
                    'total': total,
                    'commentTotal': queryset.count(),
                    'page': page,
                    'pageSize': page_size,
                },
            })

        serializer = PublicCommentSerializer(queryset, many=True)
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'list': serializer.data,
                'total': queryset.count(),
                'page': 1,
                'pageSize': queryset.count(),
            }
        })
    
    def post(self, request):
        """创建评论"""
        serializer = CommentCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()
        return Response({
            'code': 200,
            'message': '评论提交成功',
            'data': PublicCommentSerializer(comment).data
        })
