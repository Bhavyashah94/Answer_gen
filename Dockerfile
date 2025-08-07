# Use a lightweight Python image
FROM python:3.10-slim

# Install required system dependencies
RUN apt-get update && \
    apt-get install -y \
    pandoc \
    texlive-xetex \
    fonts-freefont-ttf \
    texlive-fonts-recommended \
    texlive-latex-extra \
    wget \
    curl \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Streamlit default port
EXPOSE 8501

# Start the Streamlit application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
