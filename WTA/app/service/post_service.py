from sqlmodel import Session
import uuid

from app.models.models import PollingJob


def creating_polling_job(symbols: list[str], interval: int, provider: str, session: Session):
    job_id = uuid.uuid4()

    new_job = PollingJob(job_id=job_id, symbols=symbols, interval=interval, provider=provider, is_active=True)
    return_config = {
        "symbols": symbols,
        "interval": interval,

    }
    try:
        session.add(new_job)
        session.commit()
        session.refresh(new_job)
        return {"job_id": str(new_job.job_id), "status":"accepted", "config": return_config}
    except Exception as e:
        session.rollback()
        raise Exception(f"Error creating polling job: {str(e)}")
    finally:
        session.close()

