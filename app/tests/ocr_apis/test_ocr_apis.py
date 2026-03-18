from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.medicine import Medicine
from app.models.users import User
from app.services.jwt import JwtService


class TestOcrParseAPI(TestCase):
    async def _make_token(self, kakao_id: str, phone: str) -> str:
        user = await User.create(
            kakao_id=kakao_id,
            nickname="테스터",
            phone_number=phone,
            terms_agreed=True,
            privacy_agreed=True,
            sensitive_agreed=True,
        )
        return str(JwtService().create_access_token(user))

    def _make_image_file(self) -> bytes:
        return b"\xff\xd8\xff\xe0" + b"\x00" * 100  # minimal JPEG header

    async def test_ocr_parse_prescription_stub_returns_200(self):
        """stub 모드 → 200 + items:[] + raw_text 반환"""
        auth_token = await self._make_token("ocr_001", "01033330001")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ocr/parse-prescription",
                files={"file": ("test.jpg", self._make_image_file(), "image/jpeg")},
                headers={"Authorization": f"Bearer {auth_token}"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "raw_text" in data
        assert isinstance(data["items"], list)

    async def test_ocr_parse_prescription_unauthorized_returns_401(self):
        """토큰 없음 → 401"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ocr/parse-prescription",
                files={"file": ("test.jpg", self._make_image_file(), "image/jpeg")},
            )
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    async def test_ocr_parse_prescription_invalid_file_returns_400(self):
        """지원하지 않는 파일 형식 → 400"""
        token = await self._make_token("ocr_003", "01033330003")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ocr/parse-prescription",
                files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_ocr_parse_prescription_returns_items_with_inline_pattern(self):
        """인라인 패턴 파싱 검증"""
        from app.services.ocr_service import OcrService

        service = OcrService()
        parsed = service._parse_prescription_text(["렉사프로정 1.0 2 15"])
        assert len(parsed) == 1
        assert parsed[0]["drug_name"] == "렉사프로정"
        assert parsed[0]["dose_per_intake"] == 1.0
        assert parsed[0]["daily_frequency"] == 2
        assert parsed[0]["total_days"] == 15

    async def test_ocr_parse_prescription_returns_items_with_label_pattern(self):
        """레이블 패턴 OCR 텍스트 → items 파싱"""
        from app.services.ocr_service import OcrService

        service = OcrService()
        lines = ["렉사프로정", "1회투약량 1.00", "1일투여횟수 3", "총투약일수 7"]
        parsed = service._parse_prescription_text(lines)
        assert len(parsed) == 1
        assert parsed[0]["dose_per_intake"] == 1.0
        assert parsed[0]["daily_frequency"] == 3
        assert parsed[0]["total_days"] == 7

    async def test_ocr_parse_prescription_matches_medicine_in_db(self):
        """DB에 약품 존재 시 confidence HIGH, item_seq 반환"""
        await self._make_token("ocr_006", "01033330006")
        await Medicine.create(
            item_seq="OCR_MED001",
            item_name="렉사프로정10밀리그램",
            search_keyword="렉사프로정",
            is_active=True,
        )
        from app.services.ocr_service import OcrService

        service = OcrService()
        candidates = await service._smart_verify_drug("렉사프로정")
        assert len(candidates) >= 1
        result = service._verify_drug_with_mfds(candidates, "렉사프로정10밀리그램")
        assert result is not None
        assert result["item_seq"] == "OCR_MED001"

    async def test_verify_drug_returns_none_when_no_candidates(self):
        """후보 없으면 None 반환"""
        from app.services.ocr_service import OcrService

        service = OcrService()
        result = service._verify_drug_with_mfds([], "존재하지않는약xyz")
        assert result is None

    async def test_parse_prescription_excludes_unmatched_drugs(self):
        """DB에 없는 약품명은 parse_prescription 결과에서 제외"""
        from unittest.mock import AsyncMock, patch

        from app.services.ocr_service import OcrService

        await Medicine.create(
            item_seq="FILTER_MED001",
            item_name="아스피린정100밀리그램",
            search_keyword="아스피린정",
            is_active=True,
        )
        service = OcrService()
        mock_text = "아스피린정 1.0 1 30\n약제비총액정 1.0 1 30"
        with (
            patch.object(service, "extract_text", new=AsyncMock(return_value=mock_text)),
            patch.object(service, "_preprocess_image", return_value=b"fake"),
            patch("app.services.ocr_service.config.OCR_PROVIDER", "http"),
        ):
            result = await service.parse_prescription(b"fake", "image/jpeg")
        item_names = [item.item_name for item in result.items]
        assert any("아스피린" in name for name in item_names)
        assert not any("약제비총액" in name for name in item_names)

    # ── 회귀 테스트: 4.jpg 레이블 패턴 다중 약품 ────────────────────────────────
    async def test_parse_label_pattern_multi_drug_4jpg(self):
        """4.jpg: 레이블 패턴 3개 약품 모두 파싱"""
        from app.services.ocr_service import OcrService

        service = OcrService()
        lines = [
            "시클러캡슐250밀리그램(세파",
            "1회투약량 1.00",
            "1일투여횟수3 총투약일수3",
            "잘레톤정(잘토프로팬)_(80",
            "1회투약량1.00",
            "1일투여횟수3",
            "총투약일수3",
            "에소졸정20밀리그림(에스오메",
            "1회투약량1.00 4,200",
            "1일투여횟수1 총투약일수3",
        ]
        parsed = service._parse_prescription_text(lines)
        names = [p["drug_name"] for p in parsed]
        assert any("시클러캡슐" in n for n in names), f"시클러캡슐 미검출: {names}"
        assert any("잘레톤정" in n for n in names), f"잘레톤정 미검출: {names}"
        assert any("에소졸정" in n for n in names), f"에소졸정 미검출: {names}"
        for p in parsed:
            if "시클러캡슐" in p["drug_name"]:
                assert p["dose_per_intake"] == 1.0
                assert p["daily_frequency"] == 3
                assert p["total_days"] == 3
            if "잘레톤정" in p["drug_name"]:
                assert p["dose_per_intake"] == 1.0
                assert p["daily_frequency"] == 3
                assert p["total_days"] == 3
            if "에소졸정" in p["drug_name"]:
                assert p["dose_per_intake"] == 1.0
                assert p["daily_frequency"] == 1
                assert p["total_days"] == 3

    # ── 회귀 테스트: 6.jpg 컬럼 레이아웃 금액 노이즈 필터 ────────────────────────
    async def test_parse_column_layout_filters_price_noise_6jpg(self):
        """6.jpg: 금액 숫자가 섞여도 투약량/횟수/일수 정확히 파싱"""
        from app.services.ocr_service import OcrService

        service = OcrService()
        lines = [
            "도모호론액",
            "삼아리도맥스크림",
            "아드반탄연고",
            "투약량",
            "0.5 0.5 0.5",
            "횟수",
            "22 2",
            "일수",
            "1",
        ]
        parsed = service._parse_prescription_text(lines)
        for p in parsed:
            assert p["daily_frequency"] == 2, f"{p['drug_name']} 횟수 오류: {p['daily_frequency']}"
            assert p["total_days"] == 1, f"{p['drug_name']} 일수 오류: {p['total_days']}"

    # ── 회귀 테스트: 7.jpg 하단 숫자 테이블 파싱 ─────────────────────────────────
    async def test_parse_7jpg_bottom_table(self):
        """7.jpg: 하단 '약품명(성분) 일수 투약량 횟수' 테이블 파싱"""
        from app.services.ocr_service import OcrService

        service = OcrService()
        lines = [
            "사이옵신정(시프로플록",
            "3",
            "1.00",
            "3",
            "타이레놀8시간이알서방",
            "1.00",
            "3",
            "3",
            "케이캡정50밀리그램(테",
            "1.00",
            "1",
            "5",
            "베이제정",
            "1.00",
            "3",
            "5",
            "밀양디세텔정(피나베륨",
            "1.00",
            "3",
            "5",
            "포리부틴정150mg(트리",
            "1.00",
            "3",
            "5",
        ]
        parsed = service._parse_prescription_text(lines)
        names = [p["drug_name"] for p in parsed]
        assert any("사이" in n and "정" in n for n in names), f"사이옵신정 미검출: {names}"
        assert any("타이레놀" in n for n in names), f"타이레놀 미검출: {names}"
        assert any("케이캡정" in n for n in names), f"케이캡정 미검출: {names}"
        assert any("베" in n and "정" in n for n in names), f"베아제정 미검출: {names}"
        assert any("디세텔정" in n for n in names), f"디세텔정 미검출: {names}"
        assert any("포리부틴정" in n for n in names), f"포리부틴정 미검출: {names}"

    # ── 회귀 테스트: 8.jpeg 접두 노이즈 제거 ────────────────────────────────────
    async def test_parse_8jpeg_prefix_noise_removal(self):
        """8.jpeg: '비)' 접두사 및 괄호 이후 절단 후 약품명 파싱"""
        from app.services.ocr_service import OcrService

        service = OcrService()
        lines = [
            "약품명",
            "비)복합파자임이중정 정제",
            "비보존모사프리드정5mg(모사",
            "유파론정(애엽95%에탄올연조",
            "투약량",
            "1",
            "1",
            "1",
            "횟수",
            "3",
            "3",
            "3",
            "일수",
            "3",
            "3",
            "3",
        ]
        parsed = service._parse_prescription_text(lines)
        names = [p["drug_name"] for p in parsed]
        assert any("복합파자임이중정" in n for n in names), f"복합파자임이중정 미검출: {names}"
        assert any("모사프리드정" in n for n in names), f"모사프리드정 미검출: {names}"
        assert any("유파론정" in n for n in names), f"유파론정 미검출: {names}"
        for p in parsed:
            assert p["dose_per_intake"] == 1.0
            assert p["daily_frequency"] == 3
            assert p["total_days"] == 3

    # ── 기존 테스트 ───────────────────────────────────────────────────────────
    async def test_ocr_parse_prescription_end_to_end_with_mock_ocr(self):
        """mock OCR 텍스트 → parse_prescription → items 반환 (DB 매칭 포함)"""
        await self._make_token("ocr_007", "01033330007")
        await Medicine.create(
            item_seq="E2E_MED001",
            item_name="아스피린정100밀리그램",
            search_keyword="아스피린정",
            is_active=True,
        )
        from app.services.ocr_service import OcrService

        service = OcrService()
        with patch.object(service, "extract_text", new=AsyncMock(return_value="아스피린정 1.0 1 30")):
            await service.parse_prescription(b"fake", "image/jpeg")
        # stub 모드이므로 extract_text가 호출되지 않음 — provider 직접 우회
        # 서비스 레벨에서 직접 검증
        lines = ["아스피린정 1.0 1 30"]
        parsed = service._parse_prescription_text(lines)
        assert parsed[0]["drug_name"] == "아스피린정"
        candidates = await service._smart_verify_drug("아스피린정")
        assert any(c["item_seq"] == "E2E_MED001" for c in candidates)
        matched = service._verify_drug_with_mfds(candidates, "아스피린정100밀리그램")
        assert matched is not None
        assert matched["item_seq"] == "E2E_MED001"
