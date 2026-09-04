import csv
import ipaddress
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.access_log.models import IpGeoRecord


class Command(BaseCommand):
    help = "Import offline CIDR geo rows; each version replaces atomically."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--version", default="")

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        version = options.get("version") or ""
        if not path.exists():
            raise CommandError("CSV 文件不存在")

        rows = []
        seen = set()
        with path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            required = {"network", "country", "region", "city", "isp", "source", "version"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise CommandError("CSV 必须包含 network,country,region,city,isp,source,version 列")
            for index, row in enumerate(reader, start=2):
                network = ipaddress.ip_network((row.get("network") or "").strip(), strict=False)
                if any(network.overlaps(existing) for existing in seen):
                    raise CommandError(f"第 {index} 行与已有网段重叠")
                seen.add(network)
                rows.append(
                    {
                        "network": str(network),
                        "country": (row.get("country") or "").strip(),
                        "region": (row.get("region") or "").strip(),
                        "city": (row.get("city") or "").strip(),
                        "isp": (row.get("isp") or "").strip(),
                        "source": (row.get("source") or "").strip(),
                        "version": (row.get("version") or "").strip() or version,
                    }
                )

        selected_versions = {row["version"] for row in rows}
        if not selected_versions:
            raise CommandError("CSV 中没有可导入的数据")
        for target_version in selected_versions:
            IpGeoRecord.objects.filter(version=target_version).delete()
        IpGeoRecord.objects.bulk_create([IpGeoRecord(**row) for row in rows])
        self.stdout.write(self.style.SUCCESS(f"已导入 {len(rows)} 条 IP 归属记录"))
