# app.py (Arquivo principal da aplicação)

from flask import Flask, render_template, g, flash, session, jsonify, request, current_app # Adicionado current_app
# Importa funções do módulo database
from database import close_db, inicializar_banco, get_db
# Importa o blueprint de autenticação e o decorador
from auth import bp as auth_bp # login_required não é usado diretamente aqui, mas em auth.py
from properties import bp as properties_bp # Importa o blueprint de imóveis
# Importa o blueprint de admin e o decorador
from admin import bp as admin_bp # admin_required não é usado diretamente aqui, mas em admin.py
from config import Config # Importa a classe de configuração

app = Flask(__name__)
app.config.from_object(Config) # Carrega as configurações da classe Config

# Registra as funções de teardown do app context
app.teardown_appcontext(close_db)

# Registra os Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(properties_bp)
app.register_blueprint(admin_bp)

# Variável global para contagem de acessos (exemplo)
app.acessos = 0

@app.route('/track_click', methods=['POST'])
def track_click():
    if request.is_json: # Verifica se o corpo da requisição é JSON
        data = request.get_json() # Pega os dados JSON
        event_name = data.get('event_name') # Pega o nome do evento

        if event_name:
            db = get_db() # Obtém a conexão com o banco de dados
            
            # Ajustado para compatibilidade com PostgreSQL (%s) e SQLite (?)
            param_placeholder = "%s" if current_app.config.get('DATABASE_URL') else "?"

            try:
                if current_app.config.get('DATABASE_URL'): # PostgreSQL
                    db.execute(
                        """
                        INSERT INTO click_counts (event_name, count) VALUES (%s, %s)
                        ON CONFLICT (event_name) DO UPDATE SET count = click_counts.count + 1
                        """,
                        (event_name, 1) # No PostgreSQL, insere 1 ou incrementa 1
                    )
                else: # SQLite
                    db.execute(
                        'INSERT OR REPLACE INTO click_counts (event_name, count) VALUES (?, COALESCE((SELECT count FROM click_counts WHERE event_name = ?), 0) + 1)',
                        (event_name, event_name)
                    )
                db.commit() # Salva as mudanças
                return jsonify(success=True, message=f"Clique para '{event_name}' rastreado com sucesso"), 200
            except Exception as e:
                db.rollback() # Reverte em caso de erro
                print(f"Erro ao rastrear clique: {e}")
                return jsonify(success=False, message=f"Erro ao rastrear clique: {e}"), 500
    return jsonify(success=False, message="Requisição inválida"), 400

# ----- CONTEXTO GLOBAL (mantido aqui para ser global para toda a aplicação) -----
# Este context_processor é global para todas as rotas de todos os blueprints

@app.context_processor
def inject_usuario():
    """
    Injeta informações do usuário logado em todos os templates.
    """
    usuario_nome = tipo_usuario = None
    # Usa g.get para evitar KeyError se não estiver setado
    user_id = g.get('usuario_id')
    if user_id:
        # Não precisa importar get_db aqui se já está importado no topo do arquivo
        # from database import get_db
        db = get_db()
        
        # Ajustado para compatibilidade com PostgreSQL (%s) e SQLite (?)
        param_placeholder = "%s" if current_app.config.get('DATABASE_URL') else "?"
        
        cur = db.execute(
            f'SELECT nome, tipo_usuario FROM usuarios WHERE id = {param_placeholder}', (user_id,)
        )
        row = cur.fetchone()
        if row:
            usuario_nome = row['nome']
            tipo_usuario = row['tipo_usuario']
    return dict(usuario_nome=usuario_nome, tipo_usuario=tipo_usuario)

# Antes de cada requisição, tenta obter o usuário logado e armazená-lo em 'g'

@app.before_request
def load_logged_in_user():
    user_id = session.get('usuario_id')
    if user_id is None:
        g.usuario_id = None
    else:
        g.usuario_id = user_id # Armazena o ID do usuário em g para fácil acesso

# ----- ROTAS DE PÁGINAS BÁSICAS -----

@app.route('/')
def index():
    """
    Rota da página inicial. Incrementa o contador de acessos.
    """
    app.acessos += 1
    return render_template('index.html')

@app.route('/sobre')
def sobre():
    """
    Rota da página "Sobre".
    """
    return render_template('sobre.html')

@app.route('/termos')
def termos():
    """
    Rota da página "Termos de Uso".
    """
    return render_template('termos.html')

if __name__ == '__main__':
    # Inicializa o banco de dados dentro de um contexto de aplicação
    with app.app_context(): # ESTA LINHA É A CHAVE DA SOLUÇÃO
        inicializar_banco()
    app.run(debug=True)