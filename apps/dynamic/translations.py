#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文章机器翻译服务：provider 可插拔，结果缓存在 DynamicTranslation 表。

Provider 选择（settings.TRANSLATION_PROVIDER）：
- "auto"（默认）：配置了 TRANSLATION_API_KEY 走 OpenAI 兼容接口，否则走 Google 免费端点；
- "openai" / "google"：显式指定。
Google 端点无需密钥，属尽力而为的免费通道，必须配额控制：
- 每日生成篇数上限（TRANSLATION_DAILY_CAP，默认 120 篇，命中缓存不占额度）；
- 同一 IP 最小冷却间隔（TRANSLATION_IP_COOLDOWN 秒，默认 45 秒）。

Markdown 处理策略：按「围栏代码块 / 普通段落」切分，代码块原样保留，
仅翻译普通文本段，翻译后按原顺序拼回，保证正文结构、图片和代码不受损。
"""
import logging
import re
import time

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import Dynamic, DynamicTranslation

logger = logging.getLogger(__name__)

SUPPORTED_LANGS = {code: name for code, name in DynamicTranslation.LANG_CHOICES}


class TranslationUnavailable(Exception):
    """翻译服务不可用（未配置、配额用尽或上游失败）。"""


class RateLimited(TranslationUnavailable):
    """超出当日配额或 IP 冷却间隔。"""


def _provider_name():
    configured = getattr(settings, "TRANSLATION_PROVIDER", "auto")
    if configured in ("openai", "google"):
        return configured
    return "openai" if getattr(settings, "TRANSLATION_API_KEY", "") else "google"


def _check_quota(ip):
    today = timezone.localdate().isoformat()
    daily_key = f"translate:daily:{today}"
    if cache.get(daily_key, 0) >= getattr(settings, "TRANSLATION_DAILY_CAP", 120):
        raise RateLimited("今日机器翻译额度已用完，请明天再试或直接阅读原文")
    if ip:
        cooldown_key = f"translate:cooldown:{ip}"
        if not cache.add(cooldown_key, "1", getattr(settings, "TRANSLATION_IP_COOLDOWN", 45)):
            raise RateLimited("翻译请求太频繁，请稍等片刻再试")


def _count_quota():
    today = timezone.localdate().isoformat()
    daily_key = f"translate:daily:{today}"
    try:
        cache.incr(daily_key)
    except ValueError:
        cache.add(daily_key, 1, 86400)


def split_markdown(content):
    """把 Markdown 切成 (is_code, text) 段：围栏代码块原样保留，其余按空行分段。"""
    segments = []
    buf, in_fence, fence_mark = [], False, ""
    for line in content.splitlines(keepends=True):
        stripped = line.lstrip()
        if not in_fence and re.match(r"^(?:```|~~~)", stripped):
            if "".join(buf).strip():
                segments.append((False, "".join(buf)))
            buf, in_fence, fence_mark = [line], True, stripped[:3]
            continue
        if in_fence and stripped.startswith(fence_mark):
            buf.append(line)
            segments.append((True, "".join(buf)))
            buf, in_fence = [], False
            continue
        buf.append(line)
    if "".join(buf).strip():
        segments.append((False, "".join(buf)))
    # 空行分段的普通文本再按 1200 字合并/切块，减少上游请求次数
    chunks = []
    for is_code, text in segments:
        if is_code:
            chunks.append((True, text))
            continue
        for para in re.split(r"\n\s*\n", text.rstrip("\n")):
            if para.strip():
                chunks.append((False, para.strip()))
    return _merge_chunks(chunks)


def _merge_chunks(chunks, limit=1200):
    merged = []
    for is_code, text in chunks:
        if is_code or len(text) > limit:
            merged.append((is_code, text))
            continue
        if merged and not merged[-1][0] and len(merged[-1][1]) + len(text) + 2 <= limit:
            prev_is_code, prev = merged[-1]
            merged[-1] = (prev_is_code, f"{prev}\n\n{text}")
        else:
            merged.append((is_code, text))
    return merged


def _translate_google(text, lang):
    """Google 免费通道：dict-chrome-ex 客户端（gtx 客户端对机房 IP 已稳定 429）。

    响应两种形态都可能出现：["译文"] 或 [["译文","备选"],...]，做兼容解析。
    """
    last_error = None
    for attempt in range(2):
        try:
            resp = requests.get(
                "https://clients5.google.com/translate_a/t",
                params={"client": "dict-chrome-ex", "sl": "zh-CN", "tl": lang, "q": text},
                timeout=getattr(settings, "TRANSLATION_TIMEOUT", 25),
                headers={"User-Agent": "Mozilla/5.0 (compatible; SilentTimeBot/1.0)"},
            )
            if resp.status_code in (429, 500, 502, 503) and attempt == 0:
                time.sleep(1.5)
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, str):
                    return first
                if isinstance(first, list):
                    return "".join(part[0] for part in data if part and part[0])
            raise ValueError(f"无法解析的响应: {str(data)[:80]}")
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt == 0 and isinstance(exc, requests.RequestException):
                time.sleep(1.5)
                continue
            break
    raise last_error


def _translate_openai(text, lang):
    base = getattr(settings, "TRANSLATION_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    resp = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {settings.TRANSLATION_API_KEY}"},
        json={
            "model": getattr(settings, "TRANSLATION_OPENAI_MODEL", "gpt-4o-mini"),
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": (
                    "你是一名专业的技术博客翻译。把中文翻译成自然的"
                    f"{SUPPORTED_LANGS[lang]}。保留 Markdown 语法（标题、列表、表格、"
                    "链接、图片、粗体）原样不译 URL 与代码；技术术语首次出现可保留中文。"
                    "只输出译文，不要任何解释。"
                )},
                {"role": "user", "content": text},
            ],
        },
        timeout=getattr(settings, "TRANSLATION_TIMEOUT", 60),
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def translate_title_and_content(title, content, lang):
    """翻译标题与正文，返回 (title, content)。provider 故障抛 TranslationUnavailable。"""
    provider = _provider_name()
    translator = _translate_openai if provider == "openai" else _translate_google
    try:
        translated_title = translator(title[:200], lang)
        segments = split_markdown(content)
        translated = [
            _translate_openai(text, lang) if not is_code and provider == "openai"
            else (_translate_google(text, lang) if not is_code else text)
            for is_code, text in segments
        ]
    except requests.RequestException as exc:
        logger.warning("翻译上游失败（%s）: %s", provider, exc)
        raise TranslationUnavailable("翻译服务暂时不可用，请稍后再试") from exc
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("翻译上游响应异常（%s）: %s", provider, exc)
        raise TranslationUnavailable("翻译服务返回异常，请稍后再试") from exc
    return translated_title, "\n\n".join(translated)


def get_or_translate(dynamic: Dynamic, lang: str, ip: str = ""):
    """带缓存的翻译入口：命中缓存直接返回，否则生成并落库。"""
    if lang not in SUPPORTED_LANGS:
        raise ValueError(f"不支持的语言: {lang}")
    cached = DynamicTranslation.objects.filter(dynamic=dynamic, lang=lang).first()
    if cached is not None:
        return cached, False
    if dynamic.status != "published":
        raise Dynamic.DoesNotExist
    _check_quota(ip)
    title, content = translate_title_and_content(dynamic.title, dynamic.content, lang)
    _count_quota()
    translation = DynamicTranslation.objects.create(
        dynamic=dynamic, lang=lang, title=title[:400], content=content,
        provider=_provider_name(),
    )
    logger.info("文章翻译完成: dynamic=%s lang=%s provider=%s", dynamic.id, lang, translation.provider)
    return translation, True
