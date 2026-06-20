import sys
from sqlalchemy import text
from src.core.database import SessionLocal

def fix_db():
    db = SessionLocal()
    try:
        # Drop the old constraint
        db.execute(text("ALTER TABLE debates DROP CONSTRAINT debates_conflict_id_fkey;"))
        # Add the new constraint
        db.execute(text("ALTER TABLE debates ADD CONSTRAINT debates_conflict_id_fkey FOREIGN KEY (conflict_id) REFERENCES reconciliation_units (id);"))
        
        db.commit()
        
        # Also need to make sure the new table debate_state exists
        from src.core.database import engine
        from src.models.base import Base
        from src.models.schema import DebateState # ensure it's imported
        
        Base.metadata.create_all(bind=engine)
        
        print("Database schema fixed.")
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix_db()
