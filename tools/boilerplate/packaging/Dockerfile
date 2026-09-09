ARG KT_SCAFFOLD_BASE_IMAGE=python:3.13-alpine3.23@sha256:7ea3f82de8ea6d4fb7e5d2bbe3fe3c9d931700b7a529f1fe5769e42abe514ca1
FROM ${KT_SCAFFOLD_BASE_IMAGE}
ARG KT_SCAFFOLD_VERSION=0.3.0
ARG TARGETARCH

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_INDEX=1 \
    PIP_FIND_LINKS=/opt/wheelhouse

COPY alpine-runtime-packages.lock /locks/alpine-runtime-packages.lock
COPY apk/ /opt/apk/
RUN set -eu; \
    set -- $(awk -v arch="$TARGETARCH" '$1 == arch { print $2, $3, $4 }' \
        /locks/alpine-runtime-packages.lock); \
    [ "$#" -eq 3 ]; \
    package_spec="$2"; expected_sha256="$3"; \
    package_file="${package_spec%%=*}-${package_spec#*=}.apk"; \
    echo "${expected_sha256}  /opt/apk/${package_file}" | sha256sum -c -; \
    apk add --no-cache --no-network --repositories-file /dev/null "/opt/apk/${package_file}"; \
    rm -rf /opt/apk; \
    addgroup -g 10001 scaffold \
    && adduser -D -H -u 10001 -G scaffold scaffold

COPY wheelhouse/generator/ /opt/wheelhouse/
COPY kt_scaffold-*.whl /opt/wheelhouse/
RUN python -m pip install --no-cache-dir "kt-scaffold==${KT_SCAFFOLD_VERSION}" \
    && python -m pip uninstall --yes pip \
    && rm -rf /root/.cache /opt/wheelhouse

WORKDIR /out
USER 10001:10001
ENTRYPOINT ["kt-scaffold"]
