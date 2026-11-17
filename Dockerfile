FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY name_check ./name_check
ENV HOST=0.0.0.0 PORT=8090
EXPOSE 8090
USER nobody
CMD ["python", "-m", "name_check"]
