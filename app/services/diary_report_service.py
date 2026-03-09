import zoneinfo
from calendar import monthrange
from datetime import date, datetime

from app.core import memory_db
from app.models.diary import Diary
from app.models.mood import Mood
from app.models.report import Report
from app.services.llm_service import LlmService
from app.services.ocr_service import OcrService

KST = zoneinfo.ZoneInfo("Asia/Seoul")
TIME_SLOT_ORDER = {"MORNING": 0, "LUNCH": 1, "EVENING": 2, "BEDTIME": 3}


class DiaryReportService:
    def __init__(self) -> None:
        self.ocr_service = OcrService()
        self.llm_service = LlmService()

    def next_entry_id(self) -> int:
        entry_id = memory_db.diary_entry_sequence
        memory_db.diary_entry_sequence += 1
        return entry_id

    async def get_calendar(self, user_id: int, year: int, month: int) -> dict:
        if month < 1 or month > 12:
            raise ValueError("INVALID_PARAM")

        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        diary_dates = set(
            await Diary.filter(
                user_id=user_id,
                deleted_at__isnull=True,
                diary_date__gte=start_date,
                diary_date__lte=end_date,
            ).values_list("diary_date", flat=True)
        )
        mood_rows = await Mood.filter(
            user_id=user_id,
            log_date__gte=start_date,
            log_date__lte=end_date,
        ).order_by("log_date", "time_slot")
        moods_by_date: dict[date, list[dict]] = {}
        for mood in mood_rows:
            moods_by_date.setdefault(mood.log_date, []).append(
                {"mood_level": mood.mood_level, "time_slot": mood.time_slot}
            )

        days = []
        for day in range(1, end_date.day + 1):
            current_date = date(year, month, day)
            has_diary = current_date in diary_dates
            moods = sorted(
                moods_by_date.get(current_date, []),
                key=lambda item: TIME_SLOT_ORDER.get(item["time_slot"], 99),
            )
            days.append({"date": current_date, "hasDiary": has_diary, "moods": moods})
        return {"year": year, "month": month, "days": days}

    async def get_diary_by_date(self, user_id: int, entry_date: date) -> dict:
        diaries = await Diary.filter(user_id=user_id, diary_date=entry_date, deleted_at__isnull=True).order_by(
            "-created_at"
        )
        moods = await Mood.filter(user_id=user_id, log_date=entry_date).order_by("time_slot")
        mood_data = [
            {"mood_level": mood.mood_level, "time_slot": mood.time_slot}
            for mood in sorted(moods, key=lambda item: TIME_SLOT_ORDER.get(item.time_slot, 99))
        ]

        entries = [
            {
                "entryId": diary.diary_id,
                "source": diary.write_method or "direct",
                "title": diary.title or "",
                "content": diary.content,
                "createdAt": diary.created_at,
            }
            for diary in diaries
        ]
        return {"date": entry_date, "entries": entries, "moods": mood_data}

    async def create_text_diary(self, user_id: int, entry_date: date, title: str, content: str) -> dict:
        diary = await Diary.create(
            user_id=user_id,
            diary_date=entry_date,
            title=title,
            content=content,
            write_method="direct",
        )
        return {"entryId": diary.diary_id, "message": "일기가 저장되었습니다."}

    async def extract_ocr_text(self, entry_date: date, file_type: str, file_bytes: bytes) -> dict:
        if file_type not in {"image/jpeg", "image/png"}:
            raise ValueError("UNSUPPORTED_FORMAT")
        if len(file_bytes) > 10 * 1024 * 1024:
            raise ValueError("FILE_TOO_LARGE")

        pending_id = self.next_entry_id()
        extracted_text = await self.ocr_service.extract_text(file_bytes=file_bytes, file_type=file_type)
        memory_db.fake_ocr_pending[pending_id] = {"date": entry_date, "extractedText": extracted_text}
        return {"entryId": pending_id, "extractedText": extracted_text}

    async def confirm_ocr_text(self, user_id: int, entry_date: date, entry_id: int, title: str, content: str) -> dict:
        pending = memory_db.fake_ocr_pending.get(entry_id)
        if not pending or pending["date"] != entry_date:
            raise LookupError("ENTRY_NOT_FOUND")

        diary = await Diary.create(
            user_id=user_id,
            diary_date=entry_date,
            title=title,
            content=content,
            write_method="ocr",
        )
        del memory_db.fake_ocr_pending[entry_id]
        return {"entryId": diary.diary_id, "message": "일기가 저장되었습니다."}

    async def get_chatbot_summary(self, user_id: int, entry_date: date) -> dict:
        diaries = await Diary.filter(user_id=user_id, diary_date=entry_date, deleted_at__isnull=True).order_by(
            "-created_at"
        )
        if not diaries:
            return {"hasChatHistory": False, "entryId": None, "summary": None, "redirectToChatbot": True}

        texts = [diary.content for diary in diaries[:5]]
        try:
            summary = await self.llm_service.summarize_chat(chat_texts=texts, entry_date=entry_date.isoformat())
        except Exception:
            summary = " ".join(diary.content for diary in diaries[:3]).strip()

        pending_id = self.next_entry_id()
        memory_db.fake_chatbot_pending[pending_id] = {"date": entry_date, "summary": summary}
        return {"hasChatHistory": True, "entryId": pending_id, "summary": summary, "redirectToChatbot": False}

    async def save_chatbot_summary(
        self, user_id: int, entry_date: date, entry_id: int, title: str, content: str
    ) -> dict:
        pending = memory_db.fake_chatbot_pending.get(entry_id)
        if not pending or pending["date"] != entry_date:
            raise LookupError("ENTRY_NOT_FOUND")

        try:
            generated_title = await self.llm_service.generate_title(content=content)
        except Exception:
            generated_title = ""

        diary = await Diary.create(
            user_id=user_id,
            diary_date=entry_date,
            title=generated_title or title,
            content=content,
            write_method="chatbot",
        )
        del memory_db.fake_chatbot_pending[entry_id]
        return {"entryId": diary.diary_id, "message": "일기가 저장되었습니다."}

    async def update_diary_entry(
        self,
        user_id: int,
        entry_date: date,
        entry_id: int,
        title: str | None,
        content: str | None,
    ) -> dict:
        diary = await Diary.get_or_none(
            user_id=user_id, diary_id=entry_id, diary_date=entry_date, deleted_at__isnull=True
        )
        if not diary:
            raise LookupError("ENTRY_NOT_FOUND")

        update_data = {}
        if title is not None:
            update_data["title"] = title
        if content is not None:
            update_data["content"] = content
        if update_data:
            update_data["updated_at"] = datetime.now(tz=KST)
            await Diary.filter(diary_id=entry_id).update(**update_data)
        return {"entryId": entry_id, "message": "일기가 수정되었습니다."}

    async def delete_diary_entry(self, user_id: int, entry_date: date, entry_id: int) -> dict:
        diary = await Diary.get_or_none(
            user_id=user_id, diary_id=entry_id, diary_date=entry_date, deleted_at__isnull=True
        )
        if not diary:
            raise LookupError("ENTRY_NOT_FOUND")

        await Diary.filter(diary_id=entry_id).update(deleted_at=datetime.now(tz=KST))
        return {"message": "일기가 삭제되었습니다."}

    async def get_reports(self, user_id: int) -> dict:
        reports = await Report.filter(user_id=user_id).order_by("-created_at")
        return {
            "reports": [
                {
                    "reportId": report.report_id,
                    "startDate": report.start_date,
                    "endDate": report.end_date,
                    "createdAt": report.created_at.date(),
                }
                for report in reports
            ]
        }

    async def create_report(self, user_id: int, start_date: date, end_date: date) -> dict:
        if start_date > end_date:
            raise ValueError("INVALID_DATE_RANGE")

        diaries = await Diary.filter(
            user_id=user_id,
            deleted_at__isnull=True,
            diary_date__gte=start_date,
            diary_date__lte=end_date,
        ).order_by("diary_date", "created_at")
        diary_texts = [diary.content for diary in diaries]

        try:
            summary = await self.llm_service.summarize_report(
                diary_texts=diary_texts,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        except Exception:
            summary = f"======= 리포트 요약 데이터 =======\n{start_date}부터 {end_date}까지의 요약입니다."

        report = await Report.create(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            summary=summary,
        )
        return {
            "reportId": report.report_id,
            "startDate": report.start_date,
            "endDate": report.end_date,
            "createdAt": report.created_at.date(),
            "summary": report.summary,
        }

    async def get_report_detail(self, user_id: int, report_id: int) -> dict:
        report = await Report.get_or_none(user_id=user_id, report_id=report_id)
        if not report:
            raise LookupError("REPORT_NOT_FOUND")
        return {
            "reportId": report.report_id,
            "startDate": report.start_date,
            "endDate": report.end_date,
            "createdAt": report.created_at.date(),
            "summary": report.summary or "",
        }

    async def update_report(self, user_id: int, report_id: int, summary: str) -> dict:
        report = await Report.get_or_none(user_id=user_id, report_id=report_id)
        if not report:
            raise LookupError("REPORT_NOT_FOUND")

        await Report.filter(report_id=report_id).update(summary=summary, updated_at=datetime.now(tz=KST))
        return {"reportId": report_id, "message": "리포트가 수정되었습니다."}