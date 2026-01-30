FROM python:3.11-slim 
 
 
RUN wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && apt-get install -y /tmp/chrome.deb && rm /tmp/chrome.deb 
 
WORKDIR /app 
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt 
COPY . . 
EXPOSE 8080 
CMD ["python", "bot.py"] 
