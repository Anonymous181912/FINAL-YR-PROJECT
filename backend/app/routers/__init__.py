from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.patients.router import router as patients_router
from app.reports.router import router as reports_router
from app.prescriptions.router import router as prescriptions_router
from app.history.router import router as history_router

router = None
