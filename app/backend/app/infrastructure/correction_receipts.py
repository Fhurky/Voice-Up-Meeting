"""Purpose-separated local HMAC proof; the opaque result is never an authentication token."""

import base64
import hashlib
import hmac
import re
from datetime import datetime

from pydantic import ValidationError

from app.core.config import Settings
from app.services.speaker_ports import SpeakerError
from app.services.transcript_revision_ports import CorrectionSaveProof

_PURPOSE = b"voiceup/transcript-correction/save-receipt/v1"
_TOKEN = re.compile(r"vcr1:([A-Za-z0-9_-]+)\.([a-f0-9]{64})")
MAX_RECEIPT_CHARACTERS = 32768


class CorrectionReceiptSigner:
    def __init__(self, settings: Settings) -> None:
        self._key = hmac.digest(
            settings.jwt_secret.get_secret_value().encode("utf-8"), _PURPOSE, "sha256"
        )

    def sign(self, proof: CorrectionSaveProof) -> str:
        encoded = (
            base64.urlsafe_b64encode(proof.model_dump_json().encode("utf-8"))
            .decode("ascii")
            .rstrip("=")
        )
        signed = "vcr1:" + encoded
        return (
            signed + "." + hmac.new(self._key, signed.encode("ascii"), hashlib.sha256).hexdigest()
        )

    def verify(self, token: str, *, now: datetime) -> CorrectionSaveProof:
        try:
            if len(token) > MAX_RECEIPT_CHARACTERS or now.tzinfo is None or now.utcoffset() is None:
                raise ValueError("invalid_receipt")
            match = _TOKEN.fullmatch(token)
            if match is None:
                raise ValueError("invalid_receipt")
            encoded, received = match.groups()
            expected = hmac.new(
                self._key, ("vcr1:" + encoded).encode("ascii"), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(received, expected):
                raise ValueError("invalid_receipt")
            raw = base64.b64decode(
                encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
            )
            proof = CorrectionSaveProof.model_validate_json(raw)
            if not proof.issued_at <= now.timestamp() < proof.expires_at:
                raise ValueError("invalid_receipt")
            return proof
        except (ValueError, UnicodeError, ValidationError):
            raise SpeakerError("invalid_correction_token", 422) from None
