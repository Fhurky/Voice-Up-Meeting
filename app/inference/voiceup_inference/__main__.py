"""Single-process bootstrap; never use multiple Uvicorn workers for this GPU service."""

import logging
import sys

import uvicorn
from pydantic import ValidationError

from .api import create_app
from .config import load_settings


def main() -> None:
    try:
        settings = load_settings()
    except ValidationError:
        print(
            '{"event":"inference_startup_failed","code":"invalid_configuration"}', file=sys.stderr
        )
        raise SystemExit(2) from None
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    request_logger = logging.getLogger("voiceup.inference")
    request_logger.handlers = [handler]
    request_logger.setLevel(logging.INFO)
    request_logger.propagate = False
    # Disable third-party chatter and HTTP payload/access logging. Errors returned
    # by the service are stable codes; logs never contain model paths or tokens.
    for name in ("speechbrain", "huggingface_hub", "urllib3"):
        logging.getLogger(name).setLevel(logging.ERROR)
    uvicorn.run(
        create_app(settings), host=settings.host, port=settings.port, workers=1, access_log=False
    )


if __name__ == "__main__":
    main()
