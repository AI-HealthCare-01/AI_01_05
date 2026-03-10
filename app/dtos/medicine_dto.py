from pydantic import BaseModel

from app.dtos.base import BaseSerializerModel


class MedicineSearchResponse(BaseModel):
    item_seq: str
    item_name: str
    entp_name: str | None = None


class MedicineDetailResponse(BaseSerializerModel):
    item_seq: str
    item_name: str
    entp_name: str | None = None
    efcy_qesitm: str | None = None
    use_method_qesitm: str | None = None
    item_image: str | None = None
