from src.core.database import SessionLocal
from src.models.schema import Debate, ReconciliationUnit
from src.orchestration.debate_manager import DebateManager

import logging
logging.basicConfig(level=logging.INFO)

def debug():
    db = SessionLocal()
    try:
        from src.models.schema import DebateStatus
        
        # Create fresh debate
        d = Debate(conflict_id=2924, status=DebateStatus.in_progress)
        db.add(d)
        db.commit()
        
        u = db.query(ReconciliationUnit).get(2924)
        print(f"Debugging fresh debate {d.id} for unit {u.id}")
        m = DebateManager()
        m._run_4_round_loop(db, d, u)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug()
