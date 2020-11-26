#!/usr/bin/env groovy

def buildNumber = env.BUILD_NUMBER as int
if (buildNumber > 1) milestone(buildNumber - 1)
milestone(buildNumber)

pipeline {
	agent none
	environment {
		CI = 'true'
		DEBIAN_FRONTEND = 'noninteractive'
		REPO_URL = 'https://download.kopano.io/supported/core:/master/Debian_10/'
		PYTHONDONTWRITEBYTECODE = '1'
	}
	stages {
		stage('Lint/Test') {
			agent {
				docker {
					image 'debian:buster'
					args '-u 0 -e PYTHONDONTWRITEBYTECODE=1'
					label 'docker'
				}
			}
			stages {
				stage('Bootstrap') {
					steps {
						echo 'Bootstrapping'
						sh 'apt-get update && apt-get install -y \
							apt-transport-https \
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
							'
						sh 'echo "deb [trusted=yes] ${REPO_URL} ./" > /etc/apt/sources.list.d/kopano.list'
						sh 'apt-get update'
						sh 'apt-get install -y python3-kopano'

						// Filter out already installed dependencies
						sh 'grep -Ev "kopano|MAPI"  requirements.txt > /tmp/jenkins_requirements.txt'
						sh 'pip3 install -r /tmp/jenkins_requirements.txt'
					}
				}
				stage('Lint') {
					steps {
						echo 'Linting..'
						sh 'make lint > pylint.log || true'
						recordIssues tool: pyLint(pattern: 'pylint.log'), qualityGates: [[threshold: 40, type: 'TOTAL', unstable: true]]
						echo 'Isort..'
						sh 'make test-isort'
					}
				}
				stage('Test') {
					steps {
						echo 'Testing..'
						sh 'PYTEST_OPTIONS="-s -p no:cacheprovider" make test'
					}
				}
			}
		}
		stage('Integration Test') {
			agent { label 'docker' }
			stages {
				stage('Run test') {
					steps {
						echo 'Integration testing..'
						sh 'make -C test test-backend-kopano-ci-run EXTRA_LOCAL_ADMIN_USER=$(id -u) DOCKERCOMPOSE_UP_ARGS=--build DOCKERCOMPOSE_EXEC_ARGS="-T -u $(id -u) -e HOME=/workspace" || true'
						sh 'chown -R $(id -u) test/coverage || true'
						junit 'test/coverage/integration/backend.kopano/integration.xml'
						publishHTML([allowMissing: false, alwaysLinkToLastBuild: false, keepAll: true, reportDir: 'test/coverage/integration/backend.kopano', reportFiles: 'index.html', reportName: 'Kopano Backend Coverage Report', reportTitles: ''])
					}
				}
			}
			post {
				always {
					sh 'make -C test test-backend-kopano-ci-clean'
				}
			}
		}
	}
}
