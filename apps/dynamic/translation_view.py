from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Dynamic
from .translations import RateLimited, TranslationUnavailable, get_or_translate


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        # 与限流/访问日志同口径：XFF 最后一跳由 nginx 追加，才是可信来源
        return xff.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "")


class DynamicTranslationView(APIView):
    """公开文章翻译：?lang=en|ja|ko|es|fr，首次生成较慢（10~40s），之后读缓存。"""

    permission_classes = []

    def get(self, request, pk=None):
        lang = (request.query_params.get("lang") or "").strip().lower()
        dynamic = (
            Dynamic.objects.filter(pk=pk, status="published")
            .only("id", "title", "content")
            .first()
        )
        if dynamic is None:
            return Response(
                {"code": 404, "message": "文章不存在", "data": None}, status=status.HTTP_404_NOT_FOUND
            )
        if not lang:
            return Response(
                {"code": 400, "message": "缺少 lang 参数", "data": None}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            translation, _ = get_or_translate(dynamic, lang, ip=_client_ip(request))
        except RateLimited as exc:
            return Response(
                {"code": 429, "message": str(exc), "data": None}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except TranslationUnavailable as exc:
            return Response(
                {"code": 503, "message": str(exc), "data": None}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except ValueError as exc:
            return Response(
                {"code": 400, "message": str(exc), "data": None}, status=status.HTTP_400_BAD_REQUEST
            )
        response = Response({
            "code": 200,
            "message": "success",
            "data": {
                "lang": translation.lang,
                "title": translation.title,
                "content": translation.content,
                "provider": translation.provider,
            },
        })
        # 翻译内容更新频率低，允许边缘/浏览器短缓存，降低重复生成压力
        response["Cache-Control"] = "public, max-age=600"
        return response
