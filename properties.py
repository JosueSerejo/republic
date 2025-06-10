# properties.py

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, current_app, flash
from werkzeug.utils import secure_filename
import os
import json
from database import get_db
from auth import login_required  # Importa o decorador de login

# Cria um Blueprint para as rotas de gerenciamento de imóveis
bp = Blueprint('properties', __name__, url_prefix='/')

# ----- ROTAS DE PÁGINAS DE IMÓVEIS -----

@bp.route('/pesquisa')
def pesquisa():
    """
    Exibe a página de pesquisa de imóveis, listando todos os imóveis ativos.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT id, tipo, endereco, quartos, valor, inclusos, imagem
        FROM imoveis
        WHERE ativo = 1
        """
    ).fetchall()
    imoveis = []
    for r in rows:
        imoveis.append({
            'id': r['id'],
            'tipo': r['tipo'],
            'quartos': r['quartos'],
            'valor': r['valor'],
            'endereco': r['endereco'],
            'inclusos': r['inclusos'].split(',') if r['inclusos'] else [],
            'imagens': r['imagem'].split(',') if r['imagem'] else ['default.jpg'],
        })
    return render_template('pesquisa.html', imoveis=imoveis)


@bp.route('/detalhes_imovel/<int:id>')
def detalhes_imovel(id):
    """
    Exibe os detalhes de um imóvel específico.
    """
    db = get_db()
    r = db.execute(
        """
        SELECT imoveis.*, usuarios.nome AS dono, usuarios.telefone AS telefone_dono
        FROM imoveis
        JOIN usuarios ON usuarios.id = imoveis.usuario_id
        WHERE imoveis.id = ?
        """, (id,)
    ).fetchone()

    if not r:
        flash('Imóvel não encontrado.', 'danger')
        # Redireciona para pesquisa se não encontrar
        return redirect(url_for('properties.pesquisa'))

    apt = dict(r)
    apt['inclusos'] = apt['inclusos'].split(',') if apt['inclusos'] else []
    apt['imagens'] = apt['imagem'].split(
        ',') if apt['imagem'] else ['default.jpg']

    return render_template(
        'apt.html',
        apartamento=apt,
        dono_nome=r['dono'],
        telefone_dono=r['telefone_dono'],
        usuario_logado=session.get('usuario_id')
    )

# ----- GERENCIAMENTO DE IMÓVEIS (ANUNCIANTES) -----


@bp.route('/cadastro_imovel', methods=['GET', 'POST'])
@login_required
def cadastro_imovel():
    """
    Permite que anunciantes cadastrem novos imóveis.
    Verifica se o usuário logado é um 'anunciante'.
    """
    db = get_db()
    user_id = session.get('usuario_id')
    tipo = db.execute('SELECT tipo_usuario FROM usuarios WHERE id = ?',
                      (user_id,)).fetchone()[0]
    if tipo != 'anunciante':
        flash('Apenas anunciantes podem cadastrar imóveis.', 'warning')
        return redirect(url_for('index'))  # Redireciona para a página inicial

    if request.method == 'POST':
        data = request.form.to_dict()
        inclusos = request.form.getlist('inclusos')
        files = request.files.getlist('fotos')
        nomes = []
        for f in files:
            if f.filename:
                fn = secure_filename(f.filename)
                path = os.path.join(current_app.config['UPLOAD_FOLDER'], fn)
                f.save(path)
                nomes.append(fn)
        if not nomes:
            nomes = ['default.jpg']  # Imagem padrão se nenhuma for enviada

        try:
            db.execute(
                '''INSERT INTO imoveis (endereco, bairro, numero, cep, complemento,
                                        valor, quartos, banheiros, inclusos,
                                        outros, descricao, imagem, tipo, usuario_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (*[data.get(k) for k in ['endereco', 'bairro', 'numero', 'cep', 'complemento']],
                 # Converte valor para float
                 float(data['valor'].replace(',', '.')),
                 int(data['quartos']), int(data['banheiros']),
                 ','.join(inclusos), data.get(
                     'outros', ''), data.get('descricao', ''),
                 ','.join(nomes), data['tipo'], user_id)
            )
            db.commit()
            flash('Imóvel cadastrado com sucesso!', 'success')
            return redirect(url_for('properties.meus_imoveis'))
        except Exception as e:
            flash(f'Erro ao cadastrar imóvel: {e}', 'danger')
            current_app.logger.error(
                f"Erro ao cadastrar imóvel: {e}")  # Loga o erro
    return render_template('cadastro_imovel.html')


@bp.route('/meus_imoveis')
@login_required
def meus_imoveis():
    """
    Exibe a lista de imóveis cadastrados pelo usuário logado.
    """
    db = get_db()
    rows = db.execute(
        'SELECT id, endereco, bairro, valor, tipo, imagem, ativo FROM imoveis WHERE usuario_id = ?',
        (session['usuario_id'],)
    ).fetchall()
    return render_template('meus_imoveis.html', imoveis=rows)


@bp.route('/editar_imovel/<int:id>', methods=['GET'])
@login_required
def editar_imovel(id):
    """
    Exibe o formulário para editar um imóvel específico.
    """
    db = get_db()
    apt = db.execute(
        'SELECT valor, descricao FROM imoveis WHERE id = ? AND usuario_id = ?',
        (id, session['usuario_id'])
    ).fetchone()
    if not apt:
        flash('Imóvel não encontrado ou você não tem permissão para editá-lo.', 'danger')
        return redirect(url_for('properties.meus_imoveis'))
    return render_template('editar_imovel.html', id=id, valor=apt['valor'], descricao=apt['descricao'])


@bp.route('/excluir_imovel/<int:id>', methods=['POST'])
@login_required
def excluir_imovel(id):
    """
    Exclui um imóvel. Apenas o proprietário do imóvel pode excluí-lo.
    """
    db = get_db()
    # Só permite exclusão se o imóvel pertence ao usuário logado
    cursor = db.execute('DELETE FROM imoveis WHERE id = ? AND usuario_id = ?',
                        (id, session['usuario_id']))
    db.commit()
    if cursor.rowcount > 0:
        flash('Imóvel excluído com sucesso!', 'success')
    else:
        flash('Imóvel não encontrado ou você não tem permissão para excluí-lo.', 'danger')
    return redirect(url_for('properties.meus_imoveis'))


@bp.route('/parar_anuncio/<int:id>', methods=['POST'])
@login_required
def parar_anuncio(id):
    """
    Desativa um anúncio de imóvel. Apenas o proprietário pode desativá-lo.
    """
    db = get_db()
    cursor = db.execute('UPDATE imoveis SET ativo = 0 WHERE id = ? AND usuario_id = ?',
                        (id, session['usuario_id']))
    db.commit()
    if cursor.rowcount > 0:
        flash('Anúncio desativado com sucesso!', 'success')
    else:
        flash('Imóvel não encontrado ou você não tem permissão para desativá-lo.', 'danger')
    return redirect(url_for('properties.meus_imoveis'))


@bp.route('/ativar_anuncio/<int:id>', methods=['POST'])
@login_required
def ativar_anuncio(id):
    """
    Ativa um anúncio de imóvel. Apenas o proprietário pode ativá-lo.
    """
    db = get_db()
    cursor = db.execute('UPDATE imoveis SET ativo = 1 WHERE id = ? AND usuario_id = ?',
                        (id, session['usuario_id']))
    db.commit()
    if cursor.rowcount > 0:
        flash('Anúncio ativado com sucesso!', 'success')
    else:
        flash('Imóvel não encontrado ou você não tem permissão para ativá-lo.', 'danger')
    return redirect(url_for('properties.meus_imoveis'))

# ----- ROTAS API JSON -----


@bp.route('/api/imovel/<int:id>')
@login_required
def api_get_imovel(id):
    """
    API para obter detalhes de um imóvel em formato JSON.
    Requer que o usuário esteja logado e seja o proprietário do imóvel.
    """
    db = get_db()
    imovel = db.execute(
        'SELECT * FROM imoveis WHERE id = ? AND usuario_id = ?',
        (id, session['usuario_id'])
    ).fetchone()
    if not imovel:
        return jsonify({'erro': 'Imóvel não encontrado ou não autorizado'}), 404
    return jsonify({
        'id': imovel['id'],
        'tipo': imovel['tipo'],
        'endereco': imovel['endereco'],
        'bairro': imovel['bairro'],
        'numero': imovel['numero'],
        'cep': imovel['cep'],
        'complemento': imovel['complemento'],
        'valor': imovel['valor'],
        'quartos': imovel['quartos'],
        'banheiros': imovel['banheiros'],
        'inclusos': imovel['inclusos'].split(',') if imovel['inclusos'] else [],
        'outros': imovel['outros'],
        'descricao': imovel['descricao'],
        'fotos': imovel['imagem'].split(',') if imovel['imagem'] else []
    })


@bp.route('/api/imoveis/<int:id>', methods=['PUT'])
@login_required
def atualizar_imovel(id):
    """
    API para atualizar os dados de um imóvel.
    Requer que o usuário esteja logado e seja o proprietário do imóvel.
    Recebe os dados em formato JSON.
    """
    dados_json = request.form.get(
        'dados')  # Assumindo que os dados JSON vêm em um campo 'dados'
    if not dados_json:
        return jsonify({'erro': 'Dados inválidos ou ausentes'}), 400
    try:
        dados = json.loads(dados_json)
    except json.JSONDecodeError:
        return jsonify({'erro': 'Erro ao decodificar JSON'}), 400

    db = get_db()
    cursor = db.execute('''
        UPDATE imoveis
        SET tipo = ?, endereco = ?, bairro = ?, numero = ?, cep = ?, complemento = ?, valor = ?,
            quartos = ?, banheiros = ?, inclusos = ?, outros = ?, descricao = ?
        WHERE id = ? AND usuario_id = ?
    ''', (
        dados.get('tipo'),
        dados.get('endereco'),
        dados.get('bairro'),
        dados.get('numero'),
        dados.get('cep'),
        dados.get('complemento'),
        dados.get('valor'),
        dados.get('quartos'),
        dados.get('banheiros'),
        ','.join(dados.get('inclusos', [])),
        dados.get('outros'),
        dados.get('descricao'),
        id,
        session['usuario_id']
    ))
    db.commit()
    if cursor.rowcount > 0:
        return jsonify({'mensagem': 'Imóvel atualizado com sucesso!'}), 200
    else:
        return jsonify({'erro': 'Imóvel não encontrado ou não autorizado'}), 404