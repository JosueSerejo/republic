// Máscara simples de CEP: 12345-678
function maskCEP(input) {
    input.addEventListener('input', () => {
        let v = input.value.replace(/\D/g, '');
        if (v.length > 5) v = v.slice(0, 5) + '-' + v.slice(5, 8);
        input.value = v;
    });
}

// Formata valor como moeda brasileira: 1.234,56
function maskCurrency(input) {
    input.addEventListener('input', () => {
        let v = input.value.replace(/\D/g, '');
        v = (v / 100).toFixed(2) + '';
        v = v.replace('.', ',');
        v = v.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
        input.value = v;
    });
}

// Pré-visualização de imagens selecionadas
function previewImages(event) {
    const files = event.target.files;
    const previewContainer = document.getElementById('image-preview-container');
    previewContainer.innerHTML = '';

    if (files.length > 5) {
        alert('Você pode adicionar até 5 imagens.');
        event.target.value = '';  // limpa seleção
        return;
    }

    Array.from(files).forEach(file => {
        const reader = new FileReader();
        reader.onload = e => {
            const img = document.createElement('img');
            img.src = e.target.result;
            img.classList.add('preview-img');
            previewContainer.appendChild(img);
        };
        reader.readAsDataURL(file);
    });
}

function getUrlParams() {
    const parts = window.location.pathname.split('/');
    return { id: parts.pop() };
}

async function carregarDadosImovel() {
    const { id } = getUrlParams();
    if (!id) { alert('ID não fornecido'); return; }

    const resp = await fetch(`/api/imovel/${id}`);
    if (!resp.ok) {
        const err = await resp.json();
        alert(err.erro || 'Falha ao carregar');
        return;
    }

    const imovel = await resp.json();
    document.getElementById('imovelId').value = imovel.id;
    ['tipo', 'endereco', 'bairro', 'numero', 'cep', 'complemento', 'valor', 'quartos', 'banheiros', 'outros', 'descricao']
        .forEach(f => document.getElementById(f).value = imovel[f] || '');

    imovel.inclusos?.forEach(item => {
        const cb = document.querySelector(`input[name="inclusos"][value="${item}"]`);
        if (cb) cb.checked = true;
    });

    const existing = document.getElementById('existing-images-container');
    if (imovel.fotos?.length) {
        existing.innerHTML = '<h3>Imagens atuais:</h3>';
        imovel.fotos.forEach(f => {
            const wrap = document.createElement('div');
            wrap.className = 'existing-img-wrapper';
            const img = document.createElement('img');
            img.src = f;
            img.className = 'existing-img';
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.textContent = 'X';
            btn.onclick = () => wrap.remove();
            wrap.append(img, btn);
            existing.append(wrap);
        });
    }
}

async function enviarFormulario(e) {
    e.preventDefault();

    // Validação: pelo menos uma foto (existente ou nova)
    const existentes = document.querySelectorAll('#existing-images-container img').length;
    const novas = document.getElementById('foto-input').files.length;
    if (existentes + novas === 0) {
        alert('Adicione ao menos uma foto do imóvel.');
        return;
    }

    const id = document.getElementById('imovelId').value;
    const dados = { inclusos: [] };
    new FormData(e.target).forEach((v, k) => {
        if (k === 'inclusos') dados.inclusos.push(v);
        else dados[k] = v;
    });

    const fd = new FormData();
    fd.append('dados', JSON.stringify(dados));
    Array.from(document.getElementById('foto-input').files)
        .forEach(file => fd.append('novas_fotos', file));

    const resp = await fetch(`/api/imoveis/${id}`, { method: 'PUT', body: fd });
    if (!resp.ok) {
        const err = await resp.text();
        alert(err || 'Erro na atualização');
        return;
    }

    alert('Atualizado!');
    window.location.href = "{{ url_for('meus_imoveis') }}";
}

document.addEventListener('DOMContentLoaded', () => {
    maskCEP(document.getElementById('cep'));
    maskCurrency(document.getElementById('valor'));
    carregarDadosImovel();
    document.getElementById('editarImovelForm').onsubmit = enviarFormulario;
});


// static/js/pesquisa_filtros.js (NOVA VERSÃO PARA NOVOS FILTROS)

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const cardContainer = document.getElementById('cardContainer');
    const allCards = Array.from(cardContainer.querySelectorAll('.card')); // Captura todos os cards uma vez

    // Elementos do filtro de Valor
    const minValorInput = document.getElementById('minValor');
    const maxValorInput = document.getElementById('maxValor');

    // Elementos do filtro de Tipo
    const tipoCheckboxes = document.querySelectorAll('input[name="tipo"]');

    // Elementos do filtro de Quartos (Slider)
    const quartosSlider = document.getElementById('quartosSlider');
    const quartosValueSpan = document.getElementById('quartosValue');

    // Elementos do filtro de Extras
    const extrasCheckboxes = document.querySelectorAll('input[name="extras"]');

    // --- Event Listeners ---
    searchInput.addEventListener('input', applyFilters); // 'input' para capturar mudanças em tempo real
    minValorInput.addEventListener('input', applyFilters);
    maxValorInput.addEventListener('input', applyFilters);
    tipoCheckboxes.forEach(checkbox => checkbox.addEventListener('change', applyFilters));
    quartosSlider.addEventListener('input', () => {
        quartosValueSpan.textContent = quartosSlider.value; // Atualiza o span do slider
        applyFilters(); // Aplica os filtros ao mover o slider
    });
    extrasCheckboxes.forEach(checkbox => checkbox.addEventListener('change', applyFilters));

    // --- Função Principal de Filtragem ---
    function applyFilters() {
        const searchTerm = searchInput.value.toLowerCase().trim();

        // Valores de filtro
        const minValor = parseFloat(minValorInput.value) || 0; // Garante que é um número, ou 0
        const maxValor = parseFloat(maxValorInput.value) || Infinity; // Garante que é um número, ou infinito

        const selectedTipos = Array.from(tipoCheckboxes)
                                .filter(checkbox => checkbox.checked)
                                .map(checkbox => checkbox.value.toLowerCase());

        const minQuartos = parseInt(quartosSlider.value); // Valor do slider

        const selectedExtras = Array.from(extrasCheckboxes)
                                .filter(checkbox => checkbox.checked)
                                .map(checkbox => checkbox.value.toLowerCase());

        allCards.forEach(card => {
            const cardTipo = card.dataset.tipo.toLowerCase();
            const cardQuartos = parseInt(card.dataset.quartos);
            const cardValor = parseFloat(card.dataset.valor);
            const cardEndereco = card.dataset.endereco.toLowerCase();
            const cardInclusos = card.dataset.extras ? card.dataset.extras.toLowerCase().split(',') : [];

            let matches = true; // Assume que o card corresponde, e desabilita se não

            // 1. Filtro por Busca (Endereço)
            if (searchTerm && !cardEndereco.includes(searchTerm)) {
                matches = false;
            }

            // 2. Filtro por Valor
            if (matches && (cardValor < minValor || cardValor > maxValor)) {
                matches = false;
            }

            // 3. Filtro por Tipo
            if (matches && selectedTipos.length > 0 && !selectedTipos.includes(cardTipo)) {
                matches = false;
            }

            // 4. Filtro por Quartos (Mínimo de Quartos do Slider)
            if (matches && cardQuartos < minQuartos) {
                matches = false;
            }

            // 5. Filtro por Extras (TODOS os selecionados devem estar presentes)
            if (matches && selectedExtras.length > 0) {
                const allExtrasPresent = selectedExtras.every(selectedExtra => cardInclusos.includes(selectedExtra));
                if (!allExtrasPresent) {
                    matches = false;
                }
            }

            // Exibe ou esconde o card
            if (matches) {
                card.style.display = 'flex'; // Ou 'block', dependendo do seu CSS de card
            } else {
                card.style.display = 'none';
            }
        });
    }

    // Inicializa o valor do span do slider
    quartosValueSpan.textContent = quartosSlider.value;

    // Aplica os filtros na carga inicial da página
    applyFilters();
});