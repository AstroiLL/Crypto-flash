#docker build -t btc-14 .
FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8052

CMD ["python", "./app-BTC-14.py"]

#docker run -it --name btc-14 -p 8050:8050 btc-14

