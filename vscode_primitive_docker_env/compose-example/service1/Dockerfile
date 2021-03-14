FROM python:3.7.3-alpine3.9 AS base

WORKDIR /workspace
COPY ./requirements.txt /workspace/requirements.txt
RUN pip install -r requirements.txt

WORKDIR /workspace/sources

# debugger1

FROM base AS debugger1
RUN pip install debugpy
ENTRYPOINT ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client"]

# debugger2

FROM base AS debugger2
RUN pip install ptvsd
ENTRYPOINT ["python", "-m", "ptvsd", "--host", "0.0.0.0", "--port", "5678", "--wait"]

# prod

FROM base AS prod
ENTRYPOINT ["python"]