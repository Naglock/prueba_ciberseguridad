pipeline {
    agent any // Usamos 'agent any' para avanzar después de los errores de Docker

    // ⭐️ AÑADIMOS EL BLOQUE ENVIRONMENT AQUÍ ⭐️
    environment {
        PROJECT_NAME = "pipeline-test"
        SONARQUBE_URL = "http://sonarqube:9000"
        TARGET_URL = "http://172.31.150.232:5000" // IP de la aplicación una vez desplegada
        APP_PORT = 5000
        APP_IMAGE = "python-app:${env.BUILD_ID}"
    }
    // ⭐️ AÑADIMOS EL BLOQUE STAGES AQUÍ ⭐️
    stages { 

        // --- 1. PREPARACIÓN Y CONSTRUCCIÓN ---
        stage('Setup & Build') {
            steps {
                echo "Instalando dependencias y construyendo imagen..."
                sh '''
                    # 1. Instalar Python y herramientas necesarias
                    DEBIAN_FRONTEND=noninteractive apt install -y python3 python3-venv python3-pip

                    # 2. Crear entorno virtual dentro del workspace
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
                // 3. Construir la imagen Docker de la aplicación para el despliegue
                sh "docker build -t ${APP_IMAGE} ."
            }
        }
        stage('Install ZAP CLI') {
        steps {
            echo "Descargando e instalando ZAP CLI..."
            sh '''
                # ZAP CLI es un binario que podemos descargar directamente
                # Usaremos la versión más reciente (ej. 2.15.0)
                wget https://github.com/zaproxy/zaproxy/releases/download/v2.15.0/ZAP_CLI-2.15.0.zip -O zap_cli.zip
                unzip zap_cli.zip
                chmod +x ZAP_CLI/zap.sh
            '''
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
                    dependencyCheck additionalArguments: "--scan . --format HTML --out security-reports --enableExperimental --enableRetired --nvdApiKey ${NVD_API_KEY_SECRET} --disableOssIndex", odcInstallation: 'DependencyCheck' // ⭐️ AÑADIDO: --disableOssIndex
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
                                    -Dsonar.login=$SONAR_LOGIN_SECRET 
                            """
                        }
                    }
                }
            }
        }
        
        // --- 4. DESPLIEGUE TEMPORAL PARA DAST ---
        stage('Deploy for DAST') {
            steps {
                echo "Limpiando contenedores antiguos antes de desplegar..."
                // ⭐️ AÑADIR LIMPIEZA PREVIA AQUÍ ⭐️
                sh 'docker stop deployed-app || true'
                sh 'docker rm deployed-app || true'
                echo "Desplegando la app en el puerto ${APP_PORT} para escaneo DAST..."
                // Desplegar la app usando la imagen construida. La app y Jenkins están en la misma red.
                sh "docker run -d --name deployed-app -p ${APP_PORT}:5000 --network jenkins-net ${APP_IMAGE}"
                sleep 10 // Dar tiempo al servidor Python para iniciar
            }
        }

        // --- 5. PRUEBAS DINÁMICAS (DAST con OWASP ZAP) ---
        stage('OWASP ZAP Scan (DAST)') {
            steps {
                echo "Ejecutando escaneo ZAP Baseline (Localmente) contra ${TARGET_URL}"
                sh """
                    # Ejecutar el binario local ZAP CLI
                    ./ZAP_CLI/zap.sh -cmd -host ${TARGET_URL} -port 8080 -addonupdate -baseline -g /zap/zap-report.html || true
                    
                    # Nota: Esto es un ejemplo, el comando exacto de ZAP CLI para generar el informe HTML puede variar.
                    # Aquí generamos un informe simple para la publicación.
                    
                    # Mover el informe generado al directorio de informes de Jenkins
                    mv zap-report.html security-reports/zap-report.html
                """
                sh 'chmod -R 777 security-reports'
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
    } // ⭐️ CIERRA EL BLOQUE STAGES AQUÍ ⭐️
} // CIERRA EL BLOQUE PIPELINE