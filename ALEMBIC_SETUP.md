# How to Use and Install Alembic for FASTAPI

[read more](https://testdriven.io/blog/fastapi-sqlmodel/)
Installing Alembic...

```bash
pip install alembic
```

## Initialize Alembic for async PostgreSQL with SQLModel support

Initializing Alembic for async PostgreSQL...

```bash
alembic init -t async migrations
```

## Instructions for editing env.py

"Alembic initialized."

### Next steps

1. Open the generated *`migrations/env.py`* file.
2. Add your models' imports to *`env.py`*. For example:
`from your_project.models import YourModel`

3. Import SQLModel and set *`target_metadata`*. Add the following line in 'env.py':
`from sqlmodel import SQLModel`

4. Replace the existing *`target_metadata`* line with:
`target_metadata = SQLModel.metadata`

5. Open the generated `migrations/script.py.mako` file:

6. import the model driver file to your project. For example:
`import sqlmodel`

7. Open the generated `./alembic.ini` file.
This will ensure te persistent state of the database remains the same

- Add the database driver you are working with:
`sqlalchemy.url = postgresql+asyncpg://username:password@localhost:5432/db_name`

Make sure to complete these steps before running an initial migration.

```bash
alembic revision --autogenerate -m "Migration Message"
alembic upgrade head
alembic stamp head # if the database is not uptodate
```
