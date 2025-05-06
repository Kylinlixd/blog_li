from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from .models import TokenBlacklist

class CustomJWTAuthentication(JWTAuthentication):
    """
    自定义JWT认证后端，添加黑名单检查
    """
    def authenticate(self, request):
        # 先调用父类的authenticate
        auth_result = super().authenticate(request)
        
        # 如果认证失败，直接返回
        if auth_result is None:
            return None
            
        user, token = auth_result
        
        # 获取原始token字符串
        raw_token = self.get_raw_token(self.get_header(request))
        if raw_token is None:
            return None
            
        # 检查token是否在黑名单中
        if TokenBlacklist.is_blacklisted(raw_token.decode()):
            raise InvalidToken('Token已被注销')
            
        return auth_result 