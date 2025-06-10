# admin.py

from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, session, flash, current_app
from database import get_db  # Importa a função get_db
from auth import login_required  # Importa o decorador de login

# Cria um Blueprint para as rotas de administração
bp = Blueprint('admin', __name__, url_prefix='/admin')

# ----- DECORATOR ADMIN -----

def admin_required(f):
    """
    Decorador que verifica se o usuário logado é um administrador.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'info')
            return redirect(url_for('auth.login'))
        db = get_db()
        user = db.execute('SELECT tipo_usuario FROM usuarios WHERE id = ?',
                          (session['usuario_id'],)).fetchone()
        if not user or user['tipo_usuario'] != 'admin':
            flash(
                'Acesso não autorizado. Apenas administradores podem acessar esta página.', 'danger')
            # Redireciona para a página inicial
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapped

# ----- ROTAS DE ADMINISTRAÇÃO -----

@bp.route('/')
@login_required
@admin_required
def admin():
    """
    Página do painel de administração.
    Exibe estatísticas e listas de usuários e imóveis.
    """
    db = get_db()

    # Total de usuários
    usuarios = db.execute(
        'SELECT id, nome, email, telefone, tipo_usuario FROM usuarios'
    ).fetchall()
    total_usuarios = len(usuarios)

    # Total de imóveis, ativos e inativos
    total_imoveis = db.execute('SELECT COUNT(*) FROM imoveis').fetchone()[0]
    ativos = db.execute(
        'SELECT COUNT(*) FROM imoveis WHERE ativo = 1'
    ).fetchone()[0]
    inativos = total_imoveis - ativos

    # Lista completa de imóveis com nome do dono
    imoveis = db.execute(
        '''
        SELECT imoveis.*, usuarios.nome AS dono_nome
        FROM imoveis
        JOIN usuarios ON imoveis.usuario_id = usuarios.id
        '''
    ).fetchall()

    # Busca por solicitações de exclusão pendentes (solicitacao_exclusao = 1)
    solicitacoes_pendentes = db.execute(
        'SELECT id, nome, email, telefone FROM usuarios WHERE solicitacao_exclusao = 1'
    ).fetchall()

    # Busca a contagem de cliques no botão "Falar com anunciante"
    # COALESCE garante que, se a linha não existir (ainda não houve cliques), ele retorne 0.
    contact_anunciante_clicks_row = db.execute(
        "SELECT count FROM click_counts WHERE event_name = 'contact_anunciante_click'"
    ).fetchone()
    contact_anunciante_clicks = contact_anunciante_clicks_row[
        'count'] if contact_anunciante_clicks_row else 0

    acessos = getattr(current_app, 'acessos', 0)

    return render_template(
        'admin.html',
        usuarios=usuarios,
        total_usuarios=total_usuarios,
        total_imoveis=total_imoveis,
        ativos=ativos,
        inativos=inativos,
        acessos=acessos,
        imoveis=imoveis,
        solicitacoes_pendentes=solicitacoes_pendentes,
        # Passa a contagem de cliques para o template
        contact_anunciante_clicks=contact_anunciante_clicks
    )

# Rotas para gerenciar solicitações de exclusão de conta

@bp.route('/aceitar_exclusao/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def aceitar_exclusao(user_id):
    db = get_db()

    user = db.execute(
        'SELECT solicitacao_exclusao FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    if not user or user['solicitacao_exclusao'] != 1:
        flash('Solicitação de exclusão não encontrada ou não pendente.', 'warning')
        return redirect(url_for('admin.admin'))

    # ATENÇÃO: Ao aceitar a exclusão, todos os imóveis associados a este usuário serão DELETADOS.
    db.execute('DELETE FROM imoveis WHERE usuario_id = ?', (user_id,))

    db.execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
    db.commit()

    flash(
        f'Solicitação de exclusão para o usuário ID {user_id} aprovada e conta excluída.', 'success')
    # TODO: Lógica para enviar e-mail de aprovação aqui.
    return redirect(url_for('admin.admin'))


@bp.route('/negar_exclusao/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def negar_exclusao(user_id):
    db = get_db()

    user = db.execute(
        'SELECT solicitacao_exclusao FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    if not user or user['solicitacao_exclusao'] != 1:
        flash('Solicitação de exclusão não encontrada ou não pendente.', 'warning')
        return redirect(url_for('admin.admin'))

    # Define a solicitação de volta para 0 (não pendente)
    db.execute(
        'UPDATE usuarios SET solicitacao_exclusao = 0 WHERE id = ?',
        (user_id,)
    )
    db.commit()
    flash(
        f'Solicitação de exclusão para o usuário ID {user_id} negada.', 'info')
    # TODO: Lógica para enviar e-mail de negação aqui.
    return redirect(url_for('admin.admin'))


@bp.route('/admin/toggle_anuncio/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_anuncio(id):
    db = get_db()
    imovel = db.execute(
        'SELECT ativo FROM imoveis WHERE id = ?', (id,)).fetchone()

    if imovel is None:
        flash('Imóvel não encontrado.', 'danger')
        return redirect(url_for('admin.admin'))

    novo_status = 0 if imovel['ativo'] else 1
    db.execute('UPDATE imoveis SET ativo = ? WHERE id = ?', (novo_status, id))
    db.commit()
    flash(
        f'Status do anúncio alterado para {"ativo" if novo_status else "inativo"} com sucesso!', 'success')
    return redirect(url_for('admin.admin'))


@bp.route('/admin/excluir_imovel/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_excluir_imovel(id):
    db = get_db()
    cursor = db.execute('DELETE FROM imoveis WHERE id = ?', (id,))
    db.commit()
    if cursor.rowcount > 0:
        flash('Imóvel excluído com sucesso pelo administrador.', 'success')
    else:
        flash('Imóvel não encontrado.', 'danger')
    return redirect(url_for('admin.admin'))


@bp.route('/admin/excluir_usuario/<int:id>', methods=['POST'])
@login_required
@admin_required
def excluir_usuario(id):
    if id == session['usuario_id']:
        flash("Você não pode excluir seu próprio usuário.", 'warning')
        return redirect(url_for('admin.admin'))

    db = get_db()
    cursor = db.execute('DELETE FROM usuarios WHERE id = ?', (id,))
    db.commit()
    if cursor.rowcount > 0:
        flash("Usuário excluído com sucesso pelo administrador.", 'success')
    else:
        flash("Usuário não encontrado.", 'danger')
    return redirect(url_for('admin.admin'))