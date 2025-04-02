from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from apps.user.serializers import LoginSerializer,UserSerializer,ChangePasswordSerializer

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
                }
            })
        return Response({'code': 400, 'message': 'Invalid credentials'}, status=400)

class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'code': 200,
            'data': UserSerializer(request.user).data
        })

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data['old_password']):
            return Response({'code': 400, 'message': '旧密码错误'}, status=400)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'code': 200, 'message': '密码修改成功'})