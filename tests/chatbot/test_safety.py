"""check_safety() + check_response_safety() 단위 테스트.

Design spec: crisis-filter.design.md §7.2
Target: 정탐률 > 95%, 오탐률 < 5%, 테스트 케이스 >= 15개
"""

from ai_worker.tasks.chatbot_engine import check_response_safety, check_safety

# ──────────────────────────────────────────────
# check_safety() — Direct 카테고리
# ──────────────────────────────────────────────


class TestCheckSafetyDirect:
    def test_suicide(self):
        result = check_safety("죽고 싶어요")
        assert result is not None
        assert result["alert_type"] == "Direct"

    def test_self_harm(self):
        result = check_safety("자해하고 싶어")
        assert result is not None
        assert result["alert_type"] == "Direct"

    def test_extended_end_life(self):
        result = check_safety("생을 마감하고 싶다")
        assert result is not None
        assert result["alert_type"] == "Direct"

    def test_extended_leave_world(self):
        result = check_safety("세상을 떠나고 싶어")
        assert result is not None
        assert result["alert_type"] == "Direct"

    def test_space_variant(self):
        """공백을 삽입해도 감지되어야 함."""
        result = check_safety("죽 고 싶 어")
        assert result is not None
        assert result["alert_type"] == "Direct"


# ──────────────────────────────────────────────
# check_safety() — Indirect 카테고리
# ──────────────────────────────────────────────


class TestCheckSafetyIndirect:
    def test_disappear(self):
        result = check_safety("사라지고 싶어")
        assert result is not None
        assert result["alert_type"] == "Indirect"

    def test_eternal_sleep(self):
        result = check_safety("영원히 잠들고 싶어")
        assert result is not None
        assert result["alert_type"] == "Indirect"

    def test_burden(self):
        result = check_safety("짐이 되고 싶지 않아")
        assert result is not None
        assert result["alert_type"] == "Indirect"

    def test_no_meaning(self):
        result = check_safety("아무 의미 없는 삶이야")
        assert result is not None
        assert result["alert_type"] == "Indirect"


# ──────────────────────────────────────────────
# check_safety() — Substance 카테고리
# ──────────────────────────────────────────────


class TestCheckSafetySubstance:
    def test_overdose(self):
        result = check_safety("약물 과다 복용하고 싶어")
        assert result is not None
        assert result["alert_type"] == "Substance"

    def test_hoard_pills(self):
        result = check_safety("약을 모아두고 있어")
        assert result is not None
        assert result["alert_type"] == "Substance"

    def test_all_at_once(self):
        result = check_safety("한 번에 다 먹으려고")
        assert result is not None
        assert result["alert_type"] == "Substance"


# ──────────────────────────────────────────────
# check_safety() — Context 카테고리 (신규)
# ──────────────────────────────────────────────


class TestCheckSafetyContext:
    def test_farewell(self):
        result = check_safety("마지막 인사를 하려고")
        assert result is not None
        assert result["alert_type"] == "Context"

    def test_insurance(self):
        result = check_safety("보험금 받는 방법 알려줘")
        assert result is not None
        assert result["alert_type"] == "Context"

    def test_next_life(self):
        result = check_safety("다음 생에는 행복했으면")
        assert result is not None
        assert result["alert_type"] == "Context"


# ──────────────────────────────────────────────
# check_safety() — 오탐 검증 (일반 질문 통과)
# ──────────────────────────────────────────────


class TestCheckSafetyFalsePositive:
    def test_normal_drug_interaction(self):
        assert check_safety("혈압약과 감기약 같이 먹어도 되나요?") is None

    def test_normal_side_effect(self):
        assert check_safety("이 약의 부작용이 뭔가요?") is None

    def test_normal_sleep_prescription(self):
        assert check_safety("수면제 처방받고 싶어요") is None

    def test_normal_dosage(self):
        assert check_safety("이 약 하루에 몇 번 먹어야 하나요?") is None

    def test_normal_timing(self):
        assert check_safety("약 먹는 시간이 궁금해요") is None


# ──────────────────────────────────────────────
# check_response_safety() — 출력 위험 감지
# ──────────────────────────────────────────────


class TestCheckResponseSafety:
    def test_contraindication(self):
        answer = "이 약물 조합은 절대 금기에 해당합니다."
        result = check_response_safety(answer)
        assert result is not None
        assert result["danger_type"] == "Contraindication"

    def test_severe_effect(self):
        answer = "이 경우 심각한 부작용이 발생할 수 있습니다."
        result = check_response_safety(answer)
        assert result is not None
        assert result["danger_type"] == "SevereEffect"

    def test_overdose_warning(self):
        answer = "과다 복용 시 생명이 위험할 수 있습니다."
        result = check_response_safety(answer)
        assert result is not None
        assert result["danger_type"] == "Overdose"

    def test_lethal_dose(self):
        answer = "이 약의 치사량은 체중 기준으로 결정됩니다."
        result = check_response_safety(answer)
        assert result is not None
        assert result["danger_type"] == "Overdose"

    def test_normal_safe_answer(self):
        answer = "이 약은 식후 30분에 복용하시면 됩니다."
        assert check_response_safety(answer) is None

    def test_normal_mild_side_effect(self):
        answer = "가벼운 두통이 나타날 수 있지만 보통 며칠 내에 사라집니다."
        assert check_response_safety(answer) is None

    def test_normal_interaction_safe(self):
        answer = "이 두 약물은 함께 복용해도 문제없습니다."
        assert check_response_safety(answer) is None
