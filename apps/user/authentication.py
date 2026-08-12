from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.utils.translation import gettext_lazy as _
import jwt
from django.conf import settings
from .models import TokenBlacklist
from blog.request_utils import is_public_blog_request

class CustomJWTAuthentication(JWTAuthentication):
    """
    自定义JWT认证后端，添加黑名单检查
    """
    def authenticate(self, request):
        # 公开博客接口不应因旧页面携带的失效管理令牌而变成 401。
        # 公开接口本身不依赖登录态，直接按匿名请求继续权限判断。
        if is_public_blog_request(request):
            return None

        auth_result = super().authenticate(request)
        if auth_result is None:
            return None

        raw_token = self.get_raw_token(self.get_header(request))
        if raw_token is not None and TokenBlacklist.is_blacklisted(raw_token.decode()):
            raise InvalidToken('Token已被注销')
        return auth_result
    
    def get_user(self, token):
        try:
            payload = token.payload if hasattr(token, 'payload') else jwt.decode(
                str(token),
                settings.SIMPLE_JWT['SIGNING_KEY'],
                algorithms=[settings.SIMPLE_JWT['ALGORITHM']]
            )
            
            # 获取用户ID
            user_id = payload.get('user_id')
            if user_id is None:
                raise InvalidToken(_('令牌中缺少用户ID'))
            
            # 获取用户对象
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            return user
            
        except jwt.ExpiredSignatureError:
            raise InvalidToken(_('令牌已过期'))
        except jwt.InvalidTokenError:
            raise InvalidToken(_('令牌无效'))
        except User.DoesNotExist:
            raise InvalidToken(_('用户不存在')) 
