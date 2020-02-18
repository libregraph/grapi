ARG docker_repo=zokradonh
FROM ${docker_repo}/kopano_core

RUN useradd -m -u 107 jenkins

WORKDIR /workspace/

RUN apt-get update && apt-get install --no-install-recommends -y \
	python3-kopano libev-dev libldap2-dev libsasl2-dev python3-pip python3-setuptools \
	build-essential python3-dev python3-pillow libcap-dev

CMD [ "/bin/bash" ]
