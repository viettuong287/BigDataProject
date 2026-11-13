FROM apache/superset:4.1.2

USER root
# psycopg2: driver để Superset kết nối Neon Postgres.
RUN pip install --no-cache-dir psycopg2-binary==2.9.10
COPY docker-init.sh /app/docker-init.sh
RUN sed -i 's/\r$//' /app/docker-init.sh && chmod +x /app/docker-init.sh
# Superset 4.1 không có sẵn tiếng Việt: biên dịch bản dịch riêng (.mo cho backend, .json cho frontend).
COPY i18n /app/i18n
RUN python /app/i18n/build_catalog.py /app/i18n/vi/LC_MESSAGES/messages.po \
        /app/superset/translations/vi/LC_MESSAGES \
    && chown -R superset:superset /app/superset/translations/vi
# Nhận diện "Olist Insight" (logo, favicon) và font + CSS chung cho mọi trang (thanh menu, đăng nhập).
COPY branding /app/superset/static/assets/images/olist
COPY templates/tail_js_custom_extra.html /app/superset/templates/tail_js_custom_extra.html
USER superset

CMD ["/app/docker-init.sh"]
