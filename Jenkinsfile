// Define global variables to hold deployment decisions
// This avoids scoping issues with 'env' variables inside 'when' blocks
def deployAuth = false
def deployInference = false
def deployFrontend = false
def hasChanges = false

pipeline {
    agent any

    environment {
        // Credentials ID as configured in Jenkins
        DOCKER_CREDENTIALS_ID = 'docker-hub-credentials'
        DOCKER_USER = 'kondapallitarun3474'
        
        // Dynamic Image Tag
        IMAGE_TAG = "v${env.BUILD_NUMBER}"
        
        // Tags to pass to Ansible (defaults to empty)
        ANSIBLE_TAGS = ''
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Detect Changes') {
            steps {
                script {
                    def tagsList = []

                    // Print changes for visibility
                    try {
                        def changesResult = sh(script: 'git diff --name-only HEAD~1 HEAD', returnStdout: true).trim()
                        echo "Changed files:\n${changesResult}"
                    } catch (Exception e) {
                        echo "Listing changes failed (first run?), proceeding with detection..."
                    }

                    // Helper to check changes via shell (robust against string formatting issues)
                    // If git diff fails (e.g. first run), we default to 'true' (deploy match)
                    def checkChange = { pattern ->
                        try {
                            // grep returns 0 if found, 1 if not. We use || true to prevent script failure on 1.
                            // We check if output is non-empty.
                            def grepResult = sh(script: "git diff --name-only HEAD~1 HEAD | grep '${pattern}' || true", returnStdout: true).trim()
                            return !grepResult.isEmpty()
                        } catch (Exception e) {
                            return true // Assume changed if git fails
                        }
                    }

                    if (checkChange('mlops-llm4ts/model-service/auth-service/')) {
                        deployAuth = true
                        if (!tagsList.contains('auth')) tagsList.add('auth')
                    }
                    if (checkChange('mlops-llm4ts/model-service/inference-service/')) {
                        deployInference = true
                        if (!tagsList.contains('inference')) tagsList.add('inference')
                    }
                    if (checkChange('frontend-new/')) {
                        deployFrontend = true
                        if (!tagsList.contains('frontend')) tagsList.add('frontend')
                    }
                    
                    env.ANSIBLE_TAGS = tagsList.join(',')
                    
                    if (env.ANSIBLE_TAGS != '') {
                        hasChanges = true
                    }
                    
                    echo "Deploy Decisions -> Auth: ${deployAuth}, Inference: ${deployInference}, Frontend: ${deployFrontend}"
                    echo "Ansible Tags: ${env.ANSIBLE_TAGS}"
                }
            }
        }

        stage('Build & Push Auth') {
            when { expression { return deployAuth } }
            steps {
                script {
                    docker.withRegistry('', DOCKER_CREDENTIALS_ID) {
                        // Context: mlops-llm4ts/model-service/auth-service/
                        def img = docker.build("${DOCKER_USER}/weather-auth:${IMAGE_TAG}", "-f mlops-llm4ts/model-service/auth-service/Dockerfile.auth mlops-llm4ts/model-service/auth-service/")
                        img.push()
                    }
                }
            }
        }

        stage('Build & Push Inference') {
            when { expression { return deployInference } }
            steps {
                script {
                    docker.withRegistry('', DOCKER_CREDENTIALS_ID) {
                        // Context: mlops-llm4ts/model-service/inference-service/
                        def img = docker.build("${DOCKER_USER}/weather-inference:${IMAGE_TAG}", "-f mlops-llm4ts/model-service/inference-service/Dockerfile.param mlops-llm4ts/model-service/inference-service/")
                        img.push()
                    }
                }
            }
        }

        stage('Build & Push Frontend') {
            when { expression { return deployFrontend } }
            steps {
                script {
                    docker.withRegistry('', DOCKER_CREDENTIALS_ID) {
                        def img = docker.build("${DOCKER_USER}/weather-frontend:${IMAGE_TAG}", "frontend-new/")
                        img.push()
                    }
                }
            }
        }
        
        stage('Deploy with Ansible') {
            when { expression { return hasChanges } }
            steps {
                // Execute Ansible Playbook from the root
                // We pass dynamic tags so Ansible deploys the version we just built
                sh "ansible-playbook ansible/deploy.yml --tags '${env.ANSIBLE_TAGS}' -e 'auth_tag=${IMAGE_TAG} inference_tag=${IMAGE_TAG} frontend_tag=${IMAGE_TAG}'"
            }
        }
    }
}
