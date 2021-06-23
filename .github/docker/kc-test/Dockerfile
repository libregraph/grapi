ARG python_version
FROM python:${python_version}-buster

WORKDIR /app

SHELL ["/bin/bash", "-c"]

# Required packages.
RUN apt-get update && \
        apt-get install -y git libicu-dev libcrypto++-dev \
        libncurses-dev uuid-dev libxml2-dev libmariadbclient-dev libxapian-dev \
        zlib1g-dev libgoogle-perftools-dev libcurl4-openssl-dev \
        swig pkg-config libhx-dev libdb5.3++-dev apt-transport-https \
        ca-certificates curl gnupg-agent \
        wget make gcc g++ libev-dev libcap-dev libldap2-dev libsasl2-dev \
        libzip-dev libbz2-dev libreadline-dev \
        libssl-dev libsqlite3-dev libffi-dev autoconf libtool

# Shared and certificate.
RUN wget https://github.com/smallstep/cli/releases/download/v0.15.2/step-cli_0.15.2_amd64.deb && \
        dpkg -i step-cli_0.15.2_amd64.deb && \
        rm step-cli_0.15.2_amd64.deb
# Create certificates.
RUN mkdir -p /srv/shared/ && \
      cd /srv/shared/ && \
      step certificate create root-ca root-ca.crt root-ca.key --profile root-ca --insecure --no-password && \
      step certificate install root-ca.crt && \
      step certificate create $(hostname -f) server.crt server.key --san $(hostname -f) --san $(hostname -s) --profile leaf --ca ./root-ca.crt --ca-key ./root-ca.key --no-password --insecure --not-after "$(date --date "next year" -Iseconds)"

# Kopano packages.
RUN curl -fsSL https://repo.kopano.com/kopano/one/20.09/gpg | apt-key add - && \
        apt-key fingerprint B9DA48E3 && \
        echo "deb https://repo.kopano.com/kopano/one/20.09 $(grep 'VERSION=' /etc/os-release | grep -Po '\(.*\)' | sed -E 's/\(|\)//g') supported" > /etc/apt/sources.list.d/kopano.list && \
        apt-get update && \
        apt-get install -y libgsoap-dev libical-dev libvmime-dev libjsoncpp-dev libkcoidc-dev gsoap

# Kopano core.
RUN mkdir /app/core && \
        cd /app/core && \
        git clone https://stash.kopano.io/scm/kc/kopanocore.git . && \
        ./bootstrap.sh && \
        ./configure --enable-release --without-php --enable-kcoidc TCMALLOC_LIBS="-ltcmalloc_minimal" PYTHON=python3 && \
        make -j8

# Kopano core setup.
RUN mkdir cfg
COPY .github/docker/kc-test/server.cfg cfg/
COPY .github/docker/kc-test/ldap.cfg cfg/
COPY .github/docker/kc-test/ldap.propmap.cfg cfg/
COPY .github/docker/kc-test/openldap.cfg cfg/

# Core entry files.
COPY .github/docker/kc-test/core.sh /app/core/
COPY .github/docker/kc-test/store.sh /app/core/
RUN chmod +x /app/core/core.sh && chmod +x /app/core/store.sh

# Grapi
COPY . /app/grapi/
RUN cd /app/grapi && \
        ls . && \
        sed -i 's/kopano/#kopano/g' requirements.txt && \
        sed -i 's/MAPI/#MAPI/g' requirements.txt && \
        pip --version && \
        pip install -r requirements.txt -r requirements-dev.txt && \
        pip install pytest

# Grapi entry file.
COPY .github/docker/kc-test/grapi.sh /app/grapi/
COPY .github/docker/kc-test/test.sh /app/grapi/
RUN chmod +x /app/grapi/grapi.sh && chmod +x /app/grapi/test.sh
