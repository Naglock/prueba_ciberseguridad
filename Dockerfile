# Usa una imagen base con Python 3.12 (consistente con lo que Jenkins intentó usar)
FROM python:3.12-slim 

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia e instala las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código fuente (vulnerable_app.py y otros)
# Nota: La aplicación vulnerable es 'vulnerable_app.py' en tu lista
COPY . .

# Expone el puerto que usa Flask (puerto 5000 por defecto)
EXPOSE 5000

# Comando para ejecutar la aplicación al iniciar el contenedor
CMD ["python3", "vulnerable_app.py"]