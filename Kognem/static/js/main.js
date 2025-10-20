const phoneInput = document.getElementById('phone');
const phoneError = document.getElementById('phoneError');

phoneInput.addEventListener('input', () => {
    const value = phoneInput.value;
    const valid = /^0\d{8}$/.test(value);
    if (!valid && value.length > 0) {
        phoneInput.style.borderColor = '#ff6b6b';
        phoneError.textContent = 'Սխալ հեռախոսահամար՝ օրինակ՝ 0XXXXXXXX';
    } else {
        phoneInput.style.borderColor = '';
        phoneError.textContent = '';
    }
});
