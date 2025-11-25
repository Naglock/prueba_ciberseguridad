import sqlite3
import hashlib
#import psycopg2 as psg
import pandas as pd
#import xlwings as xw
from openpyxl import load_workbook
from  pandas import ExcelWriter
#import psycopg2

#pip install mysql-connector-python
import mysql.connector

from hashlib import sha256

def hash_password(password):
    return sha256(password.encode()).hexdigest()

#conn = psg.connect(dbname = 'postgres', 
#                        user = 'postgres', 
#                        password = 'Martin2010',
#                        host= 'localhost',
#                        port = 5432)

db_config = {
    'host': 'localhost',  # El servidor local de XAMPP
    'user': 'root',       # El usuario de MySQL
    'password': '',       # Tu contraseña (si no tienes una, déjala vacía)
    'database': 'prueba' # El nombre de la base de datos
}

conn = mysql.connector.connect(**db_config)

c = conn.cursor()

c.execute('''
    CREATE TABLE users (
        id INT NOT NULL AUTO_INCREMENT,
        username varchar(20),
        password varchar(256),
        role varchar(20),
        PRIMARY KEY (id)
    );
''')

c.execute('''
    INSERT INTO users (username, password, role) VALUES
    (%s, %s, %s),
    (%s, %s, %s)
''', ('admin', hash_password('password'), 'admin',
      'user', hash_password('password'), 'user'))


c.execute('''
    CREATE TABLE tasks (
    id INT NOT NULL AUTO_INCREMENT,
    tasks  VARCHAR(100),
    user_id INT,      
    PRIMARY KEY (id)  
);
''')

c.execute('''
    INSERT INTO tasks (tasks,user_id) VALUES
    (%s,%s),
    (%s,%s)
''', ('correr',1,
      'saltar',2))


conn.commit()
c.close()
conn.close()