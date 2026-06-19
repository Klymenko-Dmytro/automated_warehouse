let selectedCellElement = null;
let globalCellsData = []; // Масив для збереження актуального стану складу з сервера

// Функція вибору комірки мишкою на 2D-карті
function selectCell(element) {
    if (selectedCellElement) {
        selectedCellElement.classList.remove('selected');
    }
    selectedCellElement = element;
    selectedCellElement.classList.add('selected');
    const cellId = element.getAttribute('data-id');
    renderControlPanel(cellId);
}

// Рендеринг вмісту бічної панелі керування
function renderControlPanel(cellId) {
    const cellData = globalCellsData.find(c => c.id == cellId);
    const panelContent = document.getElementById('panelContent');
    if (!cellData) return;

    const addressStr = `Зона ${cellData.zone}, Ряд ${cellData.row}, Полиця ${cellData.shelf}, Місце ${cellData.position}`;
    const currentQty = cellData.product ? cellData.product.quantity : 0;

    // Якщо в комірці є хоча б один товар
    if (currentQty > 0) {
        const prodName = cellData.product.name;
        const prodBarcode = cellData.product.barcode;
        const statusText = cellData.is_occupied ? 'ЗАЙНЯТО ПОВНІСТЮ' : 'ЧАСТКОВО ЗАЙНЯТО';
        const statusColor = cellData.is_occupied ? 'var(--danger)' : 'var(--primary)';

        panelContent.innerHTML = `
            <div class="info-group"><span class="info-label">Обрана адреса:</span><br>${addressStr}</div>
            <div class="info-group"><span class="info-label">Статус:</span> <span style="color:${statusColor}; font-weight:bold;">${statusText}</span></div>
            <div class="info-group"><span class="info-label">Назва товару:</span><br><strong>${prodName}</strong></div>
            <div class="info-group"><span class="info-label">Штрихкод:</span><br><code>${prodBarcode}</code></div>
            <div class="info-group"><span class="info-label">Поточна кількість:</span><br><strong>${currentQty} / 100 шт.</strong></div>
            <div class="info-group">
                <label class="info-label">Кількість для вилучення:</label>
                <input type="number" id="manualQuantity" class="control-input" value="${currentQty}" min="1" max="${currentQty}">
            </div>
            <button class="btn-action btn-remove" onclick="manualRemove(${cellId})">Вилучити вказану кількість</button>
            <div id="actionMsg" class="msg-box"></div>
        `;
    } else {
        // Якщо комірка абсолютно порожня
        panelContent.innerHTML = `
            <div class="info-group"><span class="info-label">Обрана адреса:</span><br>${addressStr}</div>
            <div class="info-group"><span class="info-label">Статус:</span> <span style="color:var(--success); font-weight:bold;">ВІЛЬНА</span></div>
            <div class="info-group">
                <label class="info-label">Назва товару:</label>
                <input type="text" id="manualName" class="control-input" placeholder="Наприклад: Сік Апельсин">
            </div>
            <div class="info-group">
                <label class="info-label">Штрихкод:</label>
                <input type="text" id="manualBarcode" class="control-input" placeholder="13 цифр">
            </div>
            <div class="info-group">
                <label class="info-label">Кількість для додавання (можна > 100):</label>
                <input type="number" id="manualQuantity" class="control-input" value="1" min="1">
            </div>
            <button class="btn-action btn-add" onclick="manualAdd(${cellId})">Розмістити товар</button>
            <div id="actionMsg" class="msg-box"></div>
        `;
    }
}

// Надсилання асинхронного запиту на додавання товару
function manualAdd(cellId) {
    const name = document.getElementById('manualName').value;
    const barcode = document.getElementById('manualBarcode').value;
    const quantity = document.getElementById('manualQuantity').value;
    const msgBox = document.getElementById('actionMsg');

    fetch('/api/manual-add/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cell_id: cellId, name: name, barcode: barcode, quantity: quantity })
    })
    .then(res => res.json())
    .then(data => {
        msgBox.style.color = data.status === 'success' ? 'var(--success)' : 'var(--danger)';
        msgBox.innerText = data.message;
        if (data.status === 'success') updateWarehouseData();
    });
}

// Надсилання асинхронного запиту на вилучення товару
function manualRemove(cellId) {
    const quantity = document.getElementById('manualQuantity').value;
    const msgBox = document.getElementById('actionMsg');

    fetch('/api/manual-remove/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cell_id: cellId, quantity: quantity })
    })
    .then(res => res.json())
    .then(data => {
        msgBox.style.color = data.status === 'success' ? 'var(--success)' : 'var(--danger)';
        msgBox.innerText = data.message;
        if (data.status === 'success') updateWarehouseData();
    });
}

// Функція автоматичного оновлення даних складу в реальному часі (Live)
function updateWarehouseData() {
    fetch('/api/data/')
        .then(response => response.json())
        .then(data => {
            globalCellsData = data.cells;

            // Оновлення логів у файлі script.js
            const logBox = document.getElementById('logBox');
            logBox.innerHTML = '';
            data.logs.forEach(logText => {
                const line = document.createElement('div');
                line.className = 'log-line';

                // Перетворюємо текст у нижній регістр для надійної перевірки
                const lowerText = logText.toLowerCase();

                // Шукаємо будь-які варіації слів "додано" або "додав"
                if (lowerText.includes('додано') || lowerText.includes('додав')) {
                    line.classList.add('log-add');
                }
                // Шукаємо варіації слів "вилучено" або "вилучив"
                else if (lowerText.includes('вилучено') || lowerText.includes('вилучив')) {
                    line.classList.add('log-remove');
                }

                line.innerText = logText;
                logBox.appendChild(line);
            });


            // 2. Оновлення стану відкритої панелі керування (тільки якщо користувач не пише текст зараз)
            if (selectedCellElement) {
                const activeId = selectedCellElement.getAttribute('data-id');
                const inputName = document.getElementById('manualName');
                const inputBarcode = document.getElementById('manualBarcode');
                const inputQty = document.getElementById('manualQuantity');
                const isUserTyping = (document.activeElement === inputName || document.activeElement === inputBarcode || document.activeElement === inputQty);

                if (!isUserTyping) renderControlPanel(activeId);
            }

            // 3. Динамічне перефарбовування 2D-карти складу та оновлення тултипів
            data.cells.forEach(cellData => {
                const cellDiv = document.getElementById(`cell-${cellData.id}`);
                if (cellDiv) {
                    if (window.highlightedCellId && window.highlightedCellId == cellData.id) return;

                    const tooltip = cellDiv.querySelector('.tooltip');
                    const addressStr = `<strong>Адреса:</strong> ${cellData.zone}-Р${cellData.row}-П${cellData.shelf}-М${cellData.position}`;

                    cellDiv.classList.remove('free', 'partial', 'occupied');

                    if (cellData.product && cellData.product.quantity > 0) {
                        if (cellData.is_occupied) {
                            cellDiv.classList.add('occupied'); // Сірий колір (100 шт)
                        } else {
                            cellDiv.classList.add('partial'); // Синій колір (1-99 шт)
                        }
                        if (tooltip) {
                            tooltip.innerHTML = `${addressStr}<br><strong>Товар:</strong> ${cellData.product.name}<br><strong>Баркод:</strong> ${cellData.product.barcode}<br><strong>Кількість:</strong> ${cellData.product.quantity}/100 шт.`;
                        }
                    } else {
                        cellDiv.classList.add('free'); // Зелений колір (порожня)
                        if (tooltip) {
                            tooltip.innerHTML = `${addressStr}<br><span style="color: #2ecc71;">Вільна комірка</span>`;
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Помилка оновлення даних складу:', error));
}

// Ініціалізація першого завантаження та встановлення інтервалу оновлення 3 секунди
updateWarehouseData();
setInterval(updateWarehouseData, 3000);
