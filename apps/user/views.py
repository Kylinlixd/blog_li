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

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'login', 'register']:
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
                    return Response({
                        'code': 200,
                        'data': {
                            'token': str(CustomTokenObtainPairSerializer.get_token(user)),
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
            return Response({
                'code': 400,
                'message': serializer.errors,
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
            return Response({
                'code': 200,
                'data': {
                    'token': str(CustomTokenObtainPairSerializer.get_token(user)),
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

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer