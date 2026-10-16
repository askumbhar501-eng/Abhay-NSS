from .sensors import router as sensors_router
from .network import router as network_router
from .detection import router as detection_router, run_detection_cycle
from .alerts import router as alerts_router
from .repairs import router as repairs_router
from .simulate import router as simulate_router
from .upload import router as upload_router

__all__ = [
    "sensors_router",
    "network_router",
    "detection_router",
    "run_detection_cycle",
    "alerts_router",
    "repairs_router",
    "simulate_router",
    "upload_router",
]
