"""案件驾驶舱 FastAPI 入口"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.auth import get_current_user
from app.routers import ai, auth, cases, documents, events, lawyers, notifications, settings, stats

try:
    from app.config_env import load_env_file
    load_env_file()
except ImportError:
    pass

app = FastAPI(title="案件驾驶舱 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

protected = [Depends(get_current_user)]

app.include_router(auth.router)
app.include_router(cases.router, dependencies=protected)
app.include_router(lawyers.router, dependencies=protected)
app.include_router(stats.router, dependencies=protected)
app.include_router(notifications.router, dependencies=protected)
app.include_router(documents.router, dependencies=protected)
app.include_router(ai.router, dependencies=protected)
app.include_router(settings.router, dependencies=protected)
app.include_router(events.router, dependencies=protected)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

    # SQLite 自动迁移：补充 create_all 无法追加的列
    try:
        import sqlite3, os
        db_path = os.path.join(os.path.dirname(__file__), "..", "smart_justice.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            for stmt in [
                "ALTER TABLE cases ADD COLUMN core_summary TEXT DEFAULT ''",
                "ALTER TABLE notifications ADD COLUMN document_id INTEGER REFERENCES case_documents(id)",
                "ALTER TABLE case_documents ADD COLUMN ai_match_result TEXT",
                "ALTER TABLE case_documents ADD COLUMN ai_progress TEXT DEFAULT ''",
            ]:
                try:
                    conn.execute(stmt)
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # 列已存在
            conn.close()
    except Exception:
        pass

    # 从 config.json 同步非敏感 AI 配置，密钥由 .env/环境变量提供
    try:
        from app.routers.settings import _load_config, _sync_env
        config = _load_config()
        _sync_env(config)
    except Exception:
        pass
