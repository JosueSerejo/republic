// static/js/editar_imovel.js

// Função para pré-visualizar imagens selecionadas
function previewImages(event) {
    const files = event.target.files;
    const previewContainer = document.getElementById('image-preview-container');
    previewContainer.innerHTML = '';
    if (files.length > 5) {
        alert('Você pode adicionar até 5 imagens.');
        return;
    }
    for (let i = 0; i < files.length; i++) {
        const reader = new FileReader();
        reader.onload = e => {
            const img = document.createElement('img');
            img.src = e.target.result;
            img.classList.add('preview-img');
            previewContainer.appendChild(img);
        };
        reader.readAsDataURL(files[i]);
    }
}

function getUrlParams() {
    const parts = window.location.pathname.split('/');
    return { id: parts[parts.length - 1] };
}

async function carregarDadosImovel() {
    const { id } = getUrlParams();
    if (!id) {
        alert('ID não fornecido');
        return;
    }
    const resp = await fetch(`/api/imovel/${id}`);
    if (!resp.ok) {
        const err = await resp.json();
        alert(err.erro || 'Falha ao carregar');
        return;
    }
    const imovel = await resp.json();
    document.getElementById('imovelId').value = imovel.id;
    ['tipo', 'endereco', 'bairro', 'numero', 'cep', 'complemento', 'valor', 'quartos', 'banheiros', 'outros', 'descricao']
        .forEach(field => document.getElementById(field).value = imovel[field] || '');

    if (imovel.inclusos) {
        imovel.inclusos.forEach(item => {
            const cb = document.querySelector(`input[name="inclusos"][value="${item}"]`);
            if (cb) cb.checked = true;
        });
    }

    const existing = document.getElementById('existing-images-container');
    if (imovel.fotos && imovel.fotos.length) {
        existing.innerHTML = '<h3>Imagens atuais:</h3>';
        imovel.fotos.forEach((f, i) => {
            const wrap = document.createElement('div');
            wrap.className = 'existing-img-wrapper';
            const img = document.createElement('img');
            // IMPORTANTE: Aqui, o url_for não funcionará diretamente em JS puro.
            // Você precisa que o caminho base da imagem seja passado para o JS ou construído aqui.
            // A maneira mais limpa é passar a base_url como uma variável JS.
            // Por enquanto, vamos manter uma solução simples se a API já retorna o caminho completo.
            // Se a API retornar apenas o nome do arquivo, você pode precisar de:
            // img.src = `/static/img/imoveis/${f}`;
            // OU, se precisar usar o url_for do Jinja2, terá que mantê-lo no HTML ou passar via variável global.
            // Para este exemplo, vou supor que a API retorna o nome do arquivo e você quer usar o caminho estático.
            img.src = `/static/img/imoveis/${f}`; // Substitua {{ url_for(...) }} por caminho JS puro
            img.className = 'existing-img';
            const btn = document.createElement('button');
            btn.type = 'button'; btn.textContent = 'X';
            btn.onclick = () => wrap.remove();
            wrap.append(img, btn);
            existing.append(wrap);
        });
    }
}

async function enviarFormulario(e) {
    e.preventDefault();
    const id = document.getElementById('imovelId').value;
    const dados = { inclusos: [] };
    for (const [k, v] of new FormData(e.target)) {
        if (k === 'inclusos') dados.inclusos.push(v);
        else dados[k] = v;
    }

    const fd = new FormData();
    fd.append('dados', JSON.stringify(dados));
    for (let file of document.getElementById('foto-input').files) fd.append('novas_fotos', file);

    const resp = await fetch(`/api/imoveis/${id}`, { method: 'PUT', body: fd });
    if (!resp.ok) throw new Error('Erro na atualização');
    alert('Atualizado!');
    // IMPORTANTE: url_for não funcionará em JS puro aqui.
    // Você precisa que o Flask passe o URL final para o JS ou construí-lo.
    // Vou adicionar um placeholder que será substituído no HTML.
    window.location.href = window.meusImoveisUrl; // Será definido no HTML
}

document.addEventListener('DOMContentLoaded', () => {
    carregarDadosImovel();
    document.getElementById('editarImovelForm').onsubmit = enviarFormulario;
});