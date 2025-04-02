from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from apps.user.serializers import LoginSerializer, UserSerializer, ChangePasswordSerializer, RegisterSerializer, ProfileUpdateSerializer
from rest_framework import status

# Create your views here.
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(**serializer.validated_data)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'code': 200,
                'data': {
                    'token': str(refresh.access_token),
                    'userInfo': UserSerializer(user).data
                },
                'message': '登录成功'
            })
        return Response({'code': 400, 'message': '用户名或密码错误'}, status=400)

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # 生成JWT Token
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'code': 200,
                'data': {
                    'token': str(refresh.access_token),
                    'userInfo': UserSerializer(user).data
                },
                'message': '注册成功'
            }, status=status.HTTP_201_CREATED)
        except serializers.ValidationError:
            return Response({
                'code': 400,
                'message': '用户名已存在或密码格式不正确'
            }, status=status.HTTP_400_BAD_REQUEST)

class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'code': 200,
            'data': UserSerializer(request.user).data,
            'message': '获取用户信息成功'
        })

class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'code': 200,
                'data': UserSerializer(request.user).data,
                'message': '个人资料更新成功'
            })
        return Response({
            'code': 400,
            'message': '数据验证失败',
            'error': {'details': serializer.errors}
        }, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data['oldPassword']):
            return Response({'code': 400, 'message': '旧密码错误'}, status=400)
        request.user.set_password(serializer.validated_data['newPassword'])
        request.user.save()
        return Response({'code': 200, 'message': '密码修改成功'})