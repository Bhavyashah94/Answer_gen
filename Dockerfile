FROM python:3.10

RUN apt-get update && apt-get install -y \
    pandoc \
    texlive-xetex \
    fonts-freefont-ttf \
    texlive-fonts-recommended \
    texlive-latex-extra \
    wget \
    curl \
    && apt-get clean

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
