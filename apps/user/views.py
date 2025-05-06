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

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'login', 'register', 'logout']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        try:
            print(f"登录请求数据: {request.data}")  # 打印请求数据
            serializer = UserLoginSerializer(data=request.data)
            if serializer.is_valid():
                username = serializer.validated_data['username']
                password = serializer.validated_data['password']
                
                # 检查用户名和密码是否为空
                if not username or not password:
                    return Response({
                        'code': 400,
                        'message': '用户名和密码不能为空',
                        'data': None
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                print(f"尝试认证用户: {username}")  # 打印用户名
                user = authenticate(username=username, password=password)
                if user:
                    print(f"用户认证成功: {username}")  # 打印认证成功
                    if not user.is_active:
                        print(f"用户被禁用: {username}")  # 打印用户被禁用
                        return Response({
                            'code': 403,
                            'message': '用户已被禁用',
                            'data': None
                        }, status=status.HTTP_403_FORBIDDEN)
                    
                    # 获取JWT令牌对
                    token = CustomTokenObtainPairSerializer.get_token(user)
                    refresh_token = str(token)
                    access_token = str(token.access_token)
                    
                    return Response({
                        'code': 200,
                        'data': {
                            'token': {
                                'access': access_token,
                                'refresh': refresh_token
                            },
                            'userInfo': UserSerializer(user).data
                        },
                        'message': '登录成功'
                    })
                print(f"用户认证失败: {username}")  # 打印认证失败
                return Response({
                    'code': 401,
                    'message': '用户名或密码错误',
                    'data': None
                }, status=status.HTTP_401_UNAUTHORIZED)
            print(f"数据验证失败: {serializer.errors}")  # 打印验证错误
            
            # 处理验证错误
            if serializer.errors:
                # 获取第一个字段的第一个错误
                field = next(iter(serializer.errors))
                if isinstance(serializer.errors[field], list) and serializer.errors[field]:
                    error_message = f"{field}字段错误: {serializer.errors[field][0]}"
                else:
                    error_message = f"{field}字段错误: {serializer.errors[field]}"
            else:
                error_message = '请求数据无效'
                    
            return Response({
                'code': 400,
                'message': error_message,
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"登录异常: {str(e)}")  # 打印异常信息
            return Response({
                'code': 500,
                'message': str(e),
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # 获取JWT令牌对
            token = CustomTokenObtainPairSerializer.get_token(user)
            refresh_token = str(token)
            access_token = str(token.access_token)
            
            return Response({
                'code': 200,
                'data': {
                    'token': {
                        'access': access_token,
                        'refresh': refresh_token
                    },
                    'userInfo': UserSerializer(user).data
                },
                'message': '注册成功'
            })
        return Response({
            'code': 400,
            'message': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def info(self, request):
        try:
            print(f"用户信息请求开始 ==================")
            print(f"请求用户: {request.user}")
            print(f"请求用户ID: {request.user.id if request.user else None}")
            print(f"请求用户是否认证: {request.user.is_authenticated}")
            print(f"请求头: {request.headers}")
            
            user = request.user
            if not user.is_authenticated:
                print("用户未认证")
                return Response({
                    'code': 401,
                    'message': '用户未登录',
                    'data': None
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            print(f"用户对象属性: {dir(user)}")
            print(f"用户字段值:")
            for field in ['username', 'nickname', 'email', 'avatar', 'bio', 'role', 'permissions']:
                print(f"{field}: {getattr(user, field, None)}")
                
            serializer = UserSerializer(user)
            print(f"序列化数据: {serializer.data}")
            
            response_data = {
                'code': 200,
                'data': serializer.data,
                'message': '获取用户信息成功'
            }
            print(f"响应数据: {response_data}")
            print(f"用户信息请求结束 ==================")
            return Response(response_data)
            
        except Exception as e:
            print(f"获取用户信息异常: {str(e)}")
            print(f"异常类型: {type(e)}")
            print(f"异常详情: {e.__dict__}")
            import traceback
            print(f"异常堆栈: {traceback.format_exc()}")
            return Response({
                'code': 500,
                'message': str(e),
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['put'])
    def password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({
                    'code': 400,
                    'message': '旧密码错误'
                }, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({
                'code': 200,
                'message': '密码修改成功'
            })
        return Response({
            'code': 400,
            'message': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['put'])
    def profile(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'code': 200,
                'data': UserSerializer(request.user).data,
                'message': '个人资料更新成功'
            })
        return Response({
            'code': 400,
            'message': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        # JWT是无状态的，真正的登出需要前端移除存储的token
        
        try:
            # 获取Authorization头中的token
            auth_header = request.headers.get('Authorization', '')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                
                # 获取token的过期时间
                expires_delta = getattr(settings, 'SIMPLE_JWT', {}).get(
                    'ACCESS_TOKEN_LIFETIME', timedelta(minutes=15)
                )
                
                # 将token加入黑名单
                TokenBlacklist.add_token_to_blacklist(token, expires_delta)
                print(f"用户登出，token已加入黑名单: {token[:10]}...")
                
                # 清理过期的token
                deleted_count = TokenBlacklist.clean_expired_tokens()
                if deleted_count and deleted_count[0] > 0:
                    print(f"已清理 {deleted_count[0]} 个过期token")
            
            return Response({
                'code': 200,
                'message': '退出登录成功',
                'data': None
            })
        except Exception as e:
            print(f"登出异常: {str(e)}")
            # 即使发生异常，仍然返回成功，因为主要是前端清除token
            return Response({
                'code': 200,
                'message': '退出登录成功',
                'data': None
            })

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer