import os
import mysql.connector
from dotenv import load_dotenv

def setup_database():
    """
    Opretter databasen og kører SQL-scriptet for at oprette tabeller og indsætte startdata.
    """
    # Indlæs miljøvariabler fra .env-filen
    load_dotenv()
    
    mysql_host = os.getenv('MYSQL_HOST')
    mysql_user = os.getenv('MYSQL_USER')
    mysql_password = os.getenv('MYSQL_PASSWORD')
    mysql_db = os.getenv('MYSQL_DB')
    
    # Forbind til MySQL-server (uden database først)
    conn = mysql.connector.connect(
        host=mysql_host,
        user=mysql_user,
        password=mysql_password
    )
    
    cursor = conn.cursor()
    
    try:
        # Forsøg at oprette databasen, hvis den ikke allerede findes
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {mysql_db}")
        cursor.execute(f"USE {mysql_db}")
        
        print(f"Database '{mysql_db}' er oprettet eller eksisterer allerede.")
        
        # Læs SQL-scriptet
        with open('database_setup.sql', 'r') as f:
            sql_commands = f.read()
        
        # Split scriptet ved semikolon og kør hver kommando
        for command in sql_commands.split(';'):
            if command.strip():
                cursor.execute(command)
                conn.commit()
        
        print("Database tabeller og startdata er blevet oprettet.")
    
    except mysql.connector.Error as err:
        print(f"Fejl ved oprettelse af database: {err}")
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup_database()