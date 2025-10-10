# Derived from suggestions at pythonspeed.com

FROM python:3.13-slim-trixie AS compile-image
RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc

RUN python3 -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"


RUN pip3 install --upgrade pip
COPY requirements.txt .
RUN pip3 install -r requirements.txt

FROM python:3.13-slim-trixie AS build-image
COPY --from=compile-image /opt/venv /opt/venv

RUN mkdir -p /opt/modbot
COPY src /opt/modbot/src

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /opt/modbot/src/
