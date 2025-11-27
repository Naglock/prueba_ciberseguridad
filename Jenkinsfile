pipeline {
    agent any // Usamos 'agent any' para evitar conflictos con el agente Docker que fallaba

    environment {
        PROJECT_NAME = "pipeline-test"
        SONARQUBE_URL = "http://sonarqube:9000"
        
        // ⭐️ CORRECCIÓN CRÍTICA: Usamos el alias interno para la conectividad DAST ⭐️
        TARGET_URL = "http://host.docker.internal:5000" 
        APP_PORT = 5000
        APP_IMAGE = "python-app:${env.BUILD_ID}"
        ZAP_VERSION = "2.15.0" // Versión de ZAP a descargar
    }

    stages { 

        // --- 1. PREPARACIÓN, INSTALACIÓN Y CONSTRUCCIÓN ---
        stage('Setup & Build') {
            steps {
                echo "Instalando utilidades y construyendo imagen..."
                sh '''
                    # 1. Instalar herramientas críticas (wget, unzip, python)
                    DEBIAN_FRONTEND=noninteractive apt update && \
                    DEBIAN_FRONTEND=noninteractive apt install -y wget unzip python3 python3-venv python3-pip

                    # 2. Crear entorno virtual y dependencias
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
                // 3. Construir la imagen Docker
                sh "docker build -t ${APP_IMAGE} ."
            }
        }
        
        // --- 2. INSTALAR ZAP CLI (Localmente - Solución al bloqueo de Docker Hub) ---
        stage('Install ZAP CLI') {
            steps {
                echo "Descargando e instalando ZAP Core (v${ZAP_VERSION})..."
                sh """
                    # 1. Descargar el binario Linux/Unix de ZAP
                    wget https://github.com/zaproxy/zaproxy/releases/download/v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz -O zap_core.tar.gz
                    
                    # 2. Limpieza preventiva y descompresión
                    rm -rf ZAP_CLI || true
                    rm -rf ZAP_${ZAP_VERSION} || true
                    tar -xzf zap_core.tar.gz
                    
                    # 3. Renombrado y permisos
                    mv ZAP_${ZAP_VERSION} ZAP_CLI 
                    rm zap_core.tar.gz
                    chmod +x ZAP_CLI/zap.sh
                """
            }
        }

        // --- 3. ANÁLISIS DE DEPENDENCIAS (SCA) ---
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
                
                // 2. Ejecutar plugin OWASP Dependency-Check (usando credencial nvdApiKey)
                withCredentials([string(credentialsId: 'nvdApiKey', variable: 'NVD_API_KEY_SECRET')]) {
                    dependencyCheck additionalArguments: "--scan . --format HTML --out security-reports --enableExperimental --enableRetired --nvdApiKey ${NVD_API_KEY_SECRET} --disableOssIndex", odcInstallation: 'DependencyCheck'
                }
            }
        }
        
        // --- 4. ANÁLISIS ESTÁTICO DE CÓDIGO (SAST) ---
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
                                    -Dsonar.login=$SONAR_LOGIN_SECRET 
                            """
                        }
                    }
                }
            }
        }
        
        // --- 5. DESPLIEGUE TEMPORAL PARA DAST ---
        stage('Deploy for DAST') {
            steps {
                echo "Limpiando contenedores antiguos antes de desplegar..."
                sh 'docker stop deployed-app || true'
                sh 'docker rm deployed-app || true'
                
                echo "Desplegando la app en el puerto ${APP_PORT} para escaneo DAST..."
                sh "docker run -d --name deployed-app -p ${APP_PORT}:5000 --network jenkins-net ${APP_IMAGE}"
                sleep 10 // Dar tiempo al servidor Python para iniciar
            }
        }

        // --- 6. PRUEBAS DINÁMICAS (DAST con OWASP ZAP) ---
        stage('OWASP ZAP Scan (DAST)') {
            steps {
                echo "Ejecutando escaneo ZAP Baseline (Localmente) contra ${TARGET_URL}"
                sh """
                    ./ZAP_CLI/zap.sh -cmd -port 8090 -host 127.0.0.1 -quickurl ${TARGET_URL} -quickout security-reports/zap-report.html || true
                """
                sh 'chmod -R 777 security-reports'
            }
        }

        // --- 7. LIMPIEZA Y PUBLICACIÓN DE INFORMES ---
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
    } // Cierra el bloque stages
} // Cierra el bloque pipeline