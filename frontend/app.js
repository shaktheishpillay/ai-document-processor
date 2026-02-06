// Configuration
const API_BASE_URL = 'http://localhost:8000/api';

// State management
let currentDocument = null;
let pollingInterval = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeNavigation();
    initializeUpload();
    loadDocuments();
    loadAnalytics();
    
    // Add filter listener
    document.getElementById('statusFilter').addEventListener('change', loadDocuments);
});

// Navigation
function initializeNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const viewName = btn.getAttribute('data-view');
            switchView(viewName);
            
            // Update active state
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
}

function switchView(viewName) {
    const views = document.querySelectorAll('.view');
    views.forEach(view => view.classList.remove('active'));
    
    const targetView = document.getElementById(`${viewName}View`);
    if (targetView) {
        targetView.classList.add('active');
        
        // Refresh data when switching views
        if (viewName === 'documents') {
            loadDocuments();
        } else if (viewName === 'analytics') {
            loadAnalytics();
        }
    }
}

// Upload functionality
function initializeUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    
    // Click to upload
    uploadArea.addEventListener('click', () => fileInput.click());
    
    // File selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragging');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragging');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragging');
        
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });
}

async function handleFileUpload(file) {
    // Validate file
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/tiff'];
    if (!allowedTypes.includes(file.type)) {
        showToast('Invalid file type. Please upload PDF, PNG, JPG, or TIFF.', 'error');
        return;
    }
    
    if (file.size > 10 * 1024 * 1024) {
        showToast('File too large. Maximum size is 10MB.', 'error');
        return;
    }
    
    try {
        showLoading(true);
        
        // Upload file
        const formData = new FormData();
        formData.append('file', file);
        
        const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            throw new Error('Upload failed');
        }
        
        const uploadData = await uploadResponse.json();
        currentDocument = uploadData;
        
        // Show upload status
        showUploadStatus(`File uploaded: ${file.name}`, 'success');
        
        // Start processing
        await processDocument(uploadData.document_id);
        
    } catch (error) {
        console.error('Upload error:', error);
        showToast('Upload failed. Please try again.', 'error');
        showLoading(false);
    }
}

async function processDocument(documentId) {
    try {
        // Start processing
        const processResponse = await fetch(`${API_BASE_URL}/process/${documentId}`, {
            method: 'POST'
        });
        
        if (!processResponse.ok) {
            throw new Error('Processing failed to start');
        }
        
        showUploadStatus('Processing document...', 'processing');
        
        // Poll for results
        pollingInterval = setInterval(async () => {
            await checkProcessingStatus(documentId);
        }, 2000);
        
    } catch (error) {
        console.error('Processing error:', error);
        showToast('Processing failed. Please try again.', 'error');
        showLoading(false);
    }
}

async function checkProcessingStatus(documentId) {
    try {
        const response = await fetch(`${API_BASE_URL}/process/${documentId}/status`);
        
        if (!response.ok) {
            throw new Error('Failed to check status');
        }
        
        const data = await response.json();
        
        if (data.status === 'completed') {
            clearInterval(pollingInterval);
            showLoading(false);
            displayResults(data);
            showToast('Document processed successfully!', 'success');
        } else if (data.status === 'failed') {
            clearInterval(pollingInterval);
            showLoading(false);
            showToast('Processing failed. Please try again.', 'error');
        }
        
    } catch (error) {
        console.error('Status check error:', error);
        clearInterval(pollingInterval);
        showLoading(false);
    }
}

function displayResults(data) {
    const resultsContainer = document.getElementById('resultsContainer');
    const extractedFields = document.getElementById('extractedFields');
    
    // Update metadata
    document.getElementById('docType').textContent = 
        data.document_type ? formatDocumentType(data.document_type) : 'Unknown';
    document.getElementById('confidence').textContent = 
        data.confidence_score ? `${(data.confidence_score * 100).toFixed(1)}%` : 'N/A';
    document.getElementById('processingTime').textContent = 
        `${data.processing_time.toFixed(2)}s`;
    
    // Clear previous fields
    extractedFields.innerHTML = '';
    
    // Display extracted fields
    if (data.extracted_data && data.extracted_data.fields) {
        data.extracted_data.fields.forEach(field => {
            const fieldElement = createFieldElement(field);
            extractedFields.appendChild(fieldElement);
        });
    }
    
    // Show results
    resultsContainer.classList.remove('hidden');
    
    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function createFieldElement(field) {
    const div = document.createElement('div');
    div.className = 'field-item';
    
    const confidence = field.confidence || 0;
    const confidenceClass = confidence >= 0.8 ? 'high' : confidence >= 0.6 ? 'medium' : 'low';
    
    div.innerHTML = `
        <div class="field-header">
            <span class="field-name">${formatFieldName(field.field_name)}</span>
            <span class="field-confidence ${confidenceClass}">
                ${(confidence * 100).toFixed(0)}%
            </span>
        </div>
        <div class="field-value">${formatFieldValue(field.value, field.data_type)}</div>
    `;
    
    return div;
}

function formatFieldName(name) {
    return name
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

function formatFieldValue(value, dataType) {
    if (value === null || value === undefined) return 'N/A';
    
    if (dataType === 'currency') {
        const num = parseFloat(value);
        if (!isNaN(num)) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
            }).format(num);
        }
    }
    
    if (dataType === 'number') {
        const num = parseFloat(value);
        if (!isNaN(num)) {
            return new Intl.NumberFormat('en-US').format(num);
        }
    }
    
    return value.toString();
}

function formatDocumentType(type) {
    return type
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

function clearResults() {
    document.getElementById('resultsContainer').classList.add('hidden');
    document.getElementById('uploadStatus').classList.add('hidden');
    document.getElementById('fileInput').value = '';
    currentDocument = null;
}

async function exportCurrent() {
    if (!currentDocument) {
        showToast('No document to export', 'error');
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch(`${API_BASE_URL}/export`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_ids: [currentDocument.document_id],
                format: 'csv',
                include_confidence: true
            })
        });
        
        if (!response.ok) {
            throw new Error('Export failed');
        }
        
        const data = await response.json();
        
        // Download file
        window.open(`http://localhost:8000${data.download_url}`, '_blank');
        
        showToast('Export successful!', 'success');
        showLoading(false);
        
    } catch (error) {
        console.error('Export error:', error);
        showToast('Export failed. Please try again.', 'error');
        showLoading(false);
    }
}

// Documents view
async function loadDocuments() {
    const tableContainer = document.getElementById('documentsTable');
    const statusFilter = document.getElementById('statusFilter').value;
    
    try {
        let url = `${API_BASE_URL}/documents?page=1&page_size=50`;
        if (statusFilter) {
            url += `&status=${statusFilter}`;
        }
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error('Failed to load documents');
        }
        
        const data = await response.json();
        
        // Clear table
        tableContainer.innerHTML = '';
        
        if (data.documents.length === 0) {
            tableContainer.innerHTML = '<div class="table-loading">No documents found</div>';
            return;
        }
        
        // Add documents
        data.documents.forEach(doc => {
            const row = createDocumentRow(doc);
            tableContainer.appendChild(row);
        });
        
    } catch (error) {
        console.error('Load documents error:', error);
        tableContainer.innerHTML = '<div class="table-loading">Failed to load documents</div>';
    }
}

function createDocumentRow(doc) {
    const div = document.createElement('div');
    div.className = 'document-row';
    
    const confidence = doc.confidence_score 
        ? `${(doc.confidence_score * 100).toFixed(1)}%` 
        : 'N/A';
    
    div.innerHTML = `
        <div class="doc-filename" title="${doc.original_filename}">
            ${doc.original_filename}
        </div>
        <div class="doc-type">${doc.document_type || 'Unknown'}</div>
        <div class="doc-date">${formatDate(doc.created_at)}</div>
        <div class="doc-status ${doc.status}">${doc.status}</div>
        <div class="doc-confidence">${confidence}</div>
    `;
    
    return div;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

function refreshDocuments() {
    loadDocuments();
    showToast('Documents refreshed', 'success');
}

// Analytics view
async function loadAnalytics() {
    try {
        const response = await fetch(`${API_BASE_URL}/statistics`);
        
        if (!response.ok) {
            throw new Error('Failed to load statistics');
        }
        
        const data = await response.json();
        
        // Update stats
        document.getElementById('totalDocs').textContent = data.total_documents;
        document.getElementById('processedDocs').textContent = data.processed_documents;
        document.getElementById('avgTime').textContent = `${data.average_processing_time}s`;
        document.getElementById('timeSaved').textContent = `${data.total_time_saved}h`;
        
        // Update chart
        displayTypeChart(data.documents_by_type);
        
    } catch (error) {
        console.error('Load analytics error:', error);
    }
}

function displayTypeChart(documentsByType) {
    const chartContainer = document.getElementById('typeChart');
    chartContainer.innerHTML = '';
    
    if (Object.keys(documentsByType).length === 0) {
        chartContainer.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 2rem;">No data available</p>';
        return;
    }
    
    const total = Object.values(documentsByType).reduce((a, b) => a + b, 0);
    const colors = [
        'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
    ];
    
    let colorIndex = 0;
    
    Object.entries(documentsByType).forEach(([type, count]) => {
        const percentage = (count / total) * 100;
        
        const item = document.createElement('div');
        item.className = 'chart-item';
        item.innerHTML = `
            <div class="chart-label">${formatDocumentType(type)}</div>
            <div class="chart-bar-container">
                <div class="chart-bar" style="width: ${percentage}%; background: ${colors[colorIndex % colors.length]};">
                    <span class="chart-value">${count}</span>
                </div>
            </div>
        `;
        
        chartContainer.appendChild(item);
        colorIndex++;
    });
}

// Utility functions
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (show) {
        overlay.classList.remove('hidden');
    } else {
        overlay.classList.add('hidden');
    }
}

function showUploadStatus(message, type) {
    const statusElement = document.getElementById('uploadStatus');
    statusElement.textContent = message;
    statusElement.className = `upload-status ${type}`;
    statusElement.classList.remove('hidden');
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// Error handling
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});
