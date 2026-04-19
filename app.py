#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import logging
import sqlite3
import sys
import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_DB_PATH = Path(__file__).with_name("njoyemlak.db")
MAX_LIMIT = 200

logger = logging.getLogger("njoy_cli")


class AppError(Exception):
    """Application-level controlled error."""


@dataclass(frozen=True)
class Listing:
    ilan_id: int
    baslik: str
    fiyat: float
    ilce: str
    mahalle: str
    emlak_tipi: str
    brut_m2: int | None
    net_m2: int | None
    oda_sayisi: str | None
    danisman: str


@dataclass(frozen=True)
class AgentPortfolio:
    ad_soyad: str
    toplam_ilan: int
    toplam_portfoy: float | None


class NjoyRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        if not self._db_path.exists():
            raise AppError(f"Veritabanı bulunamadı: {self._db_path}")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        # Keep relational integrity checks active for every connection.
        conn.execute("PRAGMA foreign_keys = ON;")
        # Reduce transient lock errors during concurrent reads/writes.
        conn.execute("PRAGMA busy_timeout = 3000;")
        return conn

    def _timed_fetchall(
        self, conn: sqlite3.Connection, query: str, params: Sequence[object], op_name: str
    ) -> list[sqlite3.Row]:
        start = time.perf_counter()
        rows = conn.execute(query, params).fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("%s completed in %.2f ms", op_name, elapsed_ms)
        return rows

    def list_listings(self, limit: int, sort_by: str) -> list[Listing]:
        sort_map = {
            "fiyat_desc": "E.Fiyat DESC",
            "fiyat_asc": "E.Fiyat ASC",
            "m2_desc": "E.NetM2 DESC",
            "ilanid_asc": "E.IlanID ASC",
        }
        order_clause = sort_map.get(sort_by)
        if order_clause is None:
            raise AppError(f"Geçersiz sıralama: {sort_by}")

        query = f"""
            SELECT E.IlanID, E.Baslik, E.Fiyat, E.İlce, E.Mahalle, E.EmlakTipi,
                   E.BrutM2, E.NetM2, E.OdaSayisi, K.AdSoyad AS Danisman
            FROM Emlaklar E
            INNER JOIN Ekip K ON K.DanismanID = E.DanismanID
            ORDER BY {order_clause}
            LIMIT ?
        """
        with self._connect() as conn:
            rows = self._timed_fetchall(conn, query, (limit,), "list_listings")
        return [self._row_to_listing(row) for row in rows]

    def search(
        self,
        max_price: float | None,
        districts: Sequence[str] | None,
        feature: str | None,
        limit: int,
    ) -> list[Listing]:
        params: list[object] = []
        where_clauses: list[str] = []
        joins = ""

        if max_price is not None:
            where_clauses.append("E.Fiyat <= ?")
            params.append(max_price)

        if districts:
            placeholders = ", ".join("?" for _ in districts)
            where_clauses.append(f"E.İlce IN ({placeholders})")
            params.extend(districts)

        if feature:
            joins = """
                INNER JOIN Emlak_Ozellikleri EO ON EO.IlanID = E.IlanID
                INNER JOIN Ozellikler O ON O.OzellikID = EO.OzellikID
            """
            where_clauses.append("O.OzellikAdi = ?")
            params.append(feature)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT DISTINCT E.IlanID, E.Baslik, E.Fiyat, E.İlce, E.Mahalle, E.EmlakTipi,
                            E.BrutM2, E.NetM2, E.OdaSayisi, K.AdSoyad AS Danisman
            FROM Emlaklar E
            INNER JOIN Ekip K ON K.DanismanID = E.DanismanID
            {joins}
            {where_sql}
            ORDER BY E.Fiyat DESC
            LIMIT ?
        """
        params.append(limit)
        with self._connect() as conn:
            rows = self._timed_fetchall(conn, query, params, "search")
        return [self._row_to_listing(row) for row in rows]

    def agent_portfolios(self) -> list[AgentPortfolio]:
        query = """
            SELECT K.AdSoyad, COUNT(E.IlanID) AS ToplamIlan,
                   SUM(E.Fiyat) AS ToplamPortfoy
            FROM Ekip K
            LEFT JOIN Emlaklar E ON E.DanismanID = K.DanismanID
            GROUP BY K.AdSoyad
            ORDER BY ToplamPortfoy DESC
        """
        with self._connect() as conn:
            rows = self._timed_fetchall(conn, query, (), "agent_portfolios")
        return [
            AgentPortfolio(
                ad_soyad=row["AdSoyad"],
                toplam_ilan=row["ToplamIlan"],
                toplam_portfoy=row["ToplamPortfoy"],
            )
            for row in rows
        ]

    def benchmark(
        self, limit: int = 20, max_price: float = 50000, district: str = "Beyoğlu"
    ) -> dict[str, float]:
        metrics: dict[str, float] = {}
        start = time.perf_counter()
        self.list_listings(limit=limit, sort_by="fiyat_desc")
        metrics["list_ms"] = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        self.search(max_price=max_price, districts=[district], feature=None, limit=limit)
        metrics["search_ms"] = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        self.agent_portfolios()
        metrics["stats_ms"] = (time.perf_counter() - start) * 1000
        return metrics

    @staticmethod
    def _row_to_listing(row: sqlite3.Row) -> Listing:
        return Listing(
            ilan_id=row["IlanID"],
            baslik=row["Baslik"],
            fiyat=row["Fiyat"],
            ilce=row["İlce"],
            mahalle=row["Mahalle"],
            emlak_tipi=row["EmlakTipi"],
            brut_m2=row["BrutM2"],
            net_m2=row["NetM2"],
            oda_sayisi=row["OdaSayisi"],
            danisman=row["Danisman"],
        )


def format_table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    str_rows = [[str(c) if c is not None else "-" for c in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in str_rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def _fmt(row: Sequence[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    line = "-+-".join("-" * w for w in widths)
    rendered = [_fmt(list(headers)), line]
    rendered.extend(_fmt(row) for row in str_rows)
    return "\n".join(rendered)


def _add_common_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite db yolu")
    parser.add_argument("--limit", type=int, default=20, help="Maksimum kayıt sayısı")
    parser.add_argument(
        "--output",
        choices=["table", "json", "csv"],
        default="table",
        help="Çıktı formatı",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Njoy Emlak SQLite veritabanı için profesyonel CLI aracı"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_cmd = sub.add_parser("list", help="İlanları listele")
    _add_common_filters(list_cmd)
    list_cmd.add_argument(
        "--sort-by",
        choices=["fiyat_desc", "fiyat_asc", "m2_desc", "ilanid_asc"],
        default="fiyat_desc",
        help="Sıralama tipi",
    )

    search_cmd = sub.add_parser("search", help="Filtreli ilan araması")
    _add_common_filters(search_cmd)
    search_cmd.add_argument("--max-price", type=float, help="Maksimum fiyat")
    search_cmd.add_argument(
        "--district",
        action="append",
        dest="districts",
        help="İlçe filtresi (birden fazla verilebilir)",
    )
    search_cmd.add_argument("--feature", help="Özellik adına göre filtre")

    stats_cmd = sub.add_parser("stats", help="Danışman portföy istatistikleri")
    _add_common_filters(stats_cmd)

    benchmark_cmd = sub.add_parser("benchmark", help="Temel sorgu performans ölçümü")
    _add_common_filters(benchmark_cmd)
    benchmark_cmd.add_argument(
        "--bench-max-price",
        type=float,
        default=50000,
        help="Benchmark arama adımı için maksimum fiyat",
    )
    benchmark_cmd.add_argument(
        "--bench-district",
        default="Beyoğlu",
        help="Benchmark arama adımı için ilçe",
    )

    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.limit <= 0:
        raise AppError("--limit pozitif bir sayı olmalıdır.")
    if args.limit > MAX_LIMIT:
        raise AppError(f"--limit en fazla {MAX_LIMIT} olabilir.")
    if getattr(args, "max_price", None) is not None and args.max_price < 0:
        raise AppError("--max-price negatif olamaz.")
    if hasattr(args, "districts") and args.districts is not None:
        districts = [d.strip() for d in args.districts if d and d.strip()]
        if len(districts) != len(args.districts):
            raise AppError("--district boş veya sadece boşluk olamaz.")
        args.districts = list(dict.fromkeys(districts))
    if hasattr(args, "feature") and args.feature is not None:
        feature = args.feature.strip()
        if not feature:
            raise AppError("--feature boş olamaz.")
        args.feature = feature
    if hasattr(args, "bench_district"):
        args.bench_district = args.bench_district.strip()
        if not args.bench_district:
            raise AppError("--bench-district boş veya sadece boşluk olamaz.")


def _render_output(
    headers: Sequence[str], rows: list[Sequence[object]], output: str, empty_message: str
) -> str:
    if not rows:
        return empty_message
    if output == "table":
        return format_table(headers, rows)
    if output == "json":
        payload = [dict(zip(headers, row)) for row in rows]
        return json.dumps(payload, ensure_ascii=False, indent=2)
    if output == "csv":
        out = StringIO()
        writer = csv.writer(out)
        writer.writerow(headers)
        writer.writerows(rows)
        return out.getvalue().strip()
    raise AppError(f"Geçersiz çıktı formatı: {output}")


def cmd_list(repo: NjoyRepository, args: argparse.Namespace) -> str:
    items = repo.list_listings(limit=args.limit, sort_by=args.sort_by)
    headers = ["IlanID", "Başlık", "Fiyat", "İlçe", "Mahalle", "Tip", "Danışman"]
    rows = [
        (
            i.ilan_id,
            i.baslik,
            f"{i.fiyat:,.0f}",
            i.ilce,
            i.mahalle,
            i.emlak_tipi,
            i.danisman,
        )
        for i in items
    ]
    return _render_output(
        headers=headers,
        rows=rows,
        output=args.output,
        empty_message="Kayıt bulunamadı.",
    )


def cmd_search(repo: NjoyRepository, args: argparse.Namespace) -> str:
    items = repo.search(
        max_price=args.max_price,
        districts=args.districts,
        feature=args.feature,
        limit=args.limit,
    )
    headers = ["IlanID", "Başlık", "Fiyat", "İlçe", "Mahalle", "Tip"]
    rows = [
        (i.ilan_id, i.baslik, f"{i.fiyat:,.0f}", i.ilce, i.mahalle, i.emlak_tipi)
        for i in items
    ]
    return _render_output(
        headers=headers,
        rows=rows,
        output=args.output,
        empty_message="Filtrelere uygun kayıt bulunamadı.",
    )


def cmd_stats(repo: NjoyRepository, _args: argparse.Namespace) -> str:
    stats = repo.agent_portfolios()
    headers = ["Danışman", "İlan Sayısı", "Toplam Portföy (TL)"]
    rows = [
        (s.ad_soyad, s.toplam_ilan, f"{(s.toplam_portfoy or 0):,.0f}") for s in stats
    ]
    return _render_output(
        headers=headers,
        rows=rows,
        output=_args.output,
        empty_message="İstatistik bulunamadı.",
    )


def cmd_benchmark(repo: NjoyRepository, args: argparse.Namespace) -> str:
    metrics = repo.benchmark(
        limit=args.limit,
        max_price=args.bench_max_price,
        district=args.bench_district,
    )
    rows = [(name, f"{value:.2f}") for name, value in metrics.items()]
    return _render_output(
        headers=["Sorgu", "Süre (ms)"],
        rows=rows,
        output=args.output,
        empty_message="Benchmark verisi bulunamadı.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        validate_args(args)
        repo = NjoyRepository(args.db)
        handlers = {
            "list": cmd_list,
            "search": cmd_search,
            "stats": cmd_stats,
            "benchmark": cmd_benchmark,
        }
        handler = handlers.get(args.command)
        if handler is None:
            raise AppError(f"Desteklenmeyen komut: {args.command}")
        output = handler(repo, args)
        print(output)
        return 0
    except AppError as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 2
    except sqlite3.DatabaseError as exc:
        print(f"Veritabanı hatası: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
