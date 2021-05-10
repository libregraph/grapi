#!/usr/bin/env groovy

def buildNumber = env.BUILD_NUMBER as int
if (buildNumber > 1) milestone(buildNumber - 1)
milestone(buildNumber)

pipeline {
	agent none
	options {
		timeout(time: 30, unit: 'MINUTES')
	}
	stages {
		stage('Lint and Unit Test') {
			agent {
				dockerfile {
					filename 'Dockerfile.build'
					args '-e PYTHONDONTWRITEBYTECODE=1 -e HOME=${WORKSPACE} -e WORKSPACE=${WORKSPACE} -e PATH=${WORKSPACE}/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
					label 'docker'
					additionalBuildArgs '--build-arg=REPO_URL=https://download.kopano.io/supported/core:/master/Debian_10/'
				}
			}
			stages {
				stage('Bootstrap') {
					steps {
						echo 'Bootstrapping'
						sh 'pip3 install -r requirements-dev.txt'
						// Filter out already installed dependencies
						sh 'grep -Ev "kopano|MAPI"  requirements.txt > /tmp/jenkins_requirements.txt'
						sh 'pip3 install -r /tmp/jenkins_requirements.txt'
					}
				}
				stage('Lint') {
					steps {
						echo 'Linting..'
						sh 'make lint | tee pylint.log || true'
						recordIssues tool: pyLint(pattern: 'pylint.log'), qualityGates: [[threshold: 35, type: 'TOTAL', unstable: true]]
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
		stage('Integration Test Suite') {
			agent {
				label 'docker'
			}
			stages {
				stage('Run test') {
					steps {
						echo 'Integration testing..'
						sh 'make -C test test-backend-kopano-ci-run EXTRA_LOCAL_ADMIN_USER=$(id -u) DOCKERCOMPOSE_EXEC_ARGS="-T -u $(id -u) -e HOME=${WORKSPACE}" || true'
						junit 'test/coverage/integration/backend.kopano/integration.xml'
						publishHTML([allowMissing: false, alwaysLinkToLastBuild: false, keepAll: true, reportDir: 'test/coverage/integration/backend.kopano', reportFiles: 'index.html', reportName: 'Kopano Backend Coverage Report', reportTitles: ''])
					}
				}
			}
			post {
				always {
					sh 'make -C test test-backend-kopano-ci-logs DOCKERCOMPOSE_LOGS_ARGS="--timestamps --no-color" || true'
					sh 'make -C test test-backend-kopano-ci-clean'
				}
			}
		}
	}
}
