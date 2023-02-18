# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster

WORKDIR /master-distributed_system
COPY . .

# this allow to see stdout
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y iputils-ping
RUN pip3 install -r requirements.txt

CMD [ "python3", "master.py"]
