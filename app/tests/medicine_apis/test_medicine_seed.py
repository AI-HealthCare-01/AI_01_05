from tortoise.contrib.test import TestCase

from app.models.medicine import Medicine
from app.services.medicine_service import MedicineService

# ---------------------------------------------------------------------------
# 단위 테스트 — DB 불필요
# ---------------------------------------------------------------------------


class TestMedicineCsvLoaderUnit:
    def test_normalize_null_values(self):
        from scripts.seed_medicines import MedicineCsvLoader

        clean = MedicineCsvLoader._clean
        assert clean("-") is None
        assert clean("") is None
        assert clean("  ") is None
        assert clean("타이레놀") == "타이레놀"
        assert clean("  타이레놀  ") == "타이레놀"

    def test_search_keyword_matches_service_normalize(self):
        from scripts.seed_medicines import MedicineCsvLoader

        names = [
            "타이레놀정500밀리그램",
            "아스피린100mg",
            "게보린정",
            "세티리진염산염10mg정",
        ]
        for name in names:
            assert MedicineCsvLoader._make_search_keyword(name) == MedicineService._normalize_keyword(name)

    def test_full_outer_join_preserves_easy_only_records(self):
        from scripts.seed_medicines import MedicineCsvLoader

        pot = {
            "001": {"item_seq": "001", "item_name": "약A", "entp_name": "회사A"},
        }
        easy = {
            "001": {"efcy_qesitm": "효능A", "use_method_qesitm": "사용법A", "item_name": "약A", "entp_name": "회사A"},
            "002": {"efcy_qesitm": "효능B", "use_method_qesitm": "사용법B", "item_name": "약B", "entp_name": "회사B"},
        }
        result = MedicineCsvLoader._merge(pot, easy)
        seqs = {r["item_seq"] for r in result}
        assert "001" in seqs
        assert "002" in seqs  # EasyExcel에만 있는 레코드 보존

    def test_merge_prefers_pot_image_over_easy(self):
        from scripts.seed_medicines import MedicineCsvLoader

        pot = {"001": {"item_seq": "001", "item_name": "약A", "entp_name": "회사A", "item_image": "https://pot.img"}}
        easy = {
            "001": {"item_name": "약A", "entp_name": "회사A", "item_image": "https://easy.img", "efcy_qesitm": "효능"}
        }
        result = MedicineCsvLoader._merge(pot, easy)
        assert result[0]["item_image"] == "https://pot.img"


# ---------------------------------------------------------------------------
# 통합 테스트 — SQLite in-memory DB 사용
# ---------------------------------------------------------------------------


class TestMedicineSeedIntegration(TestCase):
    async def test_seed_idempotent(self):
        """동일 데이터 2회 적재 시 레코드 수 동일 (멱등성)"""
        from scripts.seed_medicines import _upsert_chunk

        rows = [
            {
                "item_seq": "SEED001",
                "item_name": "테스트정10mg",
                "search_keyword": "테스트정",
                "entp_name": "테스트제약",
                "print_front": None,
                "print_back": None,
                "drug_shape": "원형",
                "color_class": "하양",
                "efcy_qesitm": "두통에 사용합니다.",
                "use_method_qesitm": "1일 3회 복용",
                "item_image": "https://example.com/img.jpg",
            }
        ]

        await _upsert_chunk(rows)
        await _upsert_chunk(rows)  # 2회 실행

        count = await Medicine.filter(item_seq="SEED001").count()
        assert count == 1
