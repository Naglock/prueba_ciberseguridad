pipeline {
    agent {
        // Usar una imagen Docker con Python ya instalado para el agente
        // Esto evita errores de 'apt install' y garantiza la consistencia del ambiente.
        docker {
            image 'python:3.12-slim'
        }
    }

    environment {
        PROJECT_NAME = "pipeline-test"
        SONARQUBE_URL = "http://sonarqube:9000"
        TARGET_URL = "http://172.31.150.232:5000" // IP de la aplicación una vez desplegada (Verifica que esta IP de WSL siga activa)
        APP_PORT = 5000
        APP_IMAGE = "python-app:${env.BUILD_ID}"
    }

    stages {
        // --- 1. PREPARACIÓN Y CONSTRUCCIÓN ---
        stage('Setup & Build') {
            steps {
                echo "Instalando dependencias y construyendo imagen..."
                sh '''
                    # Crear entorno virtual
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
                // Construir la imagen Docker de la aplicación para el despliegue
                sh "docker build -t ${APP_IMAGE} ."
            }
        }
        
        // --- 2. ANÁLISIS DE DEPENDENCIAS (SCA) ---
        stage('Dependency Check (SCA)') {
            steps {
                echo "Ejecutando escaneo de vulnerabilidades en dependencias..."
                
                // 1. Instalar pip-audit y generar informe Markdown
                sh '''
                    . venv/bin/activate
                    pip install pip-audit
                    mkdir -p security-reports
                    pip-audit -r requirements.txt -f markdown -o security-reports/pip-audit.md || true
                '''
                
                // 2. Ejecutar plugin OWASP Dependency-Check usando la credencial 'nvdApiKey'
                withCredentials([string(credentialsId: 'nvdApiKey', variable: 'NVD_API_KEY_SECRET')]) {
                    dependencyCheck additionalArguments: "--scan . --format HTML --out security-reports --enableExperimental --enableRetired --nvdApiKey ${NVD_API_KEY_SECRET}", odcInstallation: 'DependencyCheck'
                }
            }
        }
        
        // --- 3. ANÁLISIS ESTÁTICO DE CÓDIGO (SAST) ---
        stage('SonarQube Analysis (SAST)') {
            steps {
                // 1. Usar la credencial 'sonarQubeToken' para inyectar el secreto
                withCredentials([string(credentialsId: 'sonarQubeToken', variable: 'SONAR_LOGIN_SECRET')]) { 
                    script {
                        def scannerHome = tool 'SonarQubeScanner'
                        withSonarQubeEnv('SonarQubeScanner') {
                            sh """
                                ${scannerHome}/bin/sonar-scanner \\
                                    -Dsonar.projectKey=$PROJECT_NAME \\
                                    -Dsonar.sources=. \\
                                    -Dsonar.host.url=$SONARQUBE_URL \\
                                    -Dsonar.login=$SONAR_LOGIN_SECRET  // Usa la variable secreta inyectada
                            """
                        }
                    }
                }
            }
        }
        
        // --- 4. DESPLIEGUE TEMPORAL PARA DAST ---
        stage('Deploy for DAST') {
            steps {
                echo "Desplegando la app en el puerto ${APP_PORT} para escaneo DAST..."
                // Desplegar la app usando la imagen construida. La app y Jenkins están en la misma red.
                sh "docker run -d --name deployed-app -p ${APP_PORT}:5000 --network jenkins-net ${APP_IMAGE}"
                sleep 10 // Dar tiempo al servidor Python para iniciar
            }
        }

        // --- 5. PRUEBAS DINÁMICAS (DAST con OWASP ZAP) ---
        stage('OWASP ZAP Scan (DAST)') {
            steps {
                echo "Ejecutando escaneo ZAP Baseline contra ${TARGET_URL}"
                // ZAP escanea la aplicación desplegada en el host/WSL a través de la IP 172.31.150.232
                sh """
                    docker run --rm \\
                    -v \$(pwd)/security-reports:/zap/wrk \\
                    owasp/zap2docker-stable \\
                    zap-baseline.py -t ${TARGET_URL} \\
                    -g /zap/wrk/zap-report.html -r /zap/wrk/zap-report.xml || true
                """
            }
        }

        // --- 6. LIMPIEZA Y PUBLICACIÓN DE INFORMES ---
        stage('Cleanup & Publish Reports') {
            steps {
                echo "Deteniendo y eliminando contenedor temporal..."
                sh 'docker stop deployed-app || true'
                sh 'docker rm deployed-app || true'

                echo "Publicando informes..."
                // Publicar informe de Dependency Check
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'security-reports',
                    reportFiles: 'dependency-check-report.html',
                    reportName: 'OWASP Dependency Check Report'
                ])
                // Publicar informe de ZAP
                publishHTML([
                    allowMissing: true,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'security-reports',
                    reportFiles: 'zap-report.html',
                    reportName: 'OWASP ZAP DAST Report'
                ])
            }
        }
    }
}