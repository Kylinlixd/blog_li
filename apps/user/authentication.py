from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
import jwt
from django.conf import settings
from datetime import datetime, timedelta
from .models import TokenBlacklist

class CustomJWTAuthentication(JWTAuthentication):
    """
    自定义JWT认证后端，添加黑名单检查
    """
    def authenticate(self, request):
        try:
            # 尝试使用父类的认证方法
            auth_result = super().authenticate(request)
            if auth_result is None:
                return None
                
            user, token = auth_result
            
            # 检查令牌是否即将过期（比如还有5分钟过期）
            exp = token.payload.get('exp')
            if exp:
                exp_datetime = datetime.fromtimestamp(exp)
                now = datetime.now()
                if exp_datetime - now < timedelta(minutes=5):
                    # 如果令牌即将过期，自动刷新
                    refresh_token = request.COOKIES.get('refresh_token')
                    if refresh_token:
                        try:
                            # 使用刷新令牌获取新的访问令牌
                            refresh = RefreshToken(refresh_token)
                            new_access_token = str(refresh.access_token)
                            
                            # 更新请求头中的访问令牌
                            request.META['HTTP_AUTHORIZATION'] = f'Bearer {new_access_token}'
                            
                            # 返回新的认证结果
                            return self.get_user(new_access_token), new_access_token
                        except (InvalidToken, TokenError):
                            pass
            
            # 检查token是否在黑名单中
            raw_token = self.get_raw_token(self.get_header(request))
            if raw_token is None:
                return None
            
            if TokenBlacklist.is_blacklisted(raw_token.decode()):
                raise InvalidToken('Token已被注销')
            
            return auth_result
            
        except (InvalidToken, TokenError) as e:
            # 如果是令牌过期错误，尝试使用刷新令牌
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                try:
                    refresh = RefreshToken(refresh_token)
                    new_access_token = str(refresh.access_token)
                    
                    # 更新请求头中的访问令牌
                    request.META['HTTP_AUTHORIZATION'] = f'Bearer {new_access_token}'
                    
                    # 返回新的认证结果
                    return self.get_user(new_access_token), new_access_token
                except (InvalidToken, TokenError):
                    pass
            
            # 如果刷新令牌也无效，则抛出异常
            raise InvalidToken(_('令牌无效或已过期，请重新登录'))
    
    def get_user(self, token):
        try:
            # 解码令牌
            payload = jwt.decode(
                token,
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