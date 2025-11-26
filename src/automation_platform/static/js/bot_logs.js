// Get references to the elements
const botActiveRadio = document.getElementById('botActive');
const botInactiveRadio = document.getElementById('botInactive');
const logContainer = document.getElementById("botLogs");
const changeAccessBtn = document.getElementById('changeAccessBtn');
const customUrlButtonContainer = document.getElementById('customUrlButtonContainer'); // The container location is now moved

// Modal Elements
const accessModal = document.getElementById('accessModal');
const modalContent = document.getElementById('modalContent');
const cancelAccessBtn = document.getElementById('cancelAccessBtn');
const accessForm = document.getElementById('accessForm');

// Form Inputs and Submit Button
const organizationSelect = document.getElementById('organizationSelect'); // Now a <select>
const userSelect = document.getElementById('userSelect'); // Now a <select>
const allowAccessBtn = document.getElementById('allowAccessBtn');


// --- Validation Function ---
function validateAccessForm() {
    const orgSelected = organizationSelect.value !== "";
    const userSelected = userSelect.value !== "";

    const isValid = orgSelected && userSelected;
    if (allowAccessBtn) {
        allowAccessBtn.disabled = !isValid;
    }
}

// --- Helper Function to Populate Select ---
function populateSelect(selectElement, items, defaultText) {
    selectElement.innerHTML = '';

    const defaultOption = document.createElement('option');
    defaultOption.value = "";
    defaultOption.textContent = defaultText;
    defaultOption.disabled = true;
    defaultOption.selected = true;
    defaultOption.style.color = '#9ca3af'; // gray-400
    selectElement.appendChild(defaultOption);

    items.forEach(item => {
        const option = document.createElement('option');
        option.value = item.id;
        option.textContent = item.name;
        selectElement.appendChild(option);
    });
}

async function fetchOrganizations() {
    if (!BOT_ID) {
        organizationSelect.innerHTML = '<option value="" disabled selected>Error: Bot ID missing</option>';
        organizationSelect.disabled = true;
        return;
    }

    try {
        organizationSelect.innerHTML = '<option value="" disabled selected>Loading organization...</option>';
        organizationSelect.disabled = true;

        // FIX: Pass BOT_ID as a query parameter
        const endpoint = `/api/botcontrol/organizations?bot_id=${BOT_ID}`;
        const res = await fetch(endpoint);
        const data = await res.json();

        if (data.organizations && data.organizations.length > 0) {
            // Since a bot only belongs to one organization, this list will have 1 item.
            // We can pre-select the organization and disable the dropdown if desired.
            populateSelect(organizationSelect, data.organizations, "Choose an organization");

            // Automatically select the organization (there is only one)
            organizationSelect.value = data.organizations[0].id;

            // Optionally, fetch users immediately after loading the organization
            fetchUsersForOrganization(data.organizations[0].id);

        } else {
            organizationSelect.innerHTML = '<option value="" disabled selected>Bot Organization not found or inactive</option>';
            console.error("Bot Organization not found or inactive.");
        }
    } catch (error) {
        organizationSelect.innerHTML = '<option value="" disabled selected>Error loading organization</option>';
        console.error("Error fetching organization:", error);
    } finally {
        // We keep the organizationSelect disabled since it shouldn't be changed
        organizationSelect.disabled = true;
        validateAccessForm(); // Re-validate the form state
    }
}

async function fetchUsersForOrganization(orgId) {
    userSelect.disabled = true;
    userSelect.innerHTML = '<option value="" disabled selected>Loading users...</option>';
    userSelect.value = "";
    validateAccessForm();
    try {
        // NOTE: Using /api/botcontrol/users as per your provided code
        const res = await fetch("/api/botcontrol/users", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ organization_id: orgId })
        });
        const data = await res.json();

        if (data.users && data.users.length > 0) {
            populateSelect(userSelect, data.users, "Choose a user");
        } else {
            userSelect.innerHTML = '<option value="" disabled selected>No active users found</option>';
            console.warn(`No users found for organization ID: ${orgId}`);
        }
    } catch (error) {
        console.error("Error fetching users:", error);
        userSelect.innerHTML = '<option value="" disabled selected>Error loading users</option>';
    } finally {
        userSelect.disabled = false;
        validateAccessForm();
    }
}

// --- Modal Functions ---

function openAccessModal() {
    accessModal.classList.remove('hidden');
    fetchOrganizations();
    userSelect.innerHTML = '<option value="" disabled selected>Select an organization first</option>';
    userSelect.disabled = true;
    validateAccessForm();
    setTimeout(() => {
        modalContent.classList.remove('scale-95', 'opacity-0');
        modalContent.classList.add('scale-100', 'opacity-100');
    }, 10);
}

function closeAccessModal() {
    modalContent.classList.remove('scale-100', 'opacity-100');
    modalContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => {
        accessModal.classList.add('hidden');
    }, 300);
}


// --- API Functions (Toggle Status - FIXED LOGIC) ---
async function toggleBotStatus(activate) {
    if (!BOT_ID) return;

    const endpoint = "/api/botcontrol/set-status";

    // Determine the radio button to revert to if the API call fails
    const radioToRevert = activate ? botInactiveRadio : botActiveRadio;

    if (botActiveRadio) botActiveRadio.disabled = true;
    if (botInactiveRadio) botInactiveRadio.disabled = true;

    try {
        const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                bot_id: BOT_ID,
                activate: activate
            })
        });

        const data = await res.json();

        // FIX: Check for res.ok (HTTP status 200-299) AND a successful message/no error
        if (res.ok && data.message && !data.error) {
            console.log(data.message);
            // On SUCCESS, let fetchBotLogs() confirm the new state and re-enable buttons
            await fetchBotLogs();
        } else {
            // ERROR: Revert radio button state immediately
            alert(`Error: ${data.error || 'Failed to change bot status.'}`);
            if (radioToRevert) radioToRevert.checked = true;
            await fetchBotLogs();
        }
    } catch (err) {
        // NETWORK ERROR: Revert radio button state
        console.error("Error toggling bot status:", err);
        alert("Network error: Could not contact the server.");
        if (radioToRevert) radioToRevert.checked = true;
        await fetchBotLogs();
    } finally {
        if (botActiveRadio) botActiveRadio.disabled = false;
        if (botInactiveRadio) botInactiveRadio.disabled = false;
    }
}

// --- Log and Status Fetching Function (MODIFIED) ---
async function fetchBotLogs() {
    if (!BOT_ID) return;
    try {
        const res = await fetch("/api/botcontrol/bot-wise-logs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bot_id: BOT_ID })
        });
        const data = await res.json();

        // --- 1. HANDLE CUSTOM URL BUTTON (NEW LOGIC) ---
        customUrlButtonContainer.innerHTML = ''; // Clear existing button
        if (data.bot_custom_url) {
            const customUrlBtn = document.createElement('a');
            customUrlBtn.href = data.bot_custom_url;
            customUrlBtn.target = "_blank"; // Open in a new tab

            // 🔥 CHANGED CLASS: Styled as a plain blue link
            customUrlBtn.className = "text-blue-500 hover:underline flex items-center text-sm font-medium";

            customUrlBtn.innerHTML = `
                <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                </svg>
                Bot URL
            `;
            customUrlButtonContainer.appendChild(customUrlBtn);
        }

        // --- 2. Update logs ---
        if (data.error) {
            logContainer.textContent = "No logs found for this bot.";
        } else {
            // Ensure log content is displayed correctly
            logContainer.innerHTML = `<pre>${data.logs}</pre>`;
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        // --- 3. Control segmented control state ---
        if (botActiveRadio && botInactiveRadio) {
            const isActive = data.is_active;
            const botIsActive = isActive === 1 || isActive === true;

            // This reads the definitive status from the server and updates the UI
            botActiveRadio.checked = botIsActive;
            botInactiveRadio.checked = !botIsActive;
        }
    } catch (err) {
        console.error("Error loading logs or fetching status:", err);
        logContainer.textContent = "Error loading logs. Check console for details.";
    }
}


async function checkUserPermission(userId) {
    const res = await fetch("/api/botcontrol/check-permission", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_id: userId,
            bot_id: BOT_ID
        })
    });

    const data = await res.json();
    return data.has_permission;     // true / false
}

// --- Initialization (FIXED: Added missing change listeners for bot status) ---
document.addEventListener("DOMContentLoaded", () => {
    // Initial load and auto-refresh
    fetchBotLogs();
    setInterval(fetchBotLogs, 5000);

    // --- SEGMENTED CONTROL LISTENERS (NEW/FIXED) ---
    // These listeners were missing, causing toggleBotStatus to never run.
    if (botActiveRadio) {
        botActiveRadio.addEventListener('change', () => {
            if (botActiveRadio.checked) toggleBotStatus(true);
        });
    }
    if (botInactiveRadio) {
        botInactiveRadio.addEventListener('change', () => {
            if (botInactiveRadio.checked) toggleBotStatus(false);
        });
    }

    // --- MODAL LISTENERS ---

    // 1. Open Modal Listener  
    if (changeAccessBtn) {
        changeAccessBtn.addEventListener('click', openAccessModal);
    }

    // 2. Close Modal Listeners  
    if (cancelAccessBtn) {
        cancelAccessBtn.addEventListener('click', closeAccessModal);
    }
    if (accessModal) {
        accessModal.addEventListener('click', (e) => {
            if (e.target === accessModal) {
                closeAccessModal();
            }
        });
    }

    // 3. Validation and Dependent Dropdown Listeners
    if (organizationSelect) {
        organizationSelect.addEventListener('change', (event) => {
            const selectedOrgId = event.target.value;
            if (selectedOrgId) {
                fetchUsersForOrganization(selectedOrgId);
            } else {
                userSelect.innerHTML = '<option value="" disabled selected>Select an organization first</option>';
                userSelect.disabled = true;
            }
            validateAccessForm();
        });
    }

    if (userSelect) {
        userSelect.addEventListener("change", async () => {
            validateAccessForm();

            const userId = userSelect.value;

            if (!userId) return;

            // 🔥 Check if selected user already has access
            const hasPermission = await checkUserPermission(userId);

            // 🔄 Update button label based on permission
            if (hasPermission) {
                allowAccessBtn.textContent = "Remove Access";
                allowAccessBtn.dataset.action = "remove"; // for submit logic
                allowAccessBtn.classList.remove("bg-purple-600");
                allowAccessBtn.classList.add("bg-red-600");
            } else {
                allowAccessBtn.textContent = "Allow Access";
                allowAccessBtn.dataset.action = "allow";
                allowAccessBtn.classList.remove("bg-red-600");
                allowAccessBtn.classList.add("bg-purple-600");
            }

            allowAccessBtn.disabled = false;
        });
    }


    // 4. Form Submission Listener  
    if (accessForm) {
        accessForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const userId = userSelect.value;
            const action = allowAccessBtn.dataset.action;

            if (!userId) return;

            // Disable the button while request is running
            allowAccessBtn.disabled = true;
            allowAccessBtn.textContent = "Processing...";

            try {

                let endpoint = "";
                if (action === "allow") {
                    endpoint = "/api/botcontrol/assign-user";
                } else if (action === "remove") {
                    endpoint = "/api/botcontrol/remove-user";
                } else {
                    throw new Error("Invalid action type.");
                }

                const res = await fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        bot_id: BOT_ID,
                        user_id: userId
                    })
                });

                let data = {};
                try {
                    data = await res.json();   // Attempt JSON parsing
                } catch (parseErr) {
                    throw new Error("Invalid JSON response from server.");
                }

                if (!res.ok) {
                    // Backend error (500, 400, etc.)
                    throw new Error(data.error || "Request failed.");
                }

                // SUCCESS 🎉
                alert(data.message || (action === "allow" ? "Access granted" : "Access removed"));
                closeAccessModal();

            } catch (err) {
                // NETWORK or APPLICATION error
                console.error("Submit error:", err);
                alert(`Error: ${err.message}`);
            } finally {
                // Restore button state
                allowAccessBtn.disabled = false;

                if (action === "allow") {
                    allowAccessBtn.textContent = "Allow Access";
                } else {
                    allowAccessBtn.textContent = "Remove Access";
                }
            }
        });
    }
});