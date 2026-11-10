"""Ed25519 offline licenses: clients receive only the verification key."""
import base64
import hashlib
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from app.core.config import settings


def sign_license(payload):
    if settings.OFFLINE_LICENSE_PRIVATE_KEY:
        seed = base64.b64decode(settings.OFFLINE_LICENSE_PRIVATE_KEY, validate=True)
    elif settings.is_development:
        seed = hashlib.sha256(("tourvoice-offline-v1:" + settings.SECRET_KEY).encode()).digest()
    else:
        raise RuntimeError("Offline signing key is not configured.")
    key = Ed25519PrivateKey.from_private_bytes(seed)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {**payload, "signed_payload": encoded.decode(),
            "license_signature": base64.b64encode(key.sign(encoded)).decode(),
            "public_key": base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()}
