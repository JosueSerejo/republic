# database.py

import sqlite3
import os
import psycopg2 # Importa o driver PostgreSQL
import psycopg2.extras # Para acessar colunas como dicionários (DictCursor)
from flask import g, current_app

def get_db():
    """
    Obtém uma conexão com o banco de dados.
    Usa PostgreSQL em produção (se DATABASE_URL estiver definido) ou SQLite em desenvolvimento.
    """
    if 'db' not in g:
        db_url = current_app.config.get('DATABASE_URL')

        if db_url: # Ambiente de Produção (Render) - Usar PostgreSQL
            try:
                g.db = psycopg2.connect(db_url)
                # O cursor DictCursor permite acessar os resultados como dicionários (row['nome'])
                g.db.cursor_factory = psycopg2.extras.DictCursor
                print("Conectado ao PostgreSQL.")
            except Exception as e:
                print(f"Erro ao conectar ao PostgreSQL: {e}")
                # Em produção, um erro de DB é crítico, é melhor levantar a exceção
                raise ConnectionError(f"Não foi possível conectar ao banco de dados PostgreSQL: {e}")
        else: # Ambiente de Desenvolvimento (Local) - Usar SQLite
            os.makedirs(os.path.dirname(current_app.config['DATABASE']), exist_ok=True)
            g.db = sqlite3.connect(current_app.config['DATABASE'])
            g.db.row_factory = sqlite3.Row # Permite acessar colunas por nome
            print("Conectado ao SQLite.")
    return g.db

def close_db(e=None):
    """
    Fecha a conexão com o banco de dados no final da requisição.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()
        print("Conexão com o banco de dados fechada.")

def inicializar_banco():
    """
    Inicializa o esquema do banco de dados (tabelas e colunas).
    Adapta a sintaxe SQL para PostgreSQL ou SQLite.
    """
    db_url = current_app.config.get('DATABASE_URL')
    conn = None # Conexão local para a inicialização
    try:
        if db_url: # PostgreSQL
            conn = get_db() # Obtém a conexão com o PostgreSQL
            cursor = conn.cursor()
            print("Inicializando banco de dados PostgreSQL...")
            
            # Tabela usuarios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY, -- SERIAL para auto-incremento no PostgreSQL
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    senha TEXT NOT NULL,
                    telefone TEXT,
                    tipo_usuario TEXT,
                    solicitacao_exclusao INTEGER DEFAULT 0
                )
            ''')
            # Tabela imoveis
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS imoveis (
                    id SERIAL PRIMARY KEY,
                    endereco TEXT, bairro TEXT, numero TEXT, cep TEXT,
                    complemento TEXT, valor REAL, quartos INTEGER,
                    banheiros INTEGER, inclusos TEXT, outros TEXT,
                    descricao TEXT, imagem TEXT, tipo TEXT,
                    usuario_id INTEGER, ativo INTEGER DEFAULT 1,
                    latitude REAL, longitude REAL,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
                )
            ''')
            # Tabela click_counts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS click_counts (
                    id SERIAL PRIMARY KEY,
                    event_name TEXT NOT NULL UNIQUE,
                    count INTEGER DEFAULT 0
                )
            ''')
            # Garante que o evento 'contact_anunciante_click' existe na tabela click_counts (PostgreSQL)
            cursor.execute("""
                INSERT INTO click_counts (event_name, count) VALUES (%s, %s)
                ON CONFLICT (event_name) DO NOTHING;
            """, ('contact_anunciante_click', 0))

            print("Banco de dados PostgreSQL inicializado com sucesso.")

        else: # SQLite
            conn = get_db() # Obtém a conexão com o SQLite
            cursor = conn.cursor()
            print("Inicializando banco de dados SQLite...")

            # Tabela usuarios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    senha TEXT NOT NULL,
                    telefone TEXT,
                    tipo_usuario TEXT,
                    solicitacao_exclusao INTEGER DEFAULT 0
                )
            ''')
            # Tabela imoveis
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS imoveis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endereco TEXT, bairro TEXT, numero TEXT, cep TEXT,
                    complemento TEXT, valor REAL, quartos INTEGER,
                    banheiros INTEGER, inclusos TEXT, outros TEXT,
                    descricao TEXT, imagem TEXT, tipo TEXT,
                    usuario_id INTEGER, ativo INTEGER DEFAULT 1,
                    latitude REAL, longitude REAL,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                )
            ''')
            # Tabela click_counts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS click_counts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_name TEXT NOT NULL UNIQUE,
                    count INTEGER DEFAULT 0
                )
            ''')
            # Garante que o evento 'contact_anunciante_click' existe na tabela click_counts (SQLite)
            cursor.execute("INSERT OR IGNORE INTO click_counts (event_name, count) VALUES (?, ?)", ('contact_anunciante_click', 0))
            
            print("Banco de dados SQLite inicializado com sucesso.")
        
        conn.commit() # Confirma as mudanças no banco de dados
    except Exception as e:
        print(f"ERRO ao inicializar o banco de dados: {e}")
        if conn:
            try:
                conn.rollback() # Tenta reverter qualquer mudança em caso de erro
                print("Transação do banco de dados revertida.")
            except Exception as rb_e:
                print(f"Erro durante o rollback: {rb_e}")
        raise e # Re-levanta a exceção para que o problema seja visível
    finally:
        # Se a conexão foi aberta especificamente para a inicialização (não pela g), feche-a
        if conn and not db_url: # Se for SQLite, que não usa g.db persistente para inicialização
             close_db() # Usa a função de fechamento do contexto da aplicação para garantir que g.db seja limpo