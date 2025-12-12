pipeline {
    agent any

    environment {
        // Credentials ID as configured in Jenkins
        DOCKER_CREDENTIALS_ID = 'docker-hub-credentials'
        DOCKER_USER = 'kondapallitarun3474'
        
        // Dynamic Image Tag
        IMAGE_TAG = "v${env.BUILD_NUMBER}"
        
        // Deployment Flags (will be set by Change Detection)
        DEPLOY_AUTH = 'false'
        DEPLOY_INFERENCE = 'false'
        DEPLOY_FRONTEND = 'false'
        
        // Tags to pass to Ansible
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
                    // Check diff between HEAD and previous commit
                    // If this is the first run/no history, this might fail, so wrap in try/catch or use a safer command
                    // For typical Push events, HEAD~1 works.
                    def changes = ""
                    try {
                        changes = sh(script: 'git diff --name-only HEAD~1 HEAD', returnStdout: true).trim()
                    } catch (Exception e) {
                        echo "Could not diff against HEAD~1 (first commit?). Assuming everything changed."
                        changes = "mlops-llm4ts/model-service/auth-service/ mlops-llm4ts/model-service/inference-service/ frontend-new/"
                    }

                    def tagsList = []
                    
                    echo "Changed files:\n${changes}"

                    def changedFiles = changes.split('\n')
                    
                    for (file in changedFiles) {
                        // Trim whitespace just in case
                        file = file.trim()

                        if (file.contains('mlops-llm4ts/model-service/auth-service/')) {
                            env.DEPLOY_AUTH = 'true'
                            if (!tagsList.contains('auth')) tagsList.add('auth')
                        }
                        if (file.contains('mlops-llm4ts/model-service/inference-service/')) {
                            env.DEPLOY_INFERENCE = 'true'
                            if (!tagsList.contains('inference')) tagsList.add('inference')
                        }
                        if (file.contains('frontend-new/')) {
                            env.DEPLOY_FRONTEND = 'true'
                            if (!tagsList.contains('frontend')) tagsList.add('frontend')
                        }
                    }
                    
                    env.ANSIBLE_TAGS = tagsList.join(',')
                    
                    echo "Flags -> Auth: ${env.DEPLOY_AUTH}, Inference: ${env.DEPLOY_INFERENCE}, Frontend: ${env.DEPLOY_FRONTEND}"
                    echo "Ansible Tags: ${env.ANSIBLE_TAGS}"
                }
            }
        }

        stage('Build & Push Auth') {
            when { expression { return env.DEPLOY_AUTH == 'true' } }
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
            when { expression { return env.DEPLOY_INFERENCE == 'true' } }
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
            when { expression { return env.DEPLOY_FRONTEND == 'true' } }
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
            when { expression { return env.ANSIBLE_TAGS != '' } }
            steps {
                // Execute Ansible Playbook from the root
                // We pass dynamic tags so Ansible deploys the version we just built
                sh "ansible-playbook ansible/deploy.yml --tags '${env.ANSIBLE_TAGS}' -e 'auth_tag=${IMAGE_TAG} inference_tag=${IMAGE_TAG} frontend_tag=${IMAGE_TAG}'"
            }
        }
    }
}
