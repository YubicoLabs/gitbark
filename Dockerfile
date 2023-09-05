FROM python:3.9
FROM ubuntu:latest


RUN apt-get update
RUN apt-get install -y --no-install-recommends python3-setuptools python3-pip gcc python3-dev musl-dev libffi-dev git gnupg bash
#RUN apk add --no-cache build-base gcc python3-dev postgresql-dev musl-dev libffi-dev git gnupg bash
RUN apt-get install -y openssh-server
RUN pip3 install setuptools-rust
RUN pip3 install --upgrade pip
RUN pip3 install poetry


RUN ssh -V


WORKDIR /code

COPY . /code/

RUN poetry install

RUN poetry run pytest 

