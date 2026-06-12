from src.core.database import SessionLocal
from src.models.schema import ReconciliationUnit, Debate, DebateStatus, DebateMessage
from src.orchestration.debate_manager import DebateManager

db = SessionLocal()
unit = db.query(ReconciliationUnit).first()
if not unit:
    print("ERROR: No ReconciliationUnit found. Run a scan first.")
else:
    print(f"Unit id={unit.id}, file={unit.file_path}")
    debate = Debate(conflict_id=unit.id, status=DebateStatus.in_progress)
    db.add(debate)
    db.commit()
    db.refresh(debate)
    print(f"Debate id={debate.id}")

    mgr = DebateManager()
    mgr._run_4_round_loop(db, debate, unit)

    db.refresh(debate)
    print(f"Status: {debate.status}")
    print(f"Proposal: {str(debate.architectural_proposal)[:150]}")
    print(f"Confidence: {debate.confidence}")

    msgs = db.query(DebateMessage).filter(DebateMessage.debate_id == debate.id).all()
    print(f"Messages: {len(msgs)}")
    for m in msgs:
        ev = m.evidence_refs
        ev_count = len(ev) if isinstance(ev, list) else "not a list"
        print(f"  Round {m.round} agent={m.agent} evidence_count={ev_count}")

db.close()
