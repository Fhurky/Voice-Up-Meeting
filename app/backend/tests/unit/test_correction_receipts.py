"""Save receipts are purpose-bound evidence, never login credentials or arbitrary client text."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from pydantic import SecretStr

from app.core.config import get_settings
from app.infrastructure.correction_receipts import CorrectionReceiptSigner
from app.services.speaker_ports import SpeakerError
from app.services.transcript_revision_ports import CorrectionSaveProof, ProofEdit


def proof(now):
    return CorrectionSaveProof(
        preview_id=uuid4(),
        actor_public_id=uuid4(),
        tenant_public_id=uuid4(),
        meeting_public_id=uuid4(),
        transcript_public_id=uuid4(),
        source_text_sha256="a" * 64,
        context_sha256="b" * 64,
        expected_revision=0,
        edits=(ProofEdit(start_char=0, end_char=3, original="ses", replacement="söz"),),
        model_name="local:latest",
        model_digest="c" * 64,
        policy_version="tr-context-words-v2",
        issued_at=int(now.timestamp()),
        expires_at=int(now.timestamp()) + 900,
    )


def test_round_trip_receipt_is_not_a_session_jwt():
    now = datetime.now(UTC)
    signer = CorrectionReceiptSigner(get_settings())
    document = proof(now)
    token = signer.sign(document)
    assert signer.verify(token, now=now) == document
    assert token.startswith("vcr1:") and len(token) <= 32768
    with pytest.raises(jwt.InvalidTokenError):
        jwt.decode(token, get_settings().jwt_secret.get_secret_value(), algorithms=["HS256"])


@pytest.mark.parametrize("mutation", ["payload", "signature", "prefix", "oversize", "whitespace"])
def test_tampering_and_invalid_token_shape_fail_closed(mutation):
    now = datetime.now(UTC)
    signer = CorrectionReceiptSigner(get_settings())
    token = signer.sign(proof(now))
    if mutation == "payload":
        token = token[:10] + ("A" if token[10] != "A" else "B") + token[11:]
    elif mutation == "signature":
        token = token[:-1] + ("a" if token[-1] != "a" else "b")
    elif mutation == "prefix":
        token = "auth:" + token[5:]
    elif mutation == "oversize":
        token = "x" * 32769
    else:
        token += "\n"
    with pytest.raises(SpeakerError, match="invalid_correction_token"):
        signer.verify(token, now=now)


def test_expiry_future_issuance_and_key_rotation_are_rejected():
    now = datetime.now(UTC)
    signer = CorrectionReceiptSigner(get_settings())
    token = signer.sign(proof(now))
    for time in [now + timedelta(seconds=900), now - timedelta(seconds=1)]:
        with pytest.raises(SpeakerError, match="invalid_correction_token"):
            signer.verify(token, now=time)
    rotated = CorrectionReceiptSigner(
        get_settings().model_copy(
            update={"jwt_secret": SecretStr("different-secret-with-more-than-32-bytes")}
        )
    )
    with pytest.raises(SpeakerError, match="invalid_correction_token"):
        rotated.verify(token, now=now)
