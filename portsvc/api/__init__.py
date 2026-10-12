from fastapi import APIRouter

from portsvc.api import port

router = APIRouter()
router.include_router(port.router)
