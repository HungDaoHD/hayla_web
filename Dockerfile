FROM python:3.13.3
WORKDIR /
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["bash","-lc","uvicorn main:app --host 0.0.0.0 --port 8000"]