import sys
from src.core.database import SessionLocal
from src.models.schema import Debate, ReconciliationUnit, DebateStatus

def test():
    db = SessionLocal()
    try:
        unit = db.query(ReconciliationUnit).filter(ReconciliationUnit.id == 1931).first()
        if not unit:
            print("Unit 1931 not found, trying unit 1")
            unit = db.query(ReconciliationUnit).first()
            if not unit:
                print("No units found")
                return
        
        debate = Debate(
            conflict_id=unit.id,
            status=DebateStatus.in_progress
        )
        db.add(debate)
        db.commit()
        db.refresh(debate)
        print(f"Debate started successfully with id {debate.id}")
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test()
