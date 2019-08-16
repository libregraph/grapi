#!/usr/bin/env groovy

pipeline {
	agent {
		docker {
			image 'ubuntu:bionic'
			args '-u 0'
		}
	}
	environment {
		CI = 'true'
		DEBIAN_FRONTEND = 'noninteractive'
		REPO_URL = 'https://download.kopano.io/supported/core:/master/Ubuntu_18.04/'
	}
	stages {
		stage('Bootstrap') {
			steps {
				echo 'Bootstrapping'
				sh 'apt-get update && apt-get install -y \
					apt-transport-https \
					ca-certificates \
					libcap-dev \
					libdb-dev \
					libev-dev \
					libldap2-dev \
					libpcap-dev \
					libsasl2-dev \
					python3-pip \
					python3-pytest \
					flake8 \
					'
				sh 'echo "deb [trusted=yes] ${REPO_URL} ./" > /etc/apt/sources.list.d/kopano.list'
				sh 'apt-get update'
				sh 'apt-get install -y python3-kopano'

				// Filter out already installed dependencies
				sh 'grep -Ev "kopano|MAPI"  requirements.txt > jenkins_requirements.txt'
				sh 'pip3 install -r jenkins_requirements.txt'
			}
		}
		stage('Lint') {
			steps {
				echo 'Linting..'
				sh 'make lint > pylint.log || exit 0'
				recordIssues tool: pyLint(pattern: 'pylint.log'), qualityGates: [[threshold: 40, type: 'TOTAL', unstable: true]]
			}
		}
		stage('Test') {
			steps {
				echo 'Testing..'
				sh 'make test'
			}
		}
	}
	post {
		always {
			cleanWs()
        }
	}
}
