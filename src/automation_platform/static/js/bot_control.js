// Bot Control - Org List View

async function loadOrganizations() {
    const res = await fetch("/api/botcontrol/bot-control-orgs");
    const orgs = await res.json();

    console.log(orgs);

    const orgContainer = document.getElementById("orgContainer");
    orgContainer.innerHTML = "";

    orgs.forEach(org => {
        const card = document.createElement("div");
        card.className =
            "bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-lg transition p-8 cursor-pointer relative";

        card.innerHTML = `
            <div class="border-t-4 border-blue-500 rounded-t-xl -mt-5 mb-3"></div>

            <h3 class="font-semibold text-lg text-gray-800 mb-1">${org.name}</h3>
            <p class="text-gray-500 text-sm">${org.bot_count} Bots Deployed</p>

            <div class="absolute top-6 right-4 text-blue-500">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2"
                     viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round"
                        d="M15 3h6v6m-1.5-4.5L10 15"></path>
                </svg>
            </div>
        `;

        // card.onclick = () => {
        //     window.location.href = `/bot-control?org=${org.id}`;
        // };

        card.onclick = async () => {
            const res = await fetch("/api/botcontrol/bot-control", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ org_id: org.id })
            });

            const html = await res.text();
            document.open();
            document.write(html);
            document.close();
        };




        orgContainer.appendChild(card);
    });
}

document.addEventListener("DOMContentLoaded", loadOrganizations);


