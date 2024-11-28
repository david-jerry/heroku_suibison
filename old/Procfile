# predeploy: alembic stamp head && alembic revision --autogenerate -m "Migration Message" && alembic upgrade head
web: gunicorn -k uvicorn.workers.UvicornWorker main:app
telegram: python telegram_bot.py
# worker: celery -A src.celery_tasks.celery_app worker --loglevel=INFO -E
# beat: celery -A src.celery_tasks.celery_app beat --loglevel=INFO
# celery_flower: celery -A src.celery_tasks.celery_app flower --address=0.0.0.0 --port=5555
