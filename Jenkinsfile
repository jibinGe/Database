pipeline {
    agent any
    stages {
        stage('Build') {
            parallel {
                stage('Building...') {
                    steps {
                        sh 'echo "building the repo"'
                    }
                }
            }
        }
        stage('Copy Files') {
            steps {
                echo "Copying app.py folder to another directory"
                sh 'sudo rm -r /home/ubuntu/genesys/genesys/genesys_db/app.py'
                sh 'sudo cp /var/lib/jenkins/workspace/Flask-Database_main/app.py /home/ubuntu/genesys/genesys/genesys_db'
            }
        }
        stage('Deploy') {
            steps {
                echo "deploying the application"
                sh 'sudo systemctl restart db.service'
            }
        }
    }
    post {
        always {
            echo 'The pipeline completed'
            junit allowEmptyResults: true, testResults: '**/test_reports/*.xml'
        }
        success {
            echo "Flask Application Up and running!!"
        }
        failure {
            echo 'Build stage failed'
            error('Stopping early…')
        }
    }
}
