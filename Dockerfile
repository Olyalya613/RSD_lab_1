# Match the native baseline's Python release; dependencies are locked.
ARG PYTHON_IMAGE=python:3.12.10-slim-bookworm
FROM ${PYTHON_IMAGE} AS dependencies
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
COPY requirements.lock.txt /tmp/requirements.lock.txt
RUN /opt/venv/bin/python -m pip install -r /tmp/requirements.lock.txt

FROM ${PYTHON_IMAGE} AS runtime
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=dependencies /opt/venv /opt/venv
RUN groupadd --gid 1000 api && useradd --uid 1000 --gid api --no-create-home api
COPY --chown=1000:1000 app.py requirements.lock.txt /app/
COPY --chown=1000:1000 docs/schema.sql docs/travel_api_swagger.json /app/docs/
USER 1000:1000
EXPOSE 4567
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4567/health',timeout=3).read()"
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "4567", "--workers", "1"]
