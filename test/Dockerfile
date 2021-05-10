ARG docker_repo=kopano
ARG kopano_core_version=latest
FROM ${docker_repo}/kopano_core:${kopano_core_version}

ARG WORKSPACE=/workspace
ENV WORKSPACE=${WORKSPACE}
WORKDIR ${WORKSPACE}

ARG EXTRA_PACKAGES=""
RUN echo "Extra packages: $EXTRA_PACKAGES"

RUN apt-get update && apt-get install --no-install-recommends -y \
	build-essential \
	ca-certificates \
	isort \
	libcap-dev \
	libdb-dev \
	libev-dev \
	libldap2-dev \
	libpcap-dev \
	libsasl2-dev \
	python3-dev \
	python3-pip \
	python3-pytest \
	python3-pytest-cov \
	python3-wheel \
	flake8 \
	python3-kopano \
	$EXTRA_PACKAGES

CMD [ "/bin/true" ]
