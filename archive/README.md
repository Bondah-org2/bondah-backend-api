# Archive

Nothing in this folder is used by the application, the tests or the deployment. It is kept for reference after the project was restructured.

| Folder | Contents |
|---|---|
| `legacy-scripts/` | One-off `fix_*`, `debug_*`, `test_*`, `create_*` scripts that were run by hand against the old Railway database. **Do not run them**: several modify or reset data. |
| `sql-patches/` | Hand-written SQL that was applied in pgAdmin. The Django migrations in `dating/migrations/` are the source of truth for the schema. |
| `railway/` | The old Railway deploy files (`start.sh`, `Procfile`, `railway.json`, `build.sh`, `runtime.txt`). |
| `schema-dumps/` | Old generated OpenAPI files. Generate a fresh one with `python manage.py spectacular --file schema.yml`. |
| `legacy-code/` | Commented-out code that sat between classes in the old `views.py` and `serializers.py`. |
| `misc/` | The Windows virtualenv that was committed by mistake, an empty `bondah_db2` file, unused modules, and `env_production.txt`. |

`misc/env_production.txt` and the old `env_sample.txt` (now `.env.example`) contained a real-looking JWT secret and database password. Both are in git history; rotate them if they were ever live.

Everything here can be deleted once the team no longer needs it; git history keeps a copy.
