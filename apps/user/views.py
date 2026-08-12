from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from .serializers import (
    UserSerializer, UserLoginSerializer, UserRegisterSerializer,
    UserProfileSerializer, ChangePasswordSerializer, CustomTokenObtainPairSerializer
)
from datetime import datetime, timedelta, timezone
from django.conf import settings
from .models import TokenBlacklist
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.utils.translation import gettext_lazy as _
from .authentication import CustomJWTAuthentication
from .permissions import IsUserAdmin
import jwt
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomJWTAuthentication]

    @staticmethod
    def _serializer_message(errors):
        return '；'.join(
            f'{field}: {"、".join(str(item) for item in messages)}'
            for field, messages in errors.items()
        )
    
    def get_permissions(self):
        if self.action == 'login':
            return [AllowAny()]
        if self.action == 'register':
            return [IsUserAdmin()]
        if self.action in {'list', 'retrieve', 'create', 'update', 'partial_update', 'destroy'}:
            return [IsUserAdmin()]
        return super().get_permissions()

    @staticmethod
    def _set_refresh_cookie(response, refresh_token):
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
            path='/',
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        )
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username'].strip()
            password = serializer.validated_data['password']
            
            user = authenticate(username=username, password=password)
            # 修改用户名后，允许使用当前邮箱或昵称登录，避免旧用户名缓存导致账号无法找回。
            if user is None:
                candidate = User.objects.filter(email__iexact=username).first()
                if candidate is None:
                    candidate = User.objects.filter(nickname=username).first()
                if candidate is not None and candidate.check_password(password):
                    user = candidate
            if user:
                # 生成令牌
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)

                response = Response({
                    'code': 200,
                    'data': {
                        'access': access_token
                    },
                    'message': '登录成功'
                })
                self._set_refresh_cookie(response, refresh_token)
                return response
            else:
                return Response({
                    'code': 400,
                    'message': '用户名或密码错误'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'code': 400,
                'message': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            response = Response({
                'code': 200,
                'data': {
                    'access': access_token
                },
                'message': '注册成功'
            })
            self._set_refresh_cookie(response, refresh_token)
            return response
        else:
            return Response({
                'code': 400,
                'message': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        try:
            # 获取当前访问令牌
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                TokenBlacklist.add_token_to_blacklist(token)

            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token and not TokenBlacklist.is_blacklisted(refresh_token):
                try:
                    refresh = RefreshToken(refresh_token)
                    exp = refresh.get('exp')
                    expires_delta = max(
                        timedelta(seconds=1),
                        datetime.fromtimestamp(exp, tz=timezone.utc) - datetime.now(timezone.utc),
                    )
                    TokenBlacklist.add_token_to_blacklist(refresh_token, expires_delta)
                except (TokenError, ValueError, TypeError):
                    pass
            
            # 清除刷新令牌 cookie
            response = Response({
                'code': 200,
                'message': '退出登录成功'
            })
            response.delete_cookie('refresh_token', path='/')
            return response
            
        except Exception as e:
            logger.warning('Logout failed: %s', e)
            return Response({
                'code': 400,
                'message': '退出登录失败，请稍后重试'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def info(self, request):
        serializer = self.get_serializer(request.user)
        return Response({
            'code': 200,
            'data': serializer.data,
            'message': 'success'
        })
    
    @action(detail=False, methods=['put'])
    def password(self, request):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'code': 400, 'message': self._serializer_message(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        if not user.check_password(old_password):
            return Response({
                'code': 400,
                'message': '原密码错误'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user)
        except Exception as exc:
            return Response({
                'code': 400,
                'message': exc.messages if hasattr(exc, 'messages') else str(exc)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save(update_fields=['password', 'updated_at'] if hasattr(user, 'updated_at') else ['password'])
        
        return Response({
            'code': 200,
            'message': '密码修改成功'
        })
    
    @action(detail=False, methods=['put'])
    def profile(self, request):
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            user.refresh_from_db()
            return Response({
                'code': 200,
                'data': {
                    **UserSerializer(user).data,
                    'created_at': user.date_joined,
                    'updated_at': user.last_login
                },
                'message': '个人信息更新成功'
            })
        else:
            return Response({
                'code': 400,
                'message': self._serializer_message(serializer.errors)
            }, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class CookieTokenRefreshView(APIView):
    """使用 HttpOnly Cookie 轮换 refresh token，不把长期令牌返回给前端脚本。"""

    permission_classes = [AllowAny]

    def post(self, request):
        raw_token = request.COOKIES.get('refresh_token')
        if not raw_token or TokenBlacklist.is_blacklisted(raw_token):
            return Response({'code': 401, 'message': '刷新令牌无效或已过期'}, status=401)

        try:
            refresh = RefreshToken(raw_token)
            user_id = refresh.get('user_id')
            user = User.objects.get(pk=user_id, is_active=True)
            exp = refresh.get('exp')
            expires_delta = max(
                timedelta(seconds=1),
                datetime.fromtimestamp(exp, tz=timezone.utc) - datetime.now(timezone.utc),
            )
            TokenBlacklist.add_token_to_blacklist(raw_token, expires_delta)
            next_refresh = RefreshToken.for_user(user)
            response = Response({
                'code': 200,
                'data': {'access': str(next_refresh.access_token)},
                'message': '令牌刷新成功',
            })
            UserViewSet._set_refresh_cookie(response, str(next_refresh))
            return response
        except (TokenError, User.DoesNotExist, ValueError, TypeError):
            return Response({'code': 401, 'message': '刷新令牌无效或已过期'}, status=401)
