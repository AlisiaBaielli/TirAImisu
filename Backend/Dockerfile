# Has Python + Chromium + all Playwright deps preinstalled
FROM mcr.microsoft.com/playwright/python:v1.55.0

WORKDIR /app

# Prevent pyc files, force unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=UTC

# Copy and install Python deps
# If you don't have this yet, generate with: pip freeze > Backend/requirements.txt
COPY Backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt

# # Ensure Chromium is installed (usually already in base)
# RUN python -m playwright install --with-deps chromium

# Copy backend code
COPY Backend /app/Backend

EXPOSE 8000

# Single worker, no reload (stable for browser automation)
CMD ["python", "-m", "uvicorn", "Backend.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

