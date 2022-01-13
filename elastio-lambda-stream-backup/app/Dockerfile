# syntax=docker/dockerfile:1
ARG REGISTRY=public.ecr.aws/elastio-dev/

# Possible values: amd64 or arm64
ARG ARCH=arm64
# Version elastio cli what will use like base image
ARG VERSION_TAG=0.8.0-master

# elastio cli version what be use in the imege(should be the same with red-stack version)
# to check stack version use command "aws ssm get-parameter --name /elastio/region-stack/version"
FROM ${REGISTRY}elastio-cli:${VERSION_TAG}-${ARCH}

RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y python3-pip python3
COPY requirements.txt  ./
RUN pip3 install -r requirements.txt
COPY app.py ./
COPY s3reader.py ./
COPY bootstrap.py ./

ENTRYPOINT [  ]
CMD python3 bootstrap.py
