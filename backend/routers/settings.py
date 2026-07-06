"""设置:OCR / 问问AI 模型切换(「我的」页用)。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_token
from settings_store import current_models, set_setting, MODEL_CANDIDATES
from classification_schema import (
    DOMAIN_ORDER, ENTRY_TYPE_ORDER, SOURCE_ORDER, SUB_TOPICS_BY_TOPIC, TOPICS_BY_DOMAIN,
)

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_token)])


class SettingsOut(BaseModel):
    ocr_model: str
    insight_model: str
    classify_model: str
    candidates: dict[str, list[str]]


class SettingsPatch(BaseModel):
    ocr_model: str | None = None
    insight_model: str | None = None
    classify_model: str | None = None


class ClassificationSchemaOut(BaseModel):
    entry_types: list[str]
    domains: list[str]
    sources: list[str]
    topics_by_domain: dict[str, list[str]]
    sub_topics_by_topic: dict[str, list[str]]


@router.get("", response_model=SettingsOut)
async def get_settings():
    m = current_models()
    return SettingsOut(**m, candidates=MODEL_CANDIDATES)


@router.get("/classification-schema", response_model=ClassificationSchemaOut)
async def classification_schema():
    return ClassificationSchemaOut(
        entry_types=ENTRY_TYPE_ORDER,
        domains=DOMAIN_ORDER,
        sources=SOURCE_ORDER,
        topics_by_domain=TOPICS_BY_DOMAIN,
        sub_topics_by_topic=SUB_TOPICS_BY_TOPIC,
    )


@router.put("", response_model=SettingsOut)
async def put_settings(patch: SettingsPatch):
    if patch.ocr_model is not None:
        set_setting("ocr_model", patch.ocr_model.strip())
    if patch.insight_model is not None:
        set_setting("insight_model", patch.insight_model.strip())
    if patch.classify_model is not None:
        set_setting("classify_model", patch.classify_model.strip())
    return SettingsOut(**current_models(), candidates=MODEL_CANDIDATES)
