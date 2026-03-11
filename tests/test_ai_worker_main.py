"""ai_worker.main 워커 프로세스 단위 테스트.

- MedicationChatbot 초기화 확인
- main() 시그널 처리 확인
"""

import asyncio
import inspect
import signal
from unittest.mock import MagicMock, patch

# ──────────────────────────────────────────────
# MedicationChatbot 초기화 테스트
# ──────────────────────────────────────────────


class TestWorkerInit:
    def test_imports_medication_chatbot(self):
        """ai_worker.main이 MedicationChatbot을 import한다."""
        from ai_worker import main

        assert hasattr(main, "MedicationChatbot")

    def test_main_function_exists(self):
        """main() 비동기 함수가 존재한다."""
        from ai_worker.main import main

        assert inspect.iscoroutinefunction(main)


# ──────────────────────────────────────────────
# main() 시그널 처리 테스트
# ──────────────────────────────────────────────


class TestWorkerMainLoop:
    @patch("ai_worker.main.MedicationChatbot")
    async def test_main_initializes_chatbot(self, mock_chatbot_cls):
        """main()이 MedicationChatbot을 생성한다."""
        mock_instance = MagicMock()
        mock_instance.model = "gpt-4o-mini"
        mock_chatbot_cls.return_value = mock_instance

        from ai_worker.main import main

        async def stop_soon():
            await asyncio.sleep(0.1)
            # SIGTERM으로 종료
            signal.raise_signal(signal.SIGTERM)

        task = asyncio.create_task(stop_soon())
        await main()
        await task

        mock_chatbot_cls.assert_called_once()

    @patch("ai_worker.main.MedicationChatbot")
    async def test_main_exits_on_sigterm(self, mock_chatbot_cls):
        """SIGTERM 수신 시 main()이 정상 종료된다."""
        mock_instance = MagicMock()
        mock_instance.model = "gpt-4o-mini"
        mock_chatbot_cls.return_value = mock_instance

        from ai_worker.main import main

        async def send_sigterm():
            await asyncio.sleep(0.1)
            signal.raise_signal(signal.SIGTERM)

        task = asyncio.create_task(send_sigterm())
        await main()  # SIGTERM으로 정상 종료되어야 함
        await task

    @patch("ai_worker.main.MedicationChatbot")
    async def test_main_logs_startup(self, mock_chatbot_cls, caplog):
        """시작 시 로그를 출력한다."""
        mock_instance = MagicMock()
        mock_instance.model = "gpt-4o-mini"
        mock_chatbot_cls.return_value = mock_instance

        from ai_worker.main import main

        async def send_sigterm():
            await asyncio.sleep(0.1)
            signal.raise_signal(signal.SIGTERM)

        with caplog.at_level("INFO", logger="ai_worker"):
            task = asyncio.create_task(send_sigterm())
            await main()
            await task

        assert any("로드 완료" in r.message for r in caplog.records)
