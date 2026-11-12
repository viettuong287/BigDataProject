FROM apache/superset:4.1.2

USER root
# psycopg2: driver để Superset kết nối Neon Postgres.
RUN pip install --no-cache-dir psycopg2-binary==2.9.10
COPY docker-init.sh /app/docker-init.sh
RUN sed -i 's/\r$//' /app/docker-init.sh && chmod +x /app/docker-init.sh
USER superset

CMD ["/app/docker-init.sh"]
