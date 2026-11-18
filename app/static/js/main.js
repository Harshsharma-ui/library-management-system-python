/**
 * SecureLib - Frontend Client Script
 * Handles flash alert dismissals, table search, and modal confirmations.
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Auto-dismiss flash alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });

    // 2. Client-side instant table filtering
    const liveSearchInput = document.getElementById('liveTableSearch');
    if (liveSearchInput) {
        liveSearchInput.addEventListener('input', function () {
            const filterValue = this.value.toLowerCase().trim();
            const tableRows = document.querySelectorAll('#filterableTable tbody tr');

            tableRows.forEach(function (row) {
                const textContent = row.textContent.toLowerCase();
                if (textContent.includes(filterValue)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    // 3. Password visibility toggle
    const togglePasswordButtons = document.querySelectorAll('.toggle-password-btn');
    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', function () {
            const inputTargetId = this.getAttribute('data-target');
            const inputField = document.getElementById(inputTargetId);
            if (inputField) {
                const isPassword = inputField.type === 'password';
                inputField.type = isPassword ? 'text' : 'password';
                this.innerHTML = isPassword ? '<i class="bi bi-eye-slash"></i>' : '<i class="bi bi-eye"></i>';
            }
        });
    });
});
