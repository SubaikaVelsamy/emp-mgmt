# 1️⃣ Base image: slim Python 3.10
FROM python:3.10-slim

# 2️⃣ Environment variables
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_DRIVER=/usr/bin/chromedriver

# 3️⃣ Install system dependencies and Chromium
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    wget unzip curl gnupg ca-certificates fonts-liberation libnss3 \
    libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxrandr2 \
    libxss1 libxtst6 xdg-utils libgtk-3-0 build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 4️⃣ Upgrade pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

# 5️⃣ Set working directory
WORKDIR /app

# 6️⃣ Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7️⃣ Copy the rest of the project
COPY . .

# 8️⃣ Expose FastAPI port
EXPOSE 8000

# 9️⃣ Run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
