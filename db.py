import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",  # or your MySQL username
        password="@STHA980",  # your MySQL password
        database="lms"  # <-- Use your actual database name
    )