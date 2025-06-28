import os
import mysql.connector
from dotenv import load_dotenv

# Indlæs miljøvariabler fra .env-filen
load_dotenv()

def setup_database():
    print("Starter database setup...")
    
    # Opret forbindelse til MySQL
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD')
    )
    
    cursor = conn.cursor()
    
    # Opret database hvis den ikke findes
    db_name = os.getenv('MYSQL_DB')
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    cursor.execute(f"USE {db_name}")
    
    print(f"Database '{db_name}' er klar til brug")
    
    # Læs SQL-fil og kør kommandoerne
    try:
        with open('database_schema.sql', 'r', encoding='utf-8') as sql_file:
            sql_script = sql_file.read()
            
        # Split SQL-scriptet ved semikolon for at få de enkelte kommandoer
        sql_commands = sql_script.split(';')
        
        for command in sql_commands:
            if command.strip():  # Ignorer tomme kommandoer
                cursor.execute(command)
                conn.commit()
        
        print("Database tabeller og initial data er oprettet")
        
    except Exception as e:
        print(f"Fejl ved oprettelse af database skema: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup_database()