from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from database import get_db
from models import User, Investigation, Evidence
from api.deps import get_current_user
from api.rate_limit import rate_limit
from plugins.runner import run_investigation

router = APIRouter(prefix="/investigations", tags=["investigations"])


class StartInvestigationRequest(BaseModel):
    target: str
    telegram_chat_id: int | None = None
    telegram_message_id: int | None = None


@router.post("", dependencies=[Depends(rate_limit(limit=30, window=60))])
async def start_investigation(
    req: StartInvestigationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from plugins.runner import classify_target
    target_type = classify_target(req.target.strip())

    inv = Investigation(
        user_id=current_user.id,
        target=req.target.strip(),
        target_type=target_type,
        status="running",
        telegram_chat_id=req.telegram_chat_id,
        telegram_message_id=req.telegram_message_id,
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)

    background_tasks.add_task(run_investigation, inv.id)
    return {"id": inv.id, "target": inv.target, "target_type": target_type, "status": "running"}


@router.get("")
async def list_investigations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
):
    result = await db.execute(
        select(Investigation)
        .where(Investigation.user_id == current_user.id)
        .order_by(desc(Investigation.created_at))
        .limit(limit)
    )
    investigations = result.scalars().all()
    return [
        {
            "id": inv.id,
            "target": inv.target,
            "target_type": inv.target_type,
            "status": inv.status,
            "created_at": inv.created_at.isoformat(),
            "completed_at": inv.completed_at.isoformat() if inv.completed_at else None,
        }
        for inv in investigations
    ]


@router.get("/{inv_id}")
async def get_investigation(
    inv_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Investigation)
        .where(Investigation.id == inv_id, Investigation.user_id == current_user.id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    evidence_result = await db.execute(
        select(Evidence).where(Evidence.investigation_id == inv_id)
    )
    evidence = evidence_result.scalars().all()

    return {
        "id": inv.id,
        "target": inv.target,
        "target_type": inv.target_type,
        "status": inv.status,
        "summary": inv.summary,
        "created_at": inv.created_at.isoformat(),
        "completed_at": inv.completed_at.isoformat() if inv.completed_at else None,
        "evidence": [
            {"plugin": e.plugin_name, "data": e.data, "collected_at": e.collected_at.isoformat()}
            for e in evidence
        ],
    }


class AnalyzeRequest(BaseModel):
    target: str
    evidence: dict


@router.post("/{inv_id}/analyze")
async def analyze_investigation(
    inv_id: int,
    req: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Investigation)
        .where(Investigation.id == inv_id, Investigation.user_id == current_user.id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    from plugins.ai_analysis import AiAnalysisPlugin
    plugin = AiAnalysisPlugin()
    if not plugin._configured:
        raise HTTPException(status_code=503, detail="AI analysis not configured — set GEMINI_API_KEY")

    ai_result = await plugin.run(req.target, evidence_data=req.evidence)
    if not ai_result.success:
        raise HTTPException(status_code=500, detail=ai_result.error)

    # Store as evidence
    from sqlalchemy import delete
    await db.execute(
        delete(Evidence).where(
            Evidence.investigation_id == inv_id,
            Evidence.plugin_name == "ai_analysis"
        )
    )
    ai_evidence = Evidence(
        investigation_id=inv_id,
        plugin_name="ai_analysis",
        data=ai_result.data,
    )
    db.add(ai_evidence)
    await db.commit()

    return {"report": ai_result.data.get("report"), "model": ai_result.data.get("model")}