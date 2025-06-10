// static/js/flash_messages.js

document.addEventListener('DOMContentLoaded', () => {
    const messageContainer = document.querySelector('.flash-message-container');

    if (messageContainer) {
        // Encontra todas as mensagens flash dentro do container
        const flashMessages = messageContainer.querySelectorAll('.flash-message');

        flashMessages.forEach(message => {
            // Adiciona funcionalidade de fechar ao botão "X"
            const closeBtn = message.querySelector('.close-btn');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    dismissMessage(message);
                });
            }

            // Faz a mensagem sumir automaticamente após 3 segundos
            setTimeout(() => {
                dismissMessage(message);
            }, 3000); // 5000 milissegundos = 3 segundos
        });
    }

    function dismissMessage(messageElement) {
        // Adiciona a classe para animar o fade-out
        messageElement.classList.add('fade-out');

        // Remove o elemento do DOM após a animação de fade-out
        messageElement.addEventListener('animationend', () => {
            messageElement.remove();
        });
    }
});