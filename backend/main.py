import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router


def configure_logging() -> None:
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")

    for logger_name in ("backend", "core"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not any(getattr(existing, "_medchat_handler", False) for existing in logger.handlers):
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            handler._medchat_handler = True
            logger.addHandler(handler)


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="MedChat Pharmacy Agent", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)


    return app


app = create_app()
