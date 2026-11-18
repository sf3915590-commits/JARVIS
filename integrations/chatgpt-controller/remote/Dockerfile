FROM python:3.13-slim
WORKDIR /app
COPY relay.py /app/relay.py
ENV HOST=0.0.0.0 PORT=8787 JARVIS_RELAY_DB=/data/jarvis-relay.sqlite3
VOLUME ["/data"]
EXPOSE 8787
CMD ["python", "/app/relay.py"]
