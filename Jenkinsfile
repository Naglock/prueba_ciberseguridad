pipeline {
    agent any // Usamos 'agent any' para avanzar después de los errores de Docker

    environment {
        PROJECT_NAME = "pipeline-test"
        SONARQUBE_URL = "http://sonarqube:9000"
        TARGET_URL = "http://172.31.150.232:5000" // IP de la aplicación una vez desplegada
        APP_PORT = 5000
        APP_IMAGE = "python-app:${env.BUILD_ID}"
        ZAP_VERSION = "2.15.0" // Definimos la versión de ZAP para simplificar
    }

    stages { 

        // --- 1. PREPARACIÓN, INSTALACIÓN Y CONSTRUCCIÓN ---
        stage('Setup & Build') {
            steps {
                echo "Instalando utilidades y construyendo imagen..."
                sh '''
                    # 1. Instalar herramientas críticas (wget, unzip) y Python
                    DEBIAN_FRONTEND=noninteractive apt update && \
                    DEBIAN_FRONTEND=noninteractive apt install -y wget unzip python3 python3-venv python3-pip

                    # 2. Crear entorno virtual
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
                // 3. Construir la imagen Docker de la aplicación para el despliegue
                sh "docker build -t ${APP_IMAGE} ."
            }
        }
        
        // --- 2. INSTALAR ZAP CLI (Solución al Bloqueo de Docker Hub) ---
        stage('Install ZAP CLI') {
            steps {
                echo "Descargando e instalando ZAP Core (v${ZAP_VERSION})..."
                sh """
                    # ⭐️ CAMBIO CRÍTICO: Descargar ZAP Core (.tar.gz) ⭐️
                    wget https://github.com/zaproxy/zaproxy/releases/download/v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz -O zap_core.tar.gz
                    
                    # Descomprime el archivo (tar.gz)
                    tar -xzf zap_core.tar.gz
                    
                    # Renombra el directorio para que coincida con la ruta de ejecución
                    mv ZAP* ZAP_CLI
                    
                    # Limpieza y Permisos
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
                
                // 2. Ejecutar plugin OWASP Dependency-Check
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
        stage('OWASP ZAP Scan (DAST)') {
            steps {
                echo "Ejecutando escaneo ZAP Baseline (Localmente) contra ${TARGET_URL}"
                sh """
                    # ⭐️ COMANDO ÚNICO CORREGIDO: INCLUYE PUERTO Y REPORTE ⭐️
                    ./ZAP_CLI/zap.sh -cmd \\
                        -port 8090 \\  // ⭐️ Solución 1: Evita conflicto con Jenkins ⭐️
                        -target ${TARGET_URL} \\
                        -quickscan \\
                        -quickout security-reports/zap-report.html || true  // ⭐️ Solución 2: Genera el HTML directamente ⭐️
                """
                // ⭐️ ELIMINAMOS el código del reporte que fallaba ⭐️
                // El comando de mv y chmod debe estar fuera del bloque sh anterior.
                sh 'chmod -R 777 security-reports'
            }
        }

        // --- 6. PRUEBAS DINÁMICAS (DAST con OWASP ZAP) ---
        stage('OWASP ZAP Scan (DAST)') {
            steps {
                echo "Ejecutando escaneo ZAP Baseline (Localmente) contra ${TARGET_URL}"
                sh """
                    # Ejecutar el binario local ZAP CLI y generar el informe
                    ./ZAP_CLI/zap.sh -cmd -target ${TARGET_URL} -T 30 -quickscan -addoninstall pscanrules -addonupdate || true
                    
                    # Generar el informe HTML (comando específico de ZAP CLI)
                    ./ZAP_CLI/zap.sh -cmd -report -format html -template traditional -output zap-report-raw.html || true
                    
                    # Mover el informe generado al directorio de informes de Jenkins
                    mv zap-report-raw.html security-reports/zap-report.html
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
    } // CIERRA EL BLOQUE STAGES AQUÍ ⭐️
} // CIERRA EL BLOQUE PIPELINE