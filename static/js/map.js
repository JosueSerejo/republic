// map.js
document.addEventListener("DOMContentLoaded", () => {
  const coords = [-2.9086316915186963, -41.76884957507456]; // Parnaíba, PI
  const map = L.map('map').setView(coords, 17);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);

  L.marker(coords)
    .addTo(map)
    .bindPopup('Condomínio em Parnaíba')
    .openPopup();

  L.circle(coords, {
    radius: 50,
    color: '#007bff',
    fillOpacity: 0.5
  }).addTo(map);
});


document.addEventListener('DOMContentLoaded', function () {
  const contactBtn = document.getElementById('contactAnuncianteBtn'); // Seleciona o botão pelo ID
  if (contactBtn) { // Verifica se o botão existe
    contactBtn.addEventListener('click', function () { // Adiciona um ouvinte de evento de clique
      fetch('/track_click', { // Faz uma requisição POST para a nova rota Flask
        method: 'POST',
        headers: {
          'Content-Type': 'application/json', // Informa que o corpo da requisição é JSON
        },
        // Envia o nome do evento no corpo da requisição
        body: JSON.stringify({ event_name: 'contact_anunciante_click' }),
      })
        .then(response => {
          if (!response.ok) { // Verifica se a requisição foi bem-sucedida (status 2xx)
            console.error('Erro ao rastrear clique:', response.statusText);
          }
        })
        .catch(error => { // Captura erros de rede
          console.error('Erro de rede ao rastrear clique:', error);
        });
      // O link do WhatsApp é aberto automaticamente pelo 'href' do 'a' pai
      // ou você poderia colocá-lo aqui com window.open se o button não estivesse dentro de um <a>
    });
  }
});