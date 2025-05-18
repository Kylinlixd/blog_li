from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model, authenticate
from .serializers import (
    UserSerializer, UserLoginSerializer, UserRegisterSerializer,
    UserProfileSerializer, ChangePasswordSerializer, CustomTokenObtainPairSerializer
)
from datetime import timedelta
from django.conf import settings
from .models import TokenBlacklist
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _
from .authentication import CustomJWTAuthentication
import jwt

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomJWTAuthentication]
    
    def get_permissions(self):
        if self.action in ['login', 'register']:
            return [AllowAny()]
        return super().get_permissions()
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(username=username, password=password)
            if user:
                # 生成令牌
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
                
                # 创建响应
                response = Response({
                    'code': 200,
                    'data': {
                        'access': access_token,
                        'refresh': refresh_token
                    },
                    'message': '登录成功'
                })
                
                # 设置刷新令牌到 cookie
                response.set_cookie(
                    'refresh_token',
                    refresh_token,
                    httponly=True,  # 防止 JavaScript 访问
                    secure=not settings.DEBUG,  # 在生产环境中使用 HTTPS
                    samesite='Lax',  # 防止 CSRF 攻击
                    max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()  # 设置过期时间
                )
                
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
            # 生成令牌
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # 创建响应
            response = Response({
                'code': 200,
                'data': {
                    'access': access_token,
                    'refresh': refresh_token
                },
                'message': '注册成功'
            })
            
            # 设置刷新令牌到 cookie
            response.set_cookie(
                'refresh_token',
                refresh_token,
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax',
                max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()
            )
            
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
                # 将令牌加入黑名单
                TokenBlacklist.objects.create(token=token)
            
            # 清除刷新令牌 cookie
            response = Response({
                'code': 200,
                'message': '退出登录成功'
            })
            response.delete_cookie('refresh_token')
            return response
            
        except Exception as e:
            return Response({
                'code': 400,
                'message': str(e)
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
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(old_password):
            return Response({
                'code': 400,
                'message': '原密码错误'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        return Response({
            'code': 200,
            'message': '密码修改成功'
        })
    
    @action(detail=False, methods=['put'])
    def profile(self, request):
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'code': 200,
                'data': {
                    **serializer.data,
                    'created_at': user.date_joined,
                    'updated_at': user.last_login
                },
                'message': '个人信息更新成功'
            })
        else:
            return Response({
                'code': 400,
                'message': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer