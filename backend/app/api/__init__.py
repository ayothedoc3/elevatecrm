from app.api.inbox import router as inbox_router
from app.api.workflows import router as workflows_router
from app.api.forms import router as forms_router

__all__ = ['inbox_router', 'workflows_router', 'forms_router']
