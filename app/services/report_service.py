from app.dtos.report_dto import ReportCreateRequest
from app.models.report import Report


async def create_report_service(request: ReportCreateRequest) -> Report:
    fake_summary = (
        f"{request.start_date}부터 {request.end_date}까지의 리포트입니다. "
        f"현재는 임시 요약문입니다."
    )

    report = await Report.create(
        user_id=request.user_id,
        start_date=request.start_date,
        end_date=request.end_date,
        summary=fake_summary,
    )
    return report