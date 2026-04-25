from __future__ import annotations

from fastapi import FastAPI

from decisiongraph.api_context import (
    build_service,
    configure_auth_middleware,
    configure_cors,
    configure_rate_limit_middleware,
)
from decisiongraph.api_routes import (
    create_decision_router,
    create_ingestion_router,
    create_intelligence_router,
    create_system_router,
)

app = FastAPI(title='DecisionGraph API', version='0.1.0')
SERVICE = build_service()

configure_cors(app)
configure_auth_middleware(app)
configure_rate_limit_middleware(app)

app.include_router(create_system_router(SERVICE))
app.include_router(create_decision_router(SERVICE))
app.include_router(create_ingestion_router(SERVICE))
app.include_router(create_intelligence_router(SERVICE))
