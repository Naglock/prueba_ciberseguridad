pipeline {
    agent {
        // Usar una imagen Docker con Python ya instalado para el agente
        docker {
            image 'python:3.12-slim'
        }
    }

    environment {
        PROJECT_NAME = "pipeline-test"
        SONARQUBE_URL = "http://sonarqube:9000"
        SONARQUBE_TOKEN = credentials('sqa_0833044ad0b0a6645c6f7651ed7d49b7d15302fb') // USAR ID de credencial en Jenkins
        TARGET_URL = "http://172.31.150.232:5000" // IP de la aplicación una vez desplegada
        APP_PORT = 5000
        APP_IMAGE = "python-app:${env.BUILD_ID}"
    }

    stages {
        // --- 1. PREPARACIÓN Y CONSTRUCCIÓN ---
        stage('Setup & Build') {
            steps {
                echo "Instalando dependencias y construyendo imagen..."
                sh '''
                    # Crear entorno virtual dentro del workspace
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
                // **Usamos pip-audit** para escanear las dependencias instaladas
                sh '''
                    . venv/bin/activate
                    pip install pip-audit
                    mkdir -p security-reports
                    pip-audit -r requirements.txt -f markdown -o security-reports/pip-audit.md || true
                '''
                // **Usamos el plugin de OWASP Dependency Check** (Revisar si es necesario ejecutar pip-audit también)
                dependencyCheck additionalArguments: "--scan . --format HTML --out security-reports --enableExperimental --enableRetired --nvdApiKey ${NVD_API_KEY}", odcInstallation: 'DependencyCheck'
            }
        }
        
        // --- 3. ANÁLISIS ESTÁTICO DE CÓDIGO (SAST) ---
        stage('SonarQube Analysis (SAST)') {
            steps {
                script {
                    def scannerHome = tool 'SonarQubeScanner'
                    withSonarQubeEnv('SonarQubeScanner') {
                        sh """
                            ${scannerHome}/bin/sonar-scanner \\
                                -Dsonar.projectKey=$PROJECT_NAME \\
                                -Dsonar.sources=. \\
                                -Dsonar.host.url=$SONARQUBE_URL \\
                                -Dsonar.login=$SONARQUBE_TOKEN
                        """
                    }
                }
            }
        }
        
        // --- 4. DESPLIEGUE TEMPORAL PARA DAST ---
        stage('Deploy for DAST') {
            steps {
                echo "Desplegando la app en el puerto ${APP_PORT} para escaneo DAST..."
                // Desplegar la app usando la imagen construida. 
                // Usar --network jenkins-net si ZAP corre en esa red.
                sh "docker run -d --name deployed-app -p ${APP_PORT}:5000 --network jenkins-net ${APP_IMAGE}"
                sleep 10 // Esperar a que el servidor Flask/Python inicie
            }
        }

        // --- 5. PRUEBAS DINÁMICAS (DAST con OWASP ZAP) ---
        stage('OWASP ZAP Scan (DAST)') {
            steps {
                echo "Ejecutando escaneo ZAP Baseline contra ${TARGET_URL}"
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