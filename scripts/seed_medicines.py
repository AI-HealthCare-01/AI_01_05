import argparse
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tortoise import Tortoise

from app.core.logger import setup_logger
from app.db.databases import TORTOISE_ORM
from app.models.medicine import Medicine
from app.services.medicine_service import MedicineService

logger = setup_logger("seed_medicines")

_NULL_VALUES = {"-", ""}
_CHUNK_SIZE = 1_000
_DATA_DIR = Path(__file__).parent.parent / "data" / "medicines"
_POT_PATH = _DATA_DIR / "OpenData_PotOpenTabletIdntfcC20260313.csv"
_EASY_PATH = _DATA_DIR / "OpenData_EasyExcelListC20260313.csv"

_UPDATE_FIELDS = [
    "item_name",
    "entp_name",
    "print_front",
    "print_back",
    "drug_shape",
    "color_class",
    "efcy_qesitm",
    "use_method_qesitm",
    "item_image",
    "search_keyword",
]


class MedicineDataLoader:
    def __init__(self, pot_path: Path = _POT_PATH, easy_path: Path = _EASY_PATH) -> None:
        self._pot_path = pot_path
        self._easy_path = easy_path

    def load(self) -> list[dict]:
        pot = self._read_pot()
        easy = self._read_easy()
        return self._merge(pot, easy)

    def _read_pot(self) -> dict[str, dict]:
        rows: dict[str, dict] = {}
        with open(self._pot_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                seq = row["품목일련번호"].strip()
                if not seq:
                    continue
                rows[seq] = {
                    "item_seq": seq,
                    "item_name": self._clean(row.get("품목명", "")),
                    "entp_name": self._clean(row.get("업소명", "")),
                    "print_front": self._clean(row.get("표시앞", "")),
                    "print_back": self._clean(row.get("표시뒤", "")),
                    "drug_shape": self._clean(row.get("의약품제형", "")),
                    "color_class": self._clean(row.get("색상앞", "")),
                    "item_image": self._clean(row.get("큰제품이미지", "")),
                }
        return rows

    def _read_easy(self) -> dict[str, dict]:
        rows: dict[str, dict] = {}
        with open(self._easy_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                seq = row["품목일련번호"].strip()
                if not seq:
                    continue
                rows[seq] = {
                    "item_name": self._clean(row.get("제품명", "")),
                    "entp_name": self._clean(row.get("업체명", "")),
                    "efcy_qesitm": self._clean(row.get("이 약의 효능은 무엇입니까?", "")),
                    "use_method_qesitm": self._clean(row.get("이 약은 어떻게 사용합니까?", "")),
                    "item_image": self._clean(row.get("낱알이미지", "")),
                }
        return rows

    @staticmethod
    def _merge(pot: dict[str, dict], easy: dict[str, dict]) -> list[dict]:
        all_seqs = set(pot.keys()) | set(easy.keys())
        result: list[dict] = []
        for seq in all_seqs:
            p = pot.get(seq, {})
            e = easy.get(seq, {})
            item_name = p.get("item_name") or e.get("item_name") or ""
            record: dict = {
                "item_seq": seq,
                "item_name": item_name,
                "entp_name": p.get("entp_name") or e.get("entp_name"),
                "print_front": p.get("print_front"),
                "print_back": p.get("print_back"),
                "drug_shape": p.get("drug_shape"),
                "color_class": p.get("color_class"),
                "efcy_qesitm": e.get("efcy_qesitm"),
                "use_method_qesitm": e.get("use_method_qesitm"),
                "item_image": p.get("item_image") or e.get("item_image"),
                "search_keyword": MedicineDataLoader._make_search_keyword(item_name),
            }
            result.append(record)
        return result

    @staticmethod
    def _clean(value: str) -> str | None:
        v = value.strip()
        return None if v in _NULL_VALUES else v

    @staticmethod
    def _make_search_keyword(item_name: str) -> str | None:
        if not item_name:
            return None
        return MedicineService._normalize_keyword(item_name) or None


async def _upsert_chunk(rows: list[dict]) -> None:
    await Medicine.bulk_create(
        [Medicine(**r) for r in rows],
        on_conflict=["item_seq"],
        update_fields=_UPDATE_FIELDS,
    )


async def seed(db_host: str | None = None) -> None:
    config = TORTOISE_ORM
    if db_host:
        config["connections"]["default"]["credentials"]["host"] = db_host
        logger.info("DB host override: %s", db_host)

    await Tortoise.init(config=config)

    loader = MedicineDataLoader()
    rows = loader.load()
    total = len(rows)
    logger.info("총 %d건 적재 시작", total)

    loaded = 0
    for i in range(0, total, _CHUNK_SIZE):
        chunk = rows[i : i + _CHUNK_SIZE]
        try:
            await _upsert_chunk(chunk)
            loaded += len(chunk)
            logger.info("  %d / %d 완료", loaded, total)
        except Exception as exc:
            logger.error("chunk %d 실패: %s", i, exc)
            raise SystemExit(1) from exc

    logger.info("적재 완료: %d건", loaded)
    await Tortoise.close_connections()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-host", default=None, help="DB host override (예: localhost)")
    args = parser.parse_args()
    asyncio.run(seed(db_host=args.db_host))
