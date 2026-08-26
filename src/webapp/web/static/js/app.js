/**
 * PiBlindHub - Main JavaScript Application
 */

// Global application state
const App = {
    config: {
        refreshInterval: 30000, // 30 seconds
        logRefreshInterval: 60000, // 60 seconds
        apiBaseUrl: '/api',
        wsUrl: 'ws://localhost:8080/ws' // WebSocket URL for real-time updates
    },
    
    state: {
        isConnected: false,
        currentUser: null,
        devices: [],
        logs: [],
        systemHealth: null
    },
    
    // Initialize the application
    init() {
        this.setupEventListeners();
        this.initializeWebSocket();
        this.startAutoRefresh();
        this.setupTooltips();
        this.setupAlerts();
    },
    
    // Setup global event listeners
    setupEventListeners() {
        // Handle form submissions
        document.addEventListener('submit', (e) => {
            if (e.target.classList.contains('ajax-form')) {
                e.preventDefault();
                this.handleFormSubmission(e.target);
            }
        });
        
        // Handle device control buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-device-action]')) {
                e.preventDefault();
                const button = e.target.closest('[data-device-action]');
                const deviceId = button.dataset.deviceId;
                const action = button.dataset.deviceAction;
                this.controlDevice(deviceId, action);
            }
        });
        
        // Handle modal events
        document.addEventListener('show.bs.modal', (e) => {
            const modal = e.target;
            if (modal.id === 'deviceModal') {
                this.loadDeviceDetails(modal.dataset.deviceId);
            }
        });
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseAutoRefresh();
            } else {
                this.resumeAutoRefresh();
            }
        });
    },
    
    // Initialize WebSocket connection for real-time updates
    initializeWebSocket() {
        try {
            this.ws = new WebSocket(this.config.wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.state.isConnected = true;
                this.updateConnectionStatus(true);
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.state.isConnected = false;
                this.updateConnectionStatus(false);
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.initializeWebSocket(), 5000);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.state.isConnected = false;
                this.updateConnectionStatus(false);
            };
        } catch (error) {
            console.warn('WebSocket not available:', error);
            this.state.isConnected = false;
        }
    },
    
    // Handle WebSocket messages
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'device_status_update':
                this.updateDeviceStatus(data.device_id, data.status);
                break;
            case 'system_health_update':
                this.updateSystemHealth(data.health);
                break;
            case 'new_log_entry':
                this.addLogEntry(data.log);
                break;
            case 'action_completed':
                this.handleActionCompleted(data.action);
                break;
            default:
                console.log('Unknown WebSocket message type:', data.type);
        }
    },
    
    // Update connection status indicator
    updateConnectionStatus(connected) {
        const indicators = document.querySelectorAll('.connection-status');
        indicators.forEach(indicator => {
            indicator.className = `connection-status ${connected ? 'status-online' : 'status-offline'}`;
            indicator.title = connected ? 'Connected' : 'Disconnected';
        });
    },
    
    // Start auto-refresh timers
    startAutoRefresh() {
        // General refresh for dashboard and devices
        this.refreshTimer = setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.refreshCurrentPage();
            }
        }, this.config.refreshInterval);
        
        // Log refresh (less frequent)
        this.logRefreshTimer = setInterval(() => {
            if (document.visibilityState === 'visible' && window.location.pathname === '/logs') {
                this.refreshLogs();
            }
        }, this.config.logRefreshInterval);
    },
    
    // Pause auto-refresh
    pauseAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        if (this.logRefreshTimer) {
            clearInterval(this.logRefreshTimer);
        }
    },
    
    // Resume auto-refresh
    resumeAutoRefresh() {
        this.startAutoRefresh();
    },
    
    // Refresh current page data
    refreshCurrentPage() {
        const path = window.location.pathname;
        
        if (path === '/' || path === '/dashboard') {
            this.refreshDashboard();
        } else if (path === '/devices') {
            this.refreshDevices();
        } else if (path === '/logs') {
            this.refreshLogs();
        } else if (path === '/settings') {
            this.refreshSystemHealth();
        }
        
        // Always refresh service status on dashboard
        if (path === '/' || path === '/dashboard') {
            this.refreshServiceStatus();
        }
    },
    
    // Refresh dashboard data
    async refreshDashboard() {
        try {
            const response = await fetch('/api/system/health');
            const health = await response.json();
            this.updateSystemHealth(health);
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
        }
    },
    
    // Refresh devices data
    async refreshDevices() {
        try {
            // This would typically be an API call to get updated device status
            // For now, we'll just reload the page
            if (this.shouldRefreshPage()) {
                window.location.reload();
            }
        } catch (error) {
            console.error('Error refreshing devices:', error);
        }
    },
    
    // Refresh logs data
    async refreshLogs() {
        try {
            // This would typically be an API call to get new log entries
            // For now, we'll just reload the page
            if (this.shouldRefreshPage()) {
                window.location.reload();
            }
        } catch (error) {
            console.error('Error refreshing logs:', error);
        }
    },
    
    // Refresh system health
    async refreshSystemHealth() {
        try {
            const response = await fetch('/api/system/health');
            const health = await response.json();
            this.updateSystemHealth(health);
        } catch (error) {
            console.error('Error refreshing system health:', error);
        }
    },
    
    // Refresh service status
    async refreshServiceStatus() {
        try {
            const response = await fetch('/api/services/status');
            const data = await response.json();
            
            if (data.success && window.updateServiceStatusDisplay) {
                window.updateServiceStatusDisplay(data);
                if (window.updateLastUpdateTime) {
                    window.updateLastUpdateTime(data.timestamp);
                }
            }
        } catch (error) {
            console.error('Error refreshing service status:', error);
        }
    },
    
    // Check if page should be refreshed (avoid too frequent refreshes)
    shouldRefreshPage() {
        const lastRefresh = localStorage.getItem('lastPageRefresh');
        const now = Date.now();
        const timeSinceLastRefresh = now - (lastRefresh ? parseInt(lastRefresh) : 0);
        
        // Only refresh if it's been more than 25 seconds
        if (timeSinceLastRefresh > 25000) {
            localStorage.setItem('lastPageRefresh', now.toString());
            return true;
        }
        return false;
    },
    
    // Control device
    async controlDevice(deviceId, action) {
        const button = document.querySelector(`[data-device-id="${deviceId}"][data-device-action="${action}"]`);
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Processing...';
        }
        
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/device/${deviceId}/control?action=${action}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showAlert('success', `Device ${action} command sent successfully`);
                
                // Update device status after a short delay
                setTimeout(() => {
                    this.updateDeviceStatus(deviceId, { action: action, status: 'processing' });
                }, 1000);
            } else {
                this.showAlert('danger', 'Failed to send device command');
            }
        } catch (error) {
            console.error('Error controlling device:', error);
            this.showAlert('danger', 'Error sending device command');
        } finally {
            if (button) {
                button.disabled = false;
                button.innerHTML = this.getButtonContent(action);
            }
        }
    },
    
    // Get button content based on action
    getButtonContent(action) {
        const icons = {
            'open': '<i class="bi bi-unlock me-1"></i>Open',
            'close': '<i class="bi bi-lock me-1"></i>Close',
            'stop': '<i class="bi bi-stop me-1"></i>Stop'
        };
        return icons[action] || action;
    },
    
    // Update device status
    updateDeviceStatus(deviceId, statusData) {
        // Update device status in the UI
        const deviceRow = document.querySelector(`tr[data-device-id="${deviceId}"]`);
        if (deviceRow) {
            const statusCell = deviceRow.querySelector('.device-status');
            if (statusCell) {
                statusCell.textContent = statusData.status;
                statusCell.className = `device-status ${statusData.status === 'online' ? 'status-online' : 'status-offline'}`;
            }
        }
        
        // Update device cards
        const deviceCard = document.querySelector(`[data-device-id="${deviceId}"]`);
        if (deviceCard) {
            const statusBadge = deviceCard.querySelector('.badge');
            if (statusBadge) {
                statusBadge.textContent = statusData.status;
                statusBadge.className = `badge ${statusData.status === 'online' ? 'bg-success' : 'bg-danger'}`;
            }
        }
    },
    
    // Update system health
    updateSystemHealth(healthData) {
        this.state.systemHealth = healthData;
        
        // Update health indicators
        const healthIndicators = document.querySelectorAll('.system-health-indicator');
        healthIndicators.forEach(indicator => {
            indicator.className = `system-health-indicator badge ${healthData.overall === 'healthy' ? 'bg-success' : 'bg-danger'}`;
            indicator.textContent = healthData.overall;
        });
        
        // Update service health cards
        const serviceCards = document.querySelectorAll('.service-health-card');
        serviceCards.forEach(card => {
            const serviceName = card.dataset.serviceName;
            const serviceHealth = healthData.services[serviceName];
            if (serviceHealth) {
                const badge = card.querySelector('.badge');
                if (badge) {
                    badge.textContent = serviceHealth.status;
                    badge.className = `badge ${serviceHealth.status === 'healthy' ? 'bg-success' : 'bg-danger'}`;
                }
            }
        });
    },
    
    // Add new log entry
    addLogEntry(logEntry) {
        const logsTable = document.getElementById('logsTable');
        if (logsTable) {
            const tbody = logsTable.querySelector('tbody');
            if (tbody) {
                const newRow = this.createLogRow(logEntry);
                tbody.insertBefore(newRow, tbody.firstChild);
                
                // Remove old entries if too many
                const rows = tbody.querySelectorAll('tr');
                if (rows.length > 100) {
                    rows[rows.length - 1].remove();
                }
            }
        }
    },
    
    // Create log row element
    createLogRow(logEntry) {
        const row = document.createElement('tr');
        row.className = 'log-entry fade-in';
        row.innerHTML = `
            <td><small class="text-muted">${new Date(logEntry.timestamp).toLocaleString()}</small></td>
            <td><span class="badge ${this.getLogLevelClass(logEntry.level)}">${logEntry.level}</span></td>
            <td><span class="badge bg-light text-dark">${logEntry.category}</span></td>
            <td><span class="log-message">${logEntry.message}</span></td>
            <td>${logEntry.details ? '<button class="btn btn-sm btn-outline-info"><i class="bi bi-info-circle"></i></button>' : ''}</td>
        `;
        return row;
    },
    
    // Get log level CSS class
    getLogLevelClass(level) {
        const classes = {
            'DEBUG': 'bg-secondary',
            'INFO': 'bg-info',
            'WARNING': 'bg-warning',
            'ERROR': 'bg-danger',
            'CRITICAL': 'bg-dark'
        };
        return classes[level] || 'bg-secondary';
    },
    
    // Handle action completion
    handleActionCompleted(actionData) {
        this.showAlert('success', `Action ${actionData.action_type} completed for device ${actionData.device_id}`);
        
        // Update device status
        this.updateDeviceStatus(actionData.device_id, { status: 'online' });
    },
    
    // Show alert message
    showAlert(type, message, duration = 5000) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            <i class="bi bi-${this.getAlertIcon(type)} me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('main');
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, duration);
    },
    
    // Get alert icon based on type
    getAlertIcon(type) {
        const icons = {
            'success': 'check-circle',
            'danger': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    },
    
    // Setup Bootstrap tooltips
    setupTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },
    
    // Setup alert dismissal
    setupAlerts() {
        // Auto-dismiss alerts after 5 seconds
        const alerts = document.querySelectorAll('.alert:not(.alert-dismissible)');
        alerts.forEach(alert => {
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 5000);
        });
    },
    
    // Handle form submission
    async handleFormSubmission(form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        
        try {
            const response = await fetch(form.action, {
                method: form.method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showAlert('success', result.message || 'Operation completed successfully');
                if (form.dataset.redirect) {
                    window.location.href = form.dataset.redirect;
                }
            } else {
                this.showAlert('danger', result.message || 'Operation failed');
            }
        } catch (error) {
            console.error('Form submission error:', error);
            this.showAlert('danger', 'An error occurred while processing your request');
        }
    },
    
    // Load device details for modal
    async loadDeviceDetails(deviceId) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/device/${deviceId}/status`);
            const data = await response.json();
            
            const detailsDiv = document.getElementById('deviceDetails');
            if (detailsDiv) {
                detailsDiv.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <strong>Device ID:</strong> ${data.device_id}
                        </div>
                        <div class="col-md-6">
                            <strong>Status:</strong> 
                            <span class="badge ${data.status === 'online' ? 'bg-success' : 'bg-danger'}">${data.status}</span>
                        </div>
                    </div>
                    <div class="row mt-3">
                        <div class="col-md-6">
                            <strong>State:</strong> 
                            <span class="badge ${this.getDeviceStateClass(data.state)}">${data.state}</span>
                        </div>
                        <div class="col-md-6">
                            <strong>Last Updated:</strong> ${data.last_updated || 'Never'}
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading device details:', error);
            this.showAlert('danger', 'Error loading device details');
        }
    },
    
    // Get device state CSS class
    getDeviceStateClass(state) {
        const classes = {
            'OPEN': 'bg-success',
            'CLOSED': 'bg-secondary',
            'MOVING': 'bg-warning',
            'ERROR': 'bg-danger'
        };
        return classes[state] || 'bg-secondary';
    }
};

// Global utility functions
window.controlDevice = (deviceId, action) => App.controlDevice(deviceId, action);
window.refreshDevices = () => App.refreshDevices();
window.refreshLogs = () => App.refreshLogs();
window.showAlert = (type, message) => App.showAlert(type, message);
window.refreshServiceStatus = () => App.refreshServiceStatus();

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (App.ws) {
        App.ws.close();
    }
    App.pauseAutoRefresh();
});
