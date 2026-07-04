"""设置:OCR / 问问AI 模型切换(「我的」页用)。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_token
from settings_store import current_models, set_setting, MODEL_CANDIDATES

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_token)])


class SettingsOut(BaseModel):
    ocr_model: str
    insight_model: str
    candidates: dict[str, list[str]]


class SettingsPatch(BaseModel):
    ocr_model: str | None = None
    insight_model: str | None = None


@router.get("", response_model=SettingsOut)
async def get_settings():
    m = current_models()
    return SettingsOut(**m, candidates=MODEL_CANDIDATES)


@router.put("", response_model=SettingsOut)
async def put_settings(patch: SettingsPatch):
    if patch.ocr_model is not None:
        set_setting("ocr_model", patch.ocr_model.strip())
    if patch.insight_model is not None:
        set_setting("insight_model", patch.insight_model.strip())
    return SettingsOut(**current_models(), candidates=MODEL_CANDIDATES)
