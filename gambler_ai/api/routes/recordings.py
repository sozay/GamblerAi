"""
API routes for session recording and replay functionality.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from gambler_ai.storage.database import get_db_session
from gambler_ai.storage.models import RecordedSession, RecordedEvent, RecordedMarketData, ReplaySession
from gambler_ai.trading.session_replayer import (
    SessionReplayer,
    list_recordings,
    get_recording_details,
)


router = APIRouter(prefix="/api/v1/recordings", tags=["recordings"])


class StartRecordingRequest(BaseModel):
    """Request to start recording."""
    instance_id: int
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class StopRecordingRequest(BaseModel):
    """Request to stop recording."""
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class ReplayRequest(BaseModel):
    """Request to replay a recording."""
    modified_parameters: Dict[str, Any]
    description: Optional[str] = None


@router.get("/")
async def get_recordings(
    instance_id: Optional[int] = Query(None, description="Filter by instance ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """
    Get list of all recordings.

    Args:
        instance_id: Optional filter by instance ID
        status: Optional filter by status (recording, completed, failed)

    Returns:
        List of recordings with metadata
    """
    db = next(get_db_session())
    try:
        recordings = list_recordings(db, instance_id=instance_id)

        # Filter by status if provided
        if status:
            recordings = [r for r in recordings if r['status'] == status]

        return {
            "success": True,
            "count": len(recordings),
            "recordings": recordings,
        }
    finally:
        db.close()


@router.get("/{recording_id}")
async def get_recording(recording_id: str):
    """
    Get detailed information about a specific recording.

    Args:
        recording_id: Recording ID

    Returns:
        Recording details including events and replays
    """
    db = next(get_db_session())
    try:
        details = get_recording_details(db, recording_id)

        if not details:
            raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")

        return {
            "success": True,
            "recording": details,
        }
    finally:
        db.close()


@router.get("/{recording_id}/events")
async def get_recording_events(
    recording_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    Get events from a recording.

    Args:
        recording_id: Recording ID
        event_type: Optional filter by event type
        limit: Maximum number of events (default 100)
        offset: Offset for pagination (default 0)

    Returns:
        List of events
    """
    db = next(get_db_session())
    try:
        # Check recording exists
        recording = db.query(RecordedSession).filter(
            RecordedSession.recording_id == recording_id
        ).first()

        if not recording:
            raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")

        # Query events
        query = db.query(RecordedEvent).filter(
            RecordedEvent.recording_id == recording_id
        )

        if event_type:
            query = query.filter(RecordedEvent.event_type == event_type)

        total = query.count()
        events = query.order_by(RecordedEvent.sequence).offset(offset).limit(limit).all()

        return {
            "success": True,
            "recording_id": recording_id,
            "total_events": total,
            "offset": offset,
            "limit": limit,
            "events": [
                {
                    "event_type": e.event_type,
                    "timestamp": e.timestamp.isoformat(),
                    "sequence": e.sequence,
                    "symbol": e.symbol,
                    "event_data": e.event_data,
                    "decision_metadata": e.decision_metadata,
                    "market_state": e.market_state,
                }
                for e in events
            ],
        }
    finally:
        db.close()


@router.get("/{recording_id}/market-data")
async def get_recording_market_data(
    recording_id: str,
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(100, ge=1, le=10000, description="Maximum number of bars to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    Get market data from a recording.

    Args:
        recording_id: Recording ID
        symbol: Optional filter by symbol
        limit: Maximum number of bars (default 100)
        offset: Offset for pagination (default 0)

    Returns:
        List of market data bars
    """
    db = next(get_db_session())
    try:
        # Check recording exists
        recording = db.query(RecordedSession).filter(
            RecordedSession.recording_id == recording_id
        ).first()

        if not recording:
            raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")

        # Query market data
        query = db.query(RecordedMarketData).filter(
            RecordedMarketData.recording_id == recording_id
        )

        if symbol:
            query = query.filter(RecordedMarketData.symbol == symbol)

        total = query.count()
        bars = query.order_by(RecordedMarketData.sequence).offset(offset).limit(limit).all()

        return {
            "success": True,
            "recording_id": recording_id,
            "symbol": symbol,
            "total_bars": total,
            "offset": offset,
            "limit": limit,
            "bars": [
                {
                    "symbol": b.symbol,
                    "timestamp": b.timestamp.isoformat(),
                    "sequence": b.sequence,
                    "open": float(b.open),
                    "high": float(b.high),
                    "low": float(b.low),
                    "close": float(b.close),
                    "volume": b.volume,
                    "indicators": b.indicators,
                }
                for b in bars
            ],
        }
    finally:
        db.close()


@router.post("/{recording_id}/replay")
async def replay_recording(
    recording_id: str,
    request: ReplayRequest = Body(...),
):
    """
    Replay a recording with modified parameters.

    Args:
        recording_id: Recording ID
        request: Replay parameters

    Returns:
        Replay results and comparison with original
    """
    db = next(get_db_session())
    try:
        # Check recording exists and is completed
        recording = db.query(RecordedSession).filter(
            RecordedSession.recording_id == recording_id
        ).first()

        if not recording:
            raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")

        if recording.status != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Cannot replay recording with status '{recording.status}'. Only completed recordings can be replayed."
            )

        # Create replayer
        replayer = SessionReplayer(db, recording_id)

        # Set modified parameters
        replayer.set_parameters(request.modified_parameters)

        # TODO: Load appropriate strategy detector based on recording.strategy_name
        # For now, we'll return a placeholder response
        # In full implementation, you'd instantiate the actual detector and call replayer.replay(detector)

        return {
            "success": True,
            "message": "Replay initiated",
            "recording_id": recording_id,
            "modified_parameters": request.modified_parameters,
            "note": "Full replay implementation requires strategy detector integration. See session_replayer.py for the replay() method.",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Replay failed: {str(e)}")
    finally:
        db.close()


@router.get("/{recording_id}/replays")
async def get_replays(recording_id: str):
    """
    Get all replays for a recording.

    Args:
        recording_id: Recording ID

    Returns:
        List of replays
    """
    db = next(get_db_session())
    try:
        # Check recording exists
        recording = db.query(RecordedSession).filter(
            RecordedSession.recording_id == recording_id
        ).first()

        if not recording:
            raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")

        # Get replays
        replays = db.query(ReplaySession).filter(
            ReplaySession.recording_id == recording_id
        ).order_by(ReplaySession.replay_time.desc()).all()

        return {
            "success": True,
            "recording_id": recording_id,
            "count": len(replays),
            "replays": [
                {
                    "replay_id": r.replay_id,
                    "replay_time": r.replay_time.isoformat(),
                    "status": r.status,
                    "modified_parameters": r.modified_parameters,
                    "total_trades": r.total_trades,
                    "winning_trades": r.winning_trades,
                    "losing_trades": r.losing_trades,
                    "win_rate": float(r.win_rate) if r.win_rate else 0,
                    "total_pnl": float(r.total_pnl) if r.total_pnl else 0,
                    "max_drawdown": float(r.max_drawdown) if r.max_drawdown else 0,
                    "sharpe_ratio": float(r.sharpe_ratio) if r.sharpe_ratio else 0,
                    "trades_diff": r.trades_diff,
                    "pnl_diff": float(r.pnl_diff) if r.pnl_diff else 0,
                    "win_rate_diff": float(r.win_rate_diff) if r.win_rate_diff else 0,
                    "description": r.description,
                }
                for r in replays
            ],
        }
    finally:
        db.close()


@router.get("/replays/{replay_id}")
async def get_replay_details(replay_id: str):
    """
    Get detailed results from a replay.

    Args:
        replay_id: Replay ID

    Returns:
        Detailed replay results
    """
    db = next(get_db_session())
    try:
        replay = db.query(ReplaySession).filter(
            ReplaySession.replay_id == replay_id
        ).first()

        if not replay:
            raise HTTPException(status_code=404, detail=f"Replay {replay_id} not found")

        return {
            "success": True,
            "replay": {
                "replay_id": replay.replay_id,
                "recording_id": replay.recording_id,
                "replay_time": replay.replay_time.isoformat(),
                "status": replay.status,
                "modified_parameters": replay.modified_parameters,
                "total_trades": replay.total_trades,
                "winning_trades": replay.winning_trades,
                "losing_trades": replay.losing_trades,
                "win_rate": float(replay.win_rate) if replay.win_rate else 0,
                "total_pnl": float(replay.total_pnl) if replay.total_pnl else 0,
                "max_drawdown": float(replay.max_drawdown) if replay.max_drawdown else 0,
                "sharpe_ratio": float(replay.sharpe_ratio) if replay.sharpe_ratio else 0,
                "trades_diff": replay.trades_diff,
                "pnl_diff": float(replay.pnl_diff) if replay.pnl_diff else 0,
                "win_rate_diff": float(replay.win_rate_diff) if replay.win_rate_diff else 0,
                "comparison_data": replay.comparison_data,
                "replay_events": replay.replay_events,
                "description": replay.description,
            },
        }
    finally:
        db.close()


@router.delete("/{recording_id}")
async def delete_recording(recording_id: str):
    """
    Delete a recording and all associated data.

    Args:
        recording_id: Recording ID

    Returns:
        Success message
    """
    db = next(get_db_session())
    try:
        recording = db.query(RecordedSession).filter(
            RecordedSession.recording_id == recording_id
        ).first()

        if not recording:
            raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")

        # Delete recording (cascade will delete related data)
        db.delete(recording)
        db.commit()

        return {
            "success": True,
            "message": f"Recording {recording_id} deleted successfully",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete recording: {str(e)}")
    finally:
        db.close()


@router.get("/instances/{instance_id}/active-recording")
async def get_active_recording(instance_id: int):
    """
    Get the currently active recording for an instance.

    Args:
        instance_id: Instance ID

    Returns:
        Active recording info or null if no active recording
    """
    db = next(get_db_session())
    try:
        recording = db.query(RecordedSession).filter(
            RecordedSession.instance_id == instance_id,
            RecordedSession.status == 'recording'
        ).order_by(RecordedSession.recording_start_time.desc()).first()

        if not recording:
            return {
                "success": True,
                "instance_id": instance_id,
                "active_recording": None,
            }

        return {
            "success": True,
            "instance_id": instance_id,
            "active_recording": {
                "recording_id": recording.recording_id,
                "session_id": recording.session_id,
                "strategy_name": recording.strategy_name,
                "recording_start_time": recording.recording_start_time.isoformat(),
                "total_bars_recorded": recording.total_bars_recorded,
                "total_events_recorded": recording.total_events_recorded,
            },
        }
    finally:
        db.close()
