// ============================================================================
// File: static/script.js - Main JavaScript
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeChatbot();
    loadNotifications();
});

// ============================================================================
// CHATBOT FUNCTIONALITY
// ============================================================================

function initializeChatbot() {
    const chatbotToggle = document.getElementById('chatbotToggle');
    const chatbotModal = new bootstrap.Modal(document.getElementById('chatbotModal'));
    const chatInput = document.getElementById('chatInput');
    const sendChat = document.getElementById('sendChat');
    const chatMessages = document.getElementById('chatbotMessages');

    chatbotToggle.addEventListener('click', () => chatbotModal.show());

    sendChat.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Add user message to chat
        addChatMessage(message, 'user');
        chatInput.value = '';

        // Send to server
        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                addChatMessage(data.response, 'bot');
            } else {
                addChatMessage('Sorry, I encountered an error. Please try again.', 'bot');
            }
        })
        .catch(err => {
            console.error('Chat error:', err);
            addChatMessage('Connection error. Please try again.', 'bot');
        });
    }

    function addChatMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message animate__animated animate__fadeIn`;
        
        // Handle formatted text with line breaks
        const formattedText = text
            .replace(/\*\*/g, '')
            .replace(/\n/g, '<br>')
            .replace(/•/g, '•');
        
        messageDiv.innerHTML = `<p class="mb-0">${formattedText}</p>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// ============================================================================
// NOTIFICATIONS
// ============================================================================

function loadNotifications() {
    fetch('/api/alerts')
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success' && data.alerts.length > 0) {
                displayNotifications(data.alerts);
            }
        })
        .catch(err => console.error('Error loading alerts:', err));
}

function displayNotifications(alerts) {
    const container = document.getElementById('alertContainer');
    
    alerts.slice(0, 3).forEach((alert, index) => {
        setTimeout(() => {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${alert.severity === 'critical' ? 'danger' : 'warning'} 
                                position-fixed top-0 end-0 m-3 animate__animated animate__slideInDown`;
            alertDiv.style.zIndex = '9999';
            alertDiv.innerHTML = `
                <strong>${alert.product}</strong>
                <p class="mb-0 mt-2">${alert.message}</p>
                <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
            `;
            container.appendChild(alertDiv);
            
            // Auto-remove after 5 seconds
            setTimeout(() => alertDiv.remove(), 5000);
        }, index * 500);
    });
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 
                         translate-middle-x mt-3 animate__animated animate__slideInDown`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    
    setTimeout(() => alertDiv.remove(), 4000);
}

function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

function calculateDaysLeft(expiryDate) {
    const today = new Date();
    const expiry = new Date(expiryDate);
    const diffTime = expiry - today;
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}
// ============================================================================
// Updated JavaScript for sales_counter.html - Replace the script section
// ============================================================================

let currentProduct = null;
let currentBarcode = null;

// Setup upload area
function setupUploadArea() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('barcodeFile');

    uploadArea.onclick = () => fileInput.click();

    uploadArea.ondragover = (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    };

    uploadArea.ondragleave = () => {
        uploadArea.classList.remove('dragover');
    };

    uploadArea.ondrop = (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleBarcodeUpload();
        }
    };

    fileInput.onchange = handleBarcodeUpload;
}

function handleBarcodeUpload() {
    const file = document.getElementById('barcodeFile').files[0];
    if (!file) return;

    showAlert('Scanning barcode...', 'info');

    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            Quagga.decodeSingle({
                src: e.target.result,
                numOfWorkers: 2,
                inputStream: { size: 800 },
                decoder: {
                    readers: ["code_128_reader", "ean_reader", "ean_8_reader", "code_39_reader", "upc_reader", "upc_e_reader", "i2of5_reader"]
                }
            }, (result) => {
                if (result && result.codeResult) {
                    console.log("Barcode detected:", result.codeResult.code);
                    fetchProductDetails(result.codeResult.code);
                } else {
                    showAlert('No barcode detected. Try another image.', 'warning');
                }
            });
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function fetchProductDetails(barcode) {
    currentBarcode = barcode;
    
    console.log("Fetching product for barcode:", barcode);
    showAlert('Fetching product details...', 'info');

    fetch(`/api/product-by-barcode?barcode=${encodeURIComponent(barcode)}`)
        .then(res => {
            console.log("Response status:", res.status);
            return res.json();
        })
        .then(data => {
            console.log("Response data:", data);
            
            if (data.status === 'success' && data.data) {
                currentProduct = data.data;
                console.log("Product stored:", currentProduct);
                displayProductDetails(data.data);
                showAlert('Product found! Enter quantity to proceed.', 'success');
            } else {
                console.error("Error response:", data.message);
                showAlert('Product not found in database: ' + (data.message || 'Unknown error'), 'danger');
                resetCounter();
            }
        })
        .catch(err => {
            console.error("Fetch error:", err);
            showAlert('Error fetching product: ' + err.message, 'danger');
            resetCounter();
        });
}

function displayProductDetails(product) {
    console.log("Displaying product:", product);
    
    // Set product details
    document.getElementById('productName').textContent = product.name || '-';
    document.getElementById('productBarcode').textContent = product.barcode || '-';
    document.getElementById('productCategory').textContent = product.category || '-';
    document.getElementById('productPrice').textContent = `$${(product.price || 0).toFixed(2)}`;
    document.getElementById('productStock').textContent = `${product.stock_quantity || 0} strips`;
    document.getElementById('productExpiry').textContent = product.expiry_date || '-';

    // Show sections
    document.getElementById('productSection').style.display = 'block';
    document.getElementById('quantitySection').style.display = 'block';

    // Reset quantity
    document.getElementById('quantityInput').value = 1;
    
    // Update price calculation
    updatePriceCalculation();
}

function increaseQuantity() {
    if (!currentProduct) {
        showAlert('No product selected', 'warning');
        return;
    }
    
    const input = document.getElementById('quantityInput');
    const max = currentProduct.stock_quantity;
    const currentValue = parseInt(input.value) || 1;
    
    if (currentValue < max) {
        input.value = currentValue + 1;
        updatePriceCalculation();
    } else {
        showAlert('Cannot exceed available stock!', 'warning');
    }
}

function decreaseQuantity() {
    const input = document.getElementById('quantityInput');
    const currentValue = parseInt(input.value) || 1;
    
    if (currentValue > 1) {
        input.value = currentValue - 1;
        updatePriceCalculation();
    }
}

function updatePriceCalculation() {
    if (!currentProduct) return;
    
    const quantity = parseInt(document.getElementById('quantityInput').value) || 1;
    const unitPrice = currentProduct.price || 0;
    const total = quantity * unitPrice;

    document.getElementById('quantityDisplay').textContent = quantity;
    document.getElementById('unitPrice').textContent = `$${unitPrice.toFixed(2)}`;
    document.getElementById('totalAmount').textContent = `$${total.toFixed(2)}`;

    const stockWarning = document.getElementById('stockWarning');
    if (quantity > currentProduct.stock_quantity) {
        stockWarning.textContent = '⚠️ Quantity exceeds available stock!';
        stockWarning.style.color = '#e74c3c';
    } else if (quantity > 0) {
        const remaining = currentProduct.stock_quantity - quantity;
        stockWarning.textContent = `${remaining} strips remaining after sale`;
        stockWarning.style.color = '#27ae60';
    }
}

function completeSale() {
    if (!currentProduct || !currentBarcode) {
        showAlert('No product selected', 'danger');
        return;
    }

    const quantity = parseInt(document.getElementById('quantityInput').value) || 1;

    if (quantity > currentProduct.stock_quantity) {
        showAlert('Insufficient stock!', 'danger');
        return;
    }

    const saleData = {
        barcode: currentBarcode,
        quantity: quantity,
        amount: quantity * currentProduct.price,
        product_id: currentProduct.id
    };

    console.log("Recording sale:", saleData);

    fetch('/api/record-sale', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(saleData)
    })
    .then(res => res.json())
    .then(data => {
        console.log("Sale response:", data);
        
        if (data.status === 'success') {
            showAlert('Sale completed successfully!', 'success');
            addTransactionToTable(saleData);
            loadSalesStats();
            resetCounter();
        } else {
            showAlert(data.message || 'Failed to record sale', 'danger');
        }
    })
    .catch(err => {
        console.error("Sale error:", err);
        showAlert('Error: ' + err.message, 'danger');
    });
}

function addTransactionToTable(sale) {
    const table = document.getElementById('transactionsBody');
    
    // Remove empty state
    if (table.querySelector('tr td[colspan]')) {
        table.innerHTML = '';
    }

    const row = document.createElement('tr');
    const now = new Date();
    const time = now.toLocaleTimeString();

    row.innerHTML = `
        <td>${time}</td>
        <td><strong>${currentProduct.name}</strong></td>
        <td><code>${sale.barcode}</code></td>
        <td>${sale.quantity}</td>
        <td>$${currentProduct.price.toFixed(2)}</td>
        <td><strong>$${sale.amount.toFixed(2)}</strong></td>
    `;
    table.insertBefore(row, table.firstChild);
}

function loadSalesStats() {
    fetch('/api/sales-stats')
        .then(res => res.json())
        .then(data => {
            console.log("Sales stats:", data);
            
            if (data.status === 'success') {
                document.getElementById('todaysSales').textContent = data.total_transactions || 0;
                document.getElementById('totalRevenue').textContent = `$${(data.total_revenue || 0).toFixed(2)}`;
                document.getElementById('unitsSold').textContent = data.total_units || 0;
            }
        })
        .catch(err => console.error('Error loading stats:', err));
}

function downloadReport() {
    showAlert('Generating report...', 'info');
    window.location.href = '/api/sales-report/download';
}

function resetCounter() {
    currentProduct = null;
    currentBarcode = null;
    document.getElementById('productSection').style.display = 'none';
    document.getElementById('quantitySection').style.display = 'none';
    document.getElementById('quantityInput').value = 1;
    document.getElementById('barcodeFile').value = '';
}

function showAlert(message, type) {
    const container = document.getElementById('alertContainer');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 150);
    }, 5000);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log("Sales Counter page loaded");
    setupUploadArea();
    loadSalesStats();
    setInterval(loadSalesStats, 30000);
});

// Quantity input change listener
if (document.getElementById('quantityInput')) {
    document.getElementById('quantityInput').addEventListener('change', updatePriceCalculation);
    document.getElementById('quantityInput').addEventListener('input', updatePriceCalculation);
}

// ============================================================================
// File: requirements.txt - Python Dependencies
// ============================================================================