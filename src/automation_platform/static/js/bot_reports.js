// bot_reports.js

const API_URL = "/api/bot_reports/with-log-sources";
// LOG_VIEW_URL_BASE is defined in the bot_reports.html template

document.addEventListener("DOMContentLoaded", () => {
    const logSourceListContainer = document.getElementById('logSourceListContainer');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const noBotsMessage = document.getElementById('noBotsMessage');

    /**
     * Fetches the list of active log sources and renders them as clickable cards.
     */
    async function fetchLogSources() {
        loadingIndicator.classList.remove('hidden');
        noBotsMessage.classList.add('hidden');
        logSourceListContainer.innerHTML = ''; // Clear container

        try {
            const response = await fetch(API_URL);
            const sources = await response.json();

            if (!response.ok) {
                throw new Error(sources.message || "Failed to fetch report sources.");
            }

            if (sources.length === 0) {
                noBotsMessage.classList.remove('hidden');
            } else {
                renderLogSourceCards(sources);
            }

        } catch (error) {
            console.error("Error fetching sources:", error);
            noBotsMessage.innerHTML = `<span class="text-red-600">Error: Could not load report sources.</span>`;
            noBotsMessage.classList.remove('hidden');
        } finally {
            loadingIndicator.classList.add('hidden');
        }
    }

    /**
     * Renders the list of log sources as cards.
     * @param {Array<{id: number, display_name: string, bot_id: string, bot_name: string}>} sources 
     */
    function renderLogSourceCards(sources) {
        // Group sources by bot_name (optional, but good for organization)
        const groupedSources = sources.reduce((acc, source) => {
            // Use display_name only as requested by the user, but group by bot_name for context
            if (!acc[source.bot_name]) {
                acc[source.bot_name] = [];
            }
            acc[source.bot_name].push(source);
            return acc;
        }, {});

        // Render groups
        for (const [botName, sourceList] of Object.entries(groupedSources)) {
            sourceList.forEach(source => {
                const sourceCard = document.createElement('a');
                
                // *** FIX IS HERE: Use the correct variable name: LOG_VIEW_URL_TEMPLATE ***
                const linkUrl = LOG_VIEW_URL_TEMPLATE.replace('SOURCE_ID_PLACEHOLDER', source.id);

                sourceCard.href = linkUrl;
                sourceCard.className = "source-card block bg-white p-5 rounded-lg shadow-md hover:shadow-xl transition duration-200 ease-in-out border border-gray-100 hover:border-brand-500 cursor-pointer group";
                sourceCard.dataset.sourceId = source.id;
                sourceCard.dataset.displayName = source.display_name;

                sourceCard.innerHTML = `
                    <div class="flex items-center space-x-3">
                        <svg class="h-6 w-6 text-brand-500 group-hover:text-brand-700 transition" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-6 16H8v-2h5v2zm3-4H8v-2h8v2zm0-4H8V9h8v2z"/>
                        </svg>
                        <div class="truncate">
                            <h3 class="text-lg font-bold text-gray-800 group-hover:text-brand-700 truncate">${source.display_name}</h3>
                            <p class="text-s text-gray-500 truncate">Bot: ${botName}</p>
                        </div>
                    </div>
                `;

                logSourceListContainer.appendChild(sourceCard);
            });
        }
    }

    // Initial load of the log source list
    fetchLogSources();
});