from flask import Flask, request, render_template_string, session, redirect, url_for, flash
import sqlite3
import os
import hashlib
import psycopg2 as psg
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extras import RealDictCursor
import mysql.connector
import pymysql.cursors
from hashlib import sha256

app = Flask(__name__)
app.secret_key = os.urandom(24)


def get_db_connection():

    db_config = {
        'host': 'localhost',  # El servidor local de XAMPP
        'user': 'root',       # El usuario de MySQL
        'password': '',       # Tu contraseña (si no tienes una, déjala vacía)
        'database': 'prueba' # El nombre de la base de datos
    }
    conn = mysql.connector.connect(**db_config)

    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


@app.route('/')
def index():
    return 'Welcome to the Task Manager Application!'


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()

        print(password)
        if "' OR '" in password:
            query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
            user = conn.execute(query).fetchone()
        else:
            query = "SELECT * FROM users WHERE username = %s AND password = %s"
            hashed_password = hash_password(password)

            print(password)
            print(hashed_password)
          
            cur = conn.cursor(pymysql.cursors.DictCursor)
           
            cur.execute(query, (username, hashed_password))
            user = cur.fetchone()
            cur.close()
            #user = conn.execute(query, (username, hashed_password)).fetchone()

        print("Consulta SQL generada:", query)

        print (user)
        print(session)
        print(user[0])
        if user:
            session['user_id'] = user[0]
            session['role'] = user[3]
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid credentials!'
    return '''
        <form method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
        </form>
    '''


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM tasks WHERE user_id = %s", (user_id,))
    tasks = cur.fetchall() 
    cur.close()

    return render_template_string('''
        <h1>Welcome, user {{ user_id }}!</h1>
        <form action="/add_task" method="post">
            <input type="text" name="task" placeholder="New task"><br>
            <input type="submit" value="Add Task">
        </form>
        <h2>Your Tasks</h2>
        <ul>
        {% for task in tasks %}
            <li>{{ task['task'] }} <a href="/delete_task/{{ task['id'] }}">Delete</a></li>
        {% endfor %}
        </ul>
    ''', user_id=user_id, tasks=tasks)


@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    task = request.form['task']
    user_id = session['user_id']

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("INSERT INTO tasks (user_id, tasks) VALUES (%s, %s)", (user_id, task))
    tasks = cur.fetchall() 
    #result = cur.fetchall()   # o fetchone()
    conn.commit()
    cur.close()
    conn.close()


    return redirect(url_for('dashboard'))


@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    tasks = cur.fetchall() 
    #result = cur.fetchall()   # o fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    return 'Welcome to the admin panel!'


if __name__ == '__main__':
    app.run(debug=True)
