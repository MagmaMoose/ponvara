# kics-scan ignore
# ponvara — Phase 1: a slim, REST-based Dependency-Track → DefectDojo sync.
# No Django ORM and no defectdojo-django base image — just Python + httpx, so the
# image is ~80 MB and no longer pinned to DefectDojo's version.
FROM python:3.12-slim

WORKDIR /opt/ponvara
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir . \
    && useradd --system --uid 10001 ponvara

USER 10001
ENTRYPOINT ["ponvara"]
CMD ["sync"]
