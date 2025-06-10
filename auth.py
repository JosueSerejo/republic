# auth.py

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, g, flash, current_app # Adicionado current_app
import sqlite3 # Importado para capturar sqlite3.IntegrityError e sqlite3.Error
import uuid # Adicionado para gerar tokens únicos
from datetime import datetime, timedelta # Adicionado para controlar a expiração do token
import psycopg2 # Importado para capturar psycopg2.IntegrityError e psycopg2.Error
import psycopg2.extras # Importado para usar DictCursor com PostgreSQL

# NOVO: Imports para SendGrid
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

from database import get_db # Importa a função get_db do novo módulo

# Cria um Blueprint para as rotas de autenticação
bp = Blueprint('auth', __name__, url_prefix='/')

# --- Funções de Ajuda ---

# Função para envio de e-mail com SendGrid
def enviar_email_reset_senha(user_email, reset_link):
    try:
        sg = sendgrid.SendGridAPIClient(current_app.config['SENDGRID_API_KEY'])
        from_email = Email(current_app.config['MAIL_DEFAULT_SENDER'])
        to_email = To(user_email)
        subject = "Redefinição de Senha para Republic"
        
        # Conteúdo do e-mail em HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Redefinição de Senha</title>
        </head>
        <body>
            <p>Olá,</p>
            <p>Recebemos uma solicitação para redefinir a senha da sua conta na Republic.</p>
            <p>Clique no link abaixo para prosseguir com a redefinição:</p>
            <p><a href="{reset_link}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 5px;">Redefinir Senha Agora</a></p>
            <p>Este link é válido por 1 hora.</p>
            <p>Se você não solicitou esta redefinição, por favor, ignore este e-mail.</p>
            <p>Obrigado,<br>A equipe Republic</p>
        </body>
        </html>
        """
        content = Content("text/html", html_content)
        
        message = Mail(from_email, to_email, subject, html_content=html_content)
        
        response = sg.client.mail.send.post(request_body=message.get())
        
        print(f"E-mail de redefinição enviado para {user_email}. Status Code: {response.status_code}")
        print(response.body) # Pode ser útil para depuração
        print(response.headers) # Pode ser útil para depuração
        
        if response.status_code >= 200 and response.status_code < 300:
            return True
        else:
            return False # Indicar falha
    except Exception as e:
        print(f"Erro ao enviar e-mail de redefinição: {e}")
        return False # Indicar falha

# ----- DECORATOR LOGIN -----

def login_required(f):
    """
    Decorador que verifica se o usuário está logado.
    Se não estiver logado, redireciona para a página de login.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'info')
            # Redireciona para a rota de login do blueprint
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapped

# ----- CONTEXTO GLOBAL -----

@bp.context_processor
def inject_usuario():
    """
    Injeta informações do usuário logado em todos os templates.
    """
    usuario_nome = tipo_usuario = None
    user_id = session.get('usuario_id')
    if user_id:
        db = get_db()
        # NOVO: Crie um cursor a partir da conexão para PostgreSQL (com DictCursor) ou use a conexão direta para SQLite
        if current_app.config.get('DATABASE_URL'):
            cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else: # Para SQLite
            cur = db # A conexão SQLite tem execute() diretamente ou age como um cursor

        param_placeholder = "%s" if current_app.config.get('DATABASE_URL') else "?"
        
        cur.execute( # Use cur.execute
            f'SELECT nome, tipo_usuario FROM usuarios WHERE id = {param_placeholder}', (user_id,)
        )
        row = cur.fetchone()
        if row:
            usuario_nome = row['nome']
            tipo_usuario = row['tipo_usuario']
    return dict(usuario_nome=usuario_nome, tipo_usuario=tipo_usuario)

# ----- ROTAS DE AUTENTICAÇÃO E CADASTRO -----

@bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """
    Rota para cadastro de novos usuários.
    Permite GET para exibir o formulário e POST para processar o cadastro.
    """
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha'] # Senha não está hashada, considerar hashing para segurança real
        telefone = request.form['telefone']
        tipo_usuario = request.form['tipo_usuario']
        db = get_db()
        # NOVO: Crie um cursor a partir da conexão (sem DictCursor para INSERT)
        if current_app.config.get('DATABASE_URL'):
            cur = db.cursor() 
        else:
            cur = db
        
        param_placeholder = "%s" if current_app.config.get('DATABASE_URL') else "?"
        try:
            cur.execute( # Use cur.execute
                f'INSERT INTO usuarios (nome, email, senha, telefone, tipo_usuario) VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder})',
                (nome, email, senha, telefone, tipo_usuario)
            )
            db.commit()
            flash('Cadastro realizado com sucesso! Faça login para continuar.', 'success')
            # Redireciona para a página de login após o cadastro
            return redirect(url_for('auth.login'))
        except (sqlite3.IntegrityError, psycopg2.IntegrityError) as e: # Captura erros de integridade de ambos os bancos
            flash('Email já cadastrado. Tente outro email ou faça login.', 'danger')
            db.rollback() # Reverte a transação em caso de erro de integridade
        except Exception as e: # Captura outros erros de banco de dados
            flash(f'Ocorreu um erro no cadastro: {e}', 'danger')
            print(f"Erro ao cadastrar usuário: {e}") # Log para depuração
            db.rollback() # Reverte a transação em caso de outros erros
    return render_template('cadastro.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Rota para login de usuários existentes.
    Permite GET para exibir o formulário e POST para processar o login.
    """
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        db = get_db()
        # NOVO: Crie um cursor a partir da conexão (com DictCursor para SELECT)
        if current_app.config.get('DATABASE_URL'):
            cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else:
            cur = db

        param_placeholder = "%s" if current_app.config.get('DATABASE_URL') else "?"
        cur.execute( # Use cur.execute
            f'SELECT id FROM usuarios WHERE email = {param_placeholder} AND senha = {param_placeholder}', (
                email, senha)
        )
        user = cur.fetchone()
        if user:
            session['usuario_id'] = user['id']
            flash('Login realizado com sucesso!', 'success')
            # Redireciona para a página inicial
            return redirect(url_for('index'))
        flash('Email ou senha inválidos!', 'danger')
    return render_template('cadastro.html')

@bp.route('/logout')
@login_required
def logout():
    """
    Rota para deslogar o usuário.
    Remove o ID do usuário da sessão.
    """
    session.pop('usuario_id', None)
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    db = get_db()
    user_id = session['usuario_id']
    # NOVO: Crie um cursor a partir da conexão (com DictCursor para SELECT)
    if current_app.config.get('DATABASE_URL'):
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    else:
        cur = db

    param_placeholder = "%s" if current_app.config.get('DATABASE_URL') else "?"

    if request.method == 'POST':
        # Processa a atualização de dados
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha'] # Note: Senha não está hashada, considerar hashing para segurança real
        telefone = request.form['telefone']
        
        try:
            cur.execute( # Use cur.execute
                f'UPDATE usuarios SET nome = {param_placeholder}, email = {param_placeholder}, senha = {param_placeholder}, telefone = {param_placeholder} WHERE id = {param_placeholder}',
                (nome, email, senha, telefone, user_id)
            )
            db.commit()
            flash('Suas informações foram atualizadas com sucesso!', 'success')
            return redirect(url_for('auth.perfil'))
        except (sqlite3.IntegrityError, psycopg2.IntegrityError) as e:
            flash('Este email já está cadastrado para outro usuário.', 'danger')
            db.rollback()
        except Exception as e:
            flash(f'Ocorreu um erro ao atualizar: {e}', 'danger')
            print(f"Erro ao atualizar perfil: {e}") # Log para depuração
            db.rollback()

    # Busca os dados atuais do usuário para exibir no formulário
    cur.execute( # Use cur.execute
        f'SELECT id, nome, email, telefone, tipo_usuario, solicitacao_exclusao FROM usuarios WHERE id = {param_placeholder}',
        (user_id,)
    )
    user = cur.fetchone()

    if not user:
        flash('Usuário não encontrado.', 'danger')
        # Redireciona se o usuário sumir
        return redirect(url_for('auth.login'))

    return render_template('perfil.html', user=user)

@bp.route('/solicitar_exclusao', methods=['POST'])
@login_required
def solicitar_exclusao():
    db = get_db()
    user_id = session['usuario_id']
    # NOVO: Crie um cursor a partir da conexão
    if current_app.config.get('DATABASE_URL'):
        cur = db.cursor()
    else:
        cur = db

    param_placeholder = "%s" if current_app.config.get('DATABASE_URL') else "?"

    # Atualiza o status da solicitação para pendente (1)
    cur.execute( # Use cur.execute
        f'UPDATE usuarios SET solicitacao_exclusao = 1 WHERE id = {param_placeholder}',
        (user_id,)
    )
    db.commit()
    flash('Sua solicitação de exclusão de conta foi enviada para aprovação.', 'info')
    return redirect(url_for('auth.perfil'))

# NOVO: Rota para a página "Esqueci a Senha" (solicitação de redefinição)
@bp.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form['email']
        db = get_db()
        # NOVO: Crie um cursor a partir da conexão (com DictCursor para SELECT)
        if current_app.config.get('DATABASE_URL'):
            cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else:
            cur = db

        param_placeholder = "%s" if current_app.config.get('DATABASE_URL') else "?"
        user = cur.execute(f'SELECT id, email FROM usuarios WHERE email = {param_placeholder}', (email,)).fetchone() # Use cur.execute

        if user:
            # Gerar um token único e com expiração
            token = str(uuid.uuid4())
            expiration = datetime.now() + timedelta(hours=1) # Token válido por 1 hora

            # Armazenar o token no banco de dados (precisa de uma tabela 'tokens'!)
            # NOVO: Crie um cursor separado para a inserção de token (não precisa de DictCursor)
            if current_app.config.get('DATABASE_URL'):
                insert_cur = db.cursor() 
            else:
                insert_cur = db

            insert_cur.execute( # Use insert_cur.execute
                f'INSERT INTO tokens (user_id, token, expiration) VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder})',
                (user['id'], token, expiration)
            )
            db.commit()

            # Construir o link de redefinição
            reset_link = url_for('auth.resetar_senha', token=token, _external=True)

            # Enviar e-mail com o link de redefinição
            if enviar_email_reset_senha(user['email'], reset_link):
                flash('Um link para redefinir sua senha foi enviado para seu e-mail (se ele estiver cadastrado).', 'info')
            else:
                flash('Ocorreu um erro ao enviar o e-mail de redefinição. Tente novamente mais tarde.', 'danger')
        else:
            # Não diga ao usuário que o e-mail não foi encontrado por segurança
            flash('Um link para redefinir sua senha foi enviado para seu e-mail (se ele estiver cadastrado).', 'info')
    return render_template('esqueci_senha.html')

# NOVO: Rota para a página de redefinição de senha (com token)
@bp.route('/resetar_senha/<token>', methods=['GET', 'POST'])
def resetar_senha(token):
    db = get_db()
    # NOVO: Crie um cursor para buscar o token (com DictCursor para SELECT)
    if current_app.config.get('DATABASE_URL'):
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    else:
        cur = db

    param_placeholder = "%s" if current_app.config.get('DATABASE_URL') else "?"
    
    # Buscar o token no banco de dados
    t = cur.execute(f'SELECT user_id, expiration FROM tokens WHERE token = {param_placeholder}', (token,)).fetchone() # Use cur.execute

    if not t or t['expiration'] < datetime.now():
        flash('Link de redefinição de senha inválido ou expirado.', 'danger')
        return redirect(url_for('auth.esqueci_senha'))

    if request.method == 'POST':
        nova_senha = request.form['nova_senha']
        confirma_senha = request.form['confirma_senha']

        if nova_senha != confirma_senha:
            flash('As senhas não coincidem.', 'danger')
            return render_template('resetar_senha.html', token=token) # Passa o token de volta para o form

        # NOVO: Crie um cursor para as atualizações/deleções (sem DictCursor)
        if current_app.config.get('DATABASE_URL'):
            update_cur = db.cursor()
        else:
            update_cur = db

        # Atualizar a senha do usuário
        update_cur.execute( # Use update_cur.execute
            f'UPDATE usuarios SET senha = {param_placeholder} WHERE id = {param_placeholder}',
            (nova_senha, t['user_id'])
        )
        # Invalidar o token usado (removendo-o do banco de dados)
        update_cur.execute(f'DELETE FROM tokens WHERE token = {param_placeholder}', (token,)) # Use update_cur.execute
        db.commit()

        flash('Sua senha foi redefinida com sucesso! Por favor, faça login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('resetar_senha.html', token=token)
