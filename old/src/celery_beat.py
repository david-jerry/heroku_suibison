import json
from celery.schedules import crontab
from datetime import datetime
from fastapi.encoders import jsonable_encoder
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Any, List, Literal, Optional
from src.celery_tasks import celery_app
from src.apps.accounts.models import CeleryBeat, User
from src.errors import IncorrectScheduleDuration

def create_cron_schedule(scheduling_type: str, start_datetime: datetime, end_datetime: datetime):
    if end_datetime <= start_datetime:
        return None  # Or handle as needed

    start_time = start_datetime.time()
    start_day = start_datetime.day
    start_month = start_datetime.month
    start_weekday = start_datetime.weekday()
    cron_kwargs = {
        "hour": start_time.hour,
        "minute": start_time.minute,
    }

    if scheduling_type == "daily":
        cron_kwargs.update({"day_of_month": "*", "month_of_year": "*"})
    elif scheduling_type == "weekly":
        cron_kwargs.update({"day_of_week": start_weekday})
    elif scheduling_type == "weekdays":
        cron_kwargs.update({"day_of_week": "mon-fri"})
    elif scheduling_type == "monthly":
        cron_kwargs.update({"day_of_month": start_day})
    elif scheduling_type == "yearly":
        cron_kwargs.update({"day_of_month": start_day, "month_of_year": start_month})
    elif scheduling_type == "once":
        cron_kwargs.update({
            "day_of_month": start_day,
            "month_of_year": start_month,
            "day_of_week": start_weekday,
        })
    elif scheduling_type == "hourly":
        cron_kwargs.update({"hour": "*", "minute": start_time.minute})
    elif scheduling_type == "minutes":
        cron_kwargs.update({"minute": start_time.minute})
    else:
        raise ValueError("Invalid scheduling type")

    return crontab(**cron_kwargs)


class TemplateScheduleSQLRepository:
    def __init__(self) -> None:
        pass
    
    async def get_periodic_taskks(self, session: AsyncSession) -> List[CeleryBeat]:
        db_result = await session.exec(select(CeleryBeat).order_by(CeleryBeat.updated_at))
        tasks = db_result.all()
        return tasks

    async def save(
        self,
        tasks_args: List[str],
        tasks_kwargs: Any,
        task_name: str,
        schedule_type: Literal["daily", "weekly", "weekdays", "monthly", "yearly", "once", "hourly", "minutes"],
        start_datetime: datetime,
        end_datetime: datetime,
        session: AsyncSession,
    ) -> None:
        # Generate cron schedule
        cron_value = create_cron_schedule(
            schedule_type,
            start_datetime,
            end_datetime,
        )
        
        if cron_value is None:
            raise IncorrectScheduleDuration()

        # Serialize cron settings for storage
        cron_dict = {
            "minute": cron_value._orig_minute,
            "hour": cron_value._orig_hour,
            "day_of_week": cron_value._orig_day_of_week,
            "day_of_month": cron_value._orig_day_of_month,
            "month_of_year": cron_value._orig_month_of_year,
        }

        # Create a CeleryBeat entry
        periodic_task = CeleryBeat(
            task_name=task_name,
            task_args=json.dumps(tasks_args),
            task_kwargs=json.dumps(jsonable_encoder(tasks_kwargs)),
            crontab=json.dumps(cron_dict),
            schedule_type=schedule_type,
        )
        
        session.add(periodic_task)
        await session.commit()
        
        celery_app.add_periodic_task(    
            sig=celery_app.signature(name=periodic_task.uid, varies=True),
            name=task_name,
            schedule=cron_value,
            args=periodic_task.task_args,
            kwargs=periodic_task.task_kwargs
        )
        await session.refresh(periodic_task)  # Optional: refresh to get generated values like uid
        return None

