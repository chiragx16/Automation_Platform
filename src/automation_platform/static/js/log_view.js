// log_view.js

const LOG_API_BASE = "/api/bot_reports/show-custom-table";

// Global variables to manage data state
let fullLogData = [];
let sourceDetails = {};
let tableHeaders = [];
let currentlyDisplayedData = []; // CRITICAL: Holds the data array to be exported/rendered

document.addEventListener("DOMContentLoaded", () => {
    // --- Initial Setup and Validation ---
    const pathSegments = window.location.pathname.split('/');
    const sourceId = pathSegments[pathSegments.length - 1]; 

    if (!sourceId || isNaN(sourceId)) {
        // Handle invalid ID error
        const logTablePlaceholder = document.getElementById('logTablePlaceholder');
        logTablePlaceholder.innerHTML = '<p class="p-4 text-red-600">Error: Invalid report ID.</p>';
        return;
    }

    // --- DOM Elements ---
    const reportTitleElement = document.getElementById('reportTitle');
    const reportSubtitleElement = document.getElementById('reportSubtitle');
    const logTablePlaceholder = document.getElementById('logTablePlaceholder');
    const logViewTitle = document.getElementById('logViewTitle');
    const downloadExcelButton = document.getElementById('downloadExcelButton');
    const logSearchInput = document.getElementById('logSearchInput');
    // Note: errorMessage and errorDetails elements are assumed to exist in HTML if used in catch block

    // Initial loading state
    logTablePlaceholder.innerHTML = getLoadingHtml('Fetching report details...');
    
    // --- Event Listeners ---
    
    // 1. Search/Filter Listener
    logSearchInput.addEventListener('keyup', filterAndRenderLogs);
    
    // 2. Download Listener (Client-Side CSV)
    downloadExcelButton.addEventListener('click', (e) => {
        e.preventDefault(); // Prevent default link navigation
        if (!downloadExcelButton.hasAttribute('disabled')) {
            exportToCsv();
        }
    });

    // ----------------------------------------------------
    // 💡 Functionality: Client-Side Export to CSV
    // ----------------------------------------------------
    function exportToCsv() {
        if (!currentlyDisplayedData.length) {
            alert("No logs to download.");
            return;
        }

        // 1. Prepare Header Row (Use display names)
        const headers = tableHeaders.map(header => 
            header.charAt(0).toUpperCase() + header.slice(1).replace(/_/g, ' ')
        );
        let csvContent = headers.join(',') + '\n';

        // 2. Prepare Data Rows
        currentlyDisplayedData.forEach(row => {
            const values = tableHeaders.map(key => {
                let value = row[key] ?? '';
                
                // CRITICAL: Escape values for CSV (especially if content contains commas or quotes)
                if (typeof value === 'string') {
                    // Replace double quotes with two double quotes, then wrap the whole value in quotes
                    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
                        value = `"${value.replace(/"/g, '""')}"`;
                    }
                } else if (value === null || value === undefined) {
                    value = '';
                }
                return value;
            });
            csvContent += values.join(',') + '\n';
        });

        // 3. Trigger Download
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement("a");
        link.setAttribute("href", url);
        
        const filename = (reportTitleElement.textContent || 'log_report')
            .toLowerCase()
            .replace(/[^a-z0-9]/g, '_')
            .substring(0, 30);
            
        link.setAttribute("download", `${filename}_filtered.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    // ----------------------------------------------------
    // 💡 Functionality: Search Filter and Re-Render
    // ----------------------------------------------------
    function filterAndRenderLogs() {
        const searchTerm = logSearchInput.value.toLowerCase().trim();
        let filteredData = fullLogData;

        if (searchTerm) {
            filteredData = fullLogData.filter(row => {
                // Search every column for the term
                return tableHeaders.some(key => 
                    String(row[key] ?? '').toLowerCase().includes(searchTerm)
                );
            });
        }
        
        // CRITICAL: Store the filtered data
        currentlyDisplayedData = filteredData;
        
        // Re-render the table
        const logDataContent = renderJsonAsTable(filteredData, sourceDetails, tableHeaders);

        logTablePlaceholder.innerHTML = `
            <div class="log-source-content">
                ${logDataContent}
                ${filteredData.length === 0 && searchTerm.length > 0 ? '<p class="p-4 text-center text-gray-500">No results found for that search term.</p>' : ''}
            </div>
        `;
        
        // Enable/Disable download button based on results
        if (currentlyDisplayedData.length > 0) {
            downloadExcelButton.removeAttribute('disabled');
        } else {
            downloadExcelButton.setAttribute('disabled', 'true');
        }
    }


    // ----------------------------------------------------
    // Functionality: Initial Data Render
    // ----------------------------------------------------
    function renderReportData(sourceData, botName) {
        sourceDetails = sourceData;
        fullLogData = sourceData.data; 

        reportTitleElement.textContent = sourceData.display_name;
        reportSubtitleElement.textContent = `Endpoint: ${sourceData.endpoint}`;
        logViewTitle.textContent = sourceData.display_name; 

        if (Array.isArray(fullLogData) && fullLogData.length > 0) {
            
            // Determine headers once
            tableHeaders = sourceData.columns && sourceData.columns.length > 0
                ? sourceData.columns
                : Object.keys(fullLogData[0]);

            // Initial render uses full data
            currentlyDisplayedData = fullLogData; 
            
            // Render the table
            const logDataContent = renderJsonAsTable(fullLogData, sourceDetails, tableHeaders);
            logTablePlaceholder.innerHTML = `<div class="log-source-content">${logDataContent}</div>`;
            
            logSearchInput.removeAttribute('disabled');
            downloadExcelButton.removeAttribute('disabled');
        } else {
            // Handle error/empty data display
            const errorText = (typeof fullLogData === 'string' && fullLogData.startsWith('External endpoint returned'))
                ? fullLogData
                : 'Report data could not be retrieved or was empty.';
            
            const errorHtml = `
            <div class="p-4 border border-gray-300 rounded-lg bg-white overflow-x-auto text-sm">
                <h4 class="font-bold text-red-600 mb-2">Error or Raw Data for ${sourceData.display_name}</h4>
                <pre class="whitespace-pre-wrap font-mono text-gray-700">${errorText}</pre>
            </div>`;
            
            logTablePlaceholder.innerHTML = `<div class="log-source-content">${errorHtml}</div>`;
            downloadExcelButton.setAttribute('disabled', 'true');
        }
    }


    // ----------------------------------------------------
    // Helper: HTML Table Renderer (No significant change)
    // ----------------------------------------------------
    function renderJsonAsTable(data, source, headers) {
        if (!Array.isArray(data) || data.length === 0) {
            return '<p class="p-4 text-gray-500">No structured log entries found.</p>';
        }

        let tableHtml = `<div class="overflow-x-auto">
        <table class="w-full divide-y divide-gray-200">
            <thead class="bg-indigo-100"><tr>`;

        // Render Headers
        headers.forEach(header => {
            const displayHeader = header.charAt(0).toUpperCase() + header.slice(1).replace(/_/g, ' ');
            tableHtml += `<th class="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">${displayHeader}</th>`;
        });

        tableHtml += `</tr></thead><tbody class="bg-white divide-y divide-gray-200 text-sm text-gray-700">`;

        // Render Rows
        data.forEach(row => {
            tableHtml += `<tr>`;
            headers.forEach(header => {
                let cellContent = row[header] ?? '';
                let statusClass = '';

                // Simple styling for common status keywords
                if (typeof cellContent === 'string') {
                    const contentLower = cellContent.toLowerCase();
                    if (contentLower.includes('success')) {
                        statusClass = 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800';
                    } else if (contentLower.includes('error') || contentLower.includes('fail')) {
                        statusClass = 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800';
                    } else if (contentLower.includes('warning')) {
                        statusClass = 'px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800';
                    }
                }

                if (statusClass) {
                    cellContent = `<span class="${statusClass}">${cellContent}</span>`;
                }
                
                tableHtml += `<td class="px-6 py-4 whitespace-nowrap text-center">${cellContent}</td>`;
            });
            tableHtml += `</tr>`;
        });

        tableHtml += `</tbody></table></div>`;
        return tableHtml;
    }


    // ----------------------------------------------------
    // Helper: Loading HTML (No change)
    // ----------------------------------------------------
    function getLoadingHtml(message) {
        return `
            <div class="p-4 text-gray-500 text-sm flex items-center">
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                ${message}
            </div>
        `;
    }

    // ----------------------------------------------------
    // Functionality: API Fetch and Initialization (No change to core fetch)
    // ----------------------------------------------------
    async function fetchLogData() {
        logSearchInput.setAttribute('disabled', 'true');
        downloadExcelButton.setAttribute('disabled', 'true');
        
        try {
            const logResponse = await fetch(`${LOG_API_BASE}?source_id=${sourceId}`);
            const result = await logResponse.json();

            if (!logResponse.ok) {
                const errorMsg = result.error || result.message || `Failed to load report data for ID: ${sourceId}.`;
                throw new Error(errorMsg);
            }

            // Render the data, which sets the table, headers, and global variables
            renderReportData(result, result.bot_name || 'N/A');

        } catch (e) {
            console.error("API Error:", e);
            // Error handling elements (removed in the current snippet but included in logic)
            // Example cleanup:
            logTablePlaceholder.innerHTML = '';
            reportTitleElement.textContent = `Error Loading Report (ID: ${sourceId})`;
            logViewTitle.textContent = `Error`;
            // assuming error handling elements exist: 
            // errorMessage.classList.remove('hidden'); 
            // errorDetails.textContent = e.message;

            if (downloadExcelButton) {
                downloadExcelButton.setAttribute('disabled', 'true');
            }
        }
    }

    fetchLogData();
});