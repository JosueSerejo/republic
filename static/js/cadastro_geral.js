function validarTelefoneECPF() {
    let isFormValid = true;
    const telefoneInput = document.getElementById("telefone");
    const cpfInput = document.getElementById('cpf');

    if (telefoneInput) {
        if (!telefoneInput.checkValidity()) {
            isFormValid = false;
            if (typeof telefoneInput.reportValidity === 'function') {
                telefoneInput.reportValidity();
            }
        }
    }

    if (cpfInput) {
        if (!cpfInput.checkValidity()) {
            isFormValid = false;
            if (typeof cpfInput.reportValidity === 'function') {
                cpfInput.reportValidity();
            }
        }
    }

    if (!isFormValid) {
        if (telefoneInput && !telefoneInput.checkValidity()) {
            telefoneInput.focus();
        } else if (cpfInput && !cpfInput.checkValidity()) {
            cpfInput.focus();
        }
        return false;
    }
    return true;
}

document.addEventListener("DOMContentLoaded", function () {
    const telefoneInput = document.getElementById("telefone");
    if (telefoneInput) {
        telefoneInput.addEventListener("input", function (e) {
            let input = e.target.value;
            input = input.replace(/\D/g, "");

            if (input.length > 0) {
                input = input.replace(/^(\d{0,2})(\d{0,5})(\d{0,4}).*/, function (match, p1, p2, p3) {
                    let result = "";
                    if (p1) result += "(" + p1;
                    if (p1 && p1.length === 2) result += ") ";
                    if (p2) result += p2;
                    if (p3 && p3.length) result += "-" + p3;
                    return result;
                });
            }
            e.target.value = input;
        });
    }
});