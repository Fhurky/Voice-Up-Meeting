# Build from the repository root after dependency admission and model provisioning.
FROM python:3.13.14-slim-bookworm@sha256:67a1e1f215ccda113cfc024e8639049257e88f273898f595b61476d128d387e8
WORKDIR /srv/inference
COPY app/inference/requirements.txt /srv/inference/requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes \
    --extra-index-url https://download.pytorch.org/whl/cu128 -r requirements.txt
# Import the existing reference package without resolving its CPU-oriented extras.
COPY src/voiceup /srv/reference/voiceup
COPY app/inference/voiceup_inference /srv/inference/voiceup_inference
ENV PYTHONPATH=/srv/reference:/srv/inference PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Runtime supplies a read-only /models/speaker package and the internal service key.
USER 10001:10001
EXPOSE 8090
CMD ["python", "-m", "voiceup_inference"]
