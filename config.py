# config.py

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sua_chave_secreta_muito_segura'
    UPLOAD_FOLDER = os.path.join('static', 'img', 'imoveis')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Configurações para Envio de E-mail com SendGrid (se você estiver usando)
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'seu_email_verificado_sendgrid@exemplo.com'
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY') or 'SUA_CHAVE_API_SENDGRID_AQUI'

    # --- Configurações de Banco de Dados ---
    # DATABASE_URL será definida no Render para produção (PostgreSQL)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    # DATABASE é o caminho local para o SQLite (apenas para desenvolvimento)
    DATABASE = 'instance/banco.db'