# syntax=docker/dockerfile:1

# Version elastio cli what will use like base image.
# You can find the latest version at this link.
# https://gallery.ecr.aws/elastio-dev/elastio-cli
FROM public.ecr.aws/elastio-dev/elastio-cli:latest

RUN apt-get update
RUN \
    set -ex \
    && apt-get install -y --no-install-suggests --no-install-recommends \
        python3-pip python3

COPY requirements.txt  ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY failed_ecs_handler.py ./
COPY failed_ecs_handler_config.py ./

# Clean up
RUN \
   set -ex \
   && apt-get purge python3-pip -y \
   && apt-get autoremove -y \
   && apt-get clean -y \
   && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["python3"]
CMD ["failed_ecs_handler.py"]
