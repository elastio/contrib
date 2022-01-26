# syntax=docker/dockerfile:1
ARG REGISTRY=public.ecr.aws/elastio-dev/

# Possible values: amd64 or arm64
ARG ARCH=amd64
# Version elastio cli what will use like base image.
# Most likely this is not the latest version of elastio cli.
# You can find the latest version at this link.
# https://gallery.ecr.aws/elastio-dev/elastio-cli
ARG VERSION_TAG=0.9.0-master
FROM ${REGISTRY}elastio-cli:${VERSION_TAG}-${ARCH}

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y python3-pip python3
COPY requirements.txt  ./
RUN pip3 install --no-cache-dir -r requirements.txt
COPY app.py ./
COPY s3reader.py ./

ENTRYPOINT [  ]
CMD python3 app.py
