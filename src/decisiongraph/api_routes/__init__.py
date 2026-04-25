from decisiongraph.api_routes.decisions import create_decision_router
from decisiongraph.api_routes.ingestion import create_ingestion_router
from decisiongraph.api_routes.intelligence import create_intelligence_router
from decisiongraph.api_routes.system import create_system_router

__all__ = [
    'create_system_router',
    'create_decision_router',
    'create_ingestion_router',
    'create_intelligence_router',
]
