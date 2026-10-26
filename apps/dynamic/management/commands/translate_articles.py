from time import sleep

from django.core.management.base import BaseCommand

from apps.dynamic.models import Dynamic
from apps.dynamic.translations import (
    SUPPORTED_LANGS,
    RateLimited,
    TranslationUnavailable,
    get_or_translate,
)


class Command(BaseCommand):
    help = "批量预翻译已发布文章（结果缓存进 dynamic_translation，公开接口直接读缓存）"

    def add_arguments(self, parser):
        parser.add_argument("--lang", required=True, choices=sorted(SUPPORTED_LANGS))
        parser.add_argument("--latest", type=int, default=0, help="只翻译最新 N 篇")
        parser.add_argument("--pk", type=int, action="append", help="指定文章 id，可重复传")
        parser.add_argument("--sleep", type=float, default=1.0, help="每篇之间的间隔秒数，礼貌对待上游")

    def handle(self, *args, **opts):
        lang = opts["lang"]
        if opts["pk"]:
            queryset = Dynamic.objects.filter(pk__in=opts["pk"], status="published")
        elif opts["latest"]:
            queryset = Dynamic.objects.filter(status="published").order_by("-created_at")[: opts["latest"]]
        else:
            queryset = Dynamic.objects.filter(status="published").order_by("-created_at")
        ok = skip = fail = 0
        consecutive_failures = 0
        for dynamic in queryset.iterator():
            try:
                _, created = get_or_translate(dynamic, lang)
            except RateLimited as exc:
                self.stdout.write(self.style.WARNING(f"#{dynamic.pk} 触发限额，提前收工: {exc}"))
                break
            except TranslationUnavailable as exc:
                fail += 1
                consecutive_failures += 1
                self.stdout.write(self.style.ERROR(f"#{dynamic.pk} 失败: {exc}"))
                if consecutive_failures >= 5:
                    self.stdout.write(self.style.ERROR("连续失败 5 次，停止执行"))
                    break
                sleep(opts["sleep"])
                continue
            consecutive_failures = 0
            if created:
                ok += 1
                self.stdout.write(self.style.SUCCESS(f"#{dynamic.pk} 已翻译《{dynamic.title[:24]}》"))
            else:
                skip += 1
            if opts["sleep"]:
                sleep(opts["sleep"])
        self.stdout.write(f"完成：新翻译 {ok} 篇，已有缓存 {skip} 篇，失败 {fail} 篇")
