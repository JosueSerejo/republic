# adicionar_tabela_tokens.py
import sqlite3
import os
from app import Config # Assumindo que Config está acessível de app.py

DATABASE = Config.DATABASE # Para SQLite
# Se você for usar PostgreSQL, DATABASE_URL virá das variáveis de ambiente
DB_URL = os.environ.get('DATABASE_URL')

def adicionar_tabela_tokens():
    conn = None
    try:
        if DB_URL: # PostgreSQL
            import psycopg2
            conn = psycopg2.connect(DB_URL)
            cursor = conn.cursor()
            print("Conectado ao PostgreSQL para adicionar tabela 'tokens'.")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    expiration TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE
                )
            ''')
            print("Tabela 'tokens' criada no PostgreSQL.")
        else: # SQLite
            os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            print("Conectado ao SQLite para adicionar tabela 'tokens'.")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    expiration DATETIME NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE
                )
            ''')
            print("Tabela 'tokens' criada no SQLite.")

        conn.commit()
    except Exception as e:
        print(f"Erro ao adicionar tabela 'tokens': {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    adicionar_tabela_tokens()