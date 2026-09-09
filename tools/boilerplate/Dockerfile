# Connected AppSec build entrypoint. The air-gapped artifact factory continues to use
# packaging/Dockerfile with its prebuilt, checksum-sealed bundle context.
ARG KT_SCAFFOLD_BASE_IMAGE=python:3.13-alpine3.23@sha256:7ea3f82de8ea6d4fb7e5d2bbe3fe3c9d931700b7a529f1fe5769e42abe514ca1

FROM ${KT_SCAFFOLD_BASE_IMAGE} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONHASHSEED=0 \
    SOURCE_DATE_EPOCH=315532800

WORKDIR /build
COPY packaging/locks/generator-linux-amd64-cp313-musllinux.requirements.lock /locks/generator.lock
COPY packaging/locks/build-system.requirements.lock /locks/build-system.lock
RUN python -m pip download \
        --require-hashes \
        --only-binary=:all: \
        --dest /wheelhouse \
        -r /locks/generator.lock \
    && python -m venv /build-env \
    && /build-env/bin/python -m pip install \
        --no-index \
        --only-binary=:all: \
        --require-hashes \
        --find-links /wheelhouse \
        -r /locks/build-system.lock

COPY pyproject.toml README.md MANIFEST.in ./
COPY rules/ rules/
COPY agent-platform/agent-catalog.schema.json \
     agent-platform/agent-catalog.yml \
     agent-platform/agent-contract.schema.json \
     agent-platform/agent-policy.schema.json \
     agent-platform/client-capabilities.yml \
     agent-platform/conformance-snapshot.schema.json \
     agent-platform/decision-policy.schema.json \
     agent-platform/orchestration.schema.json \
     agent-platform/runtime-candidate.schema.json \
     agent-platform/standards-crosswalk.yml \
     agent-platform/
COPY agent-platform/agents/ agent-platform/agents/
COPY agent-platform/orchestrations/ agent-platform/orchestrations/
COPY agent-platform/policies/ agent-platform/policies/
COPY src/kt_scaffold/ src/kt_scaffold/
RUN PIP_NO_INDEX=1 /build-env/bin/python -m build \
    --no-isolation \
    --wheel \
    --outdir /dist \
    .

FROM ${KT_SCAFFOLD_BASE_IMAGE}
ARG KT_SCAFFOLD_VERSION=0.3.0
ARG TARGETARCH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_INDEX=1 \
    PIP_FIND_LINKS=/opt/wheelhouse

COPY packaging/locks/alpine-runtime-packages.lock /locks/alpine-runtime-packages.lock
RUN set -eu; \
    set -- $(awk -v arch="$TARGETARCH" '$1 == arch { print $2, $3, $4 }' \
        /locks/alpine-runtime-packages.lock); \
    [ "$#" -eq 3 ]; \
    alpine_arch="$1"; package_spec="$2"; expected_sha256="$3"; \
    package_file="${package_spec%%=*}-${package_spec#*=}.apk"; \
    wget -q \
        "https://dl-cdn.alpinelinux.org/alpine/v3.23/main/${alpine_arch}/${package_file}" \
        -O "/tmp/${package_file}"; \
    echo "${expected_sha256}  /tmp/${package_file}" | sha256sum -c -; \
    apk add --no-cache --no-network --repositories-file /dev/null "/tmp/${package_file}"; \
    rm -f "/tmp/${package_file}"; \
    addgroup -g 10001 scaffold \
    && adduser -D -H -u 10001 -G scaffold scaffold

COPY --from=builder /wheelhouse/ /opt/wheelhouse/
COPY --from=builder /dist/kt_scaffold-*.whl /opt/wheelhouse/
RUN python -m pip install --no-cache-dir "kt-scaffold==${KT_SCAFFOLD_VERSION}" \
    && python -m pip uninstall --yes pip \
    && rm -rf /root/.cache /opt/wheelhouse

WORKDIR /out
USER 10001:10001
ENTRYPOINT ["kt-scaffold"]
