const launchpadContainer = document.getElementById("launchpadContainer");

function bindLaunchpadEvents() {
    launchpadContainer.addEventListener('click', (e) => {
        const header = e.target.closest('[id^="orgHeader-"]');
        const botItem = e.target.closest('.bot-item');

        if (header) {
            const orgId = header.id.replace('orgHeader-', '');
            const content = document.getElementById(`botContent-${orgId}`);
            const svg = header.querySelector('svg');

            // Collapse other accordions
            document.querySelectorAll('.bot-content').forEach(c => {
                if (c !== content) c.classList.add('hidden');
            });
            document.querySelectorAll('.org-accordion svg').forEach(s => {
                if (s !== svg) s.classList.remove('rotate-180');
            });

            // Toggle clicked accordion
            content.classList.toggle('hidden');
            svg.classList.toggle('rotate-180');
        }

        if (botItem) {
            const botId = botItem.dataset.botId;

            // Submit via POST
            const form = document.getElementById('botDetailsForm');
            document.getElementById('botIdInput').value = botId;
            form.submit();
        }
    });
}

document.addEventListener("DOMContentLoaded", bindLaunchpadEvents);
