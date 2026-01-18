// Валидация формы регистрации
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('registerForm');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    const passwordRules = document.getElementById('passwordRules');
    const passwordMatch = document.getElementById('passwordMatch');
    
    // Правила валидации пароля
    const passwordRulesList = {
        length: { regex: /.{8,}/, message: 'Минимум 8 символов' },
        uppercase: { regex: /[A-Z]/, message: 'Заглавная буква' },
        lowercase: { regex: /[a-z]/, message: 'Строчная буква' },
        number: { regex: /\d/, message: 'Цифра' },
        special: { regex: /[!@#$%^&*(),.?":{}|<>]/, message: 'Спецсимвол' }
    };
    
    // Обновление визуализации правил пароля
    function updatePasswordRules(password) {
        const rules = passwordRules.querySelectorAll('li');
        
        Object.keys(passwordRulesList).forEach((rule, index) => {
            const icon = rules[index].querySelector('i');
            const isValid = passwordRulesList[rule].regex.test(password);
            
            if (isValid) {
                icon.className = 'fas fa-check text-success';
                rules[index].classList.remove('text-danger');
                rules[index].classList.add('text-success');
            } else {
                icon.className = 'fas fa-times text-danger';
                rules[index].classList.remove('text-success');
                rules[index].classList.add('text-danger');
            }
        });
    }
    
    // Проверка совпадения паролей
    function checkPasswordMatch() {
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        if (!password || !confirmPassword) {
            passwordMatch.textContent = '';
            confirmPasswordInput.classList.remove('is-valid', 'is-invalid');
            return;
        }
        
        if (password === confirmPassword) {
            passwordMatch.innerHTML = '<i class="fas fa-check text-success"></i> Пароли совпадают';
            confirmPasswordInput.classList.remove('is-invalid');
            confirmPasswordInput.classList.add('is-valid');
        } else {
            passwordMatch.innerHTML = '<i class="fas fa-times text-danger"></i> Пароли не совпадают';
            confirmPasswordInput.classList.remove('is-valid');
            confirmPasswordInput.classList.add('is-invalid');
        }
    }
    
    // Показать/скрыть пароль
    document.getElementById('togglePassword1').addEventListener('click', function() {
        const icon = this.querySelector('i');
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        } else {
            passwordInput.type = 'password';
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    });
    
    document.getElementById('togglePassword2').addEventListener('click', function() {
        const icon = this.querySelector('i');
        if (confirmPasswordInput.type === 'password') {
            confirmPasswordInput.type = 'text';
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        } else {
            confirmPasswordInput.type = 'password';
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    });
    
    // Обработчики событий
    passwordInput.addEventListener('input', function() {
        updatePasswordRules(this.value);
        checkPasswordMatch();
    });
    
    confirmPasswordInput.addEventListener('input', checkPasswordMatch);
    
    // Валидация формы перед отправкой
    form.addEventListener('submit', function(event) {
        let isValid = true;
        
        // Проверка пароля
        const password = passwordInput.value;
        Object.keys(passwordRulesList).forEach(rule => {
            if (!passwordRulesList[rule].regex.test(password)) {
                isValid = false;
            }
        });
        
        // Проверка совпадения паролей
        if (password !== confirmPasswordInput.value) {
            isValid = false;
        }
        
        if (!isValid) {
            event.preventDefault();
            alert('Пожалуйста, исправьте ошибки в форме');
        }
    });
    
    // Инициализация
    updatePasswordRules('');
});