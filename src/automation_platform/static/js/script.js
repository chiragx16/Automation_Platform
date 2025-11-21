function showBotsForOrg(orgName) {
  fetch(`/api/organization/${orgName}`)
    .then(res => res.json())
    .then(bots => {
      let botList = document.getElementById('bot-list');
      botList.innerHTML = '';
      bots.forEach(bot => {
        let botDiv = document.createElement('div');
        botDiv.className = 'box';
        botDiv.innerText = bot.name;
        botDiv.onclick = () => showBotLogs(bot.id);
        botList.appendChild(botDiv);
      });
    });
}

function showBotLogs(botId) {
  fetch(`/api/bots/${botId}`)
    .then(res => res.json())
    .then(bot => {
      let logDiv = document.getElementById('bot-logs');
      logDiv.innerHTML = '<h3>Logs</h3>' + bot.logs.map(l => `<div>${l}</div>`).join('');
    });
}

function populateBotsDropdown() {
  let org = document.getElementById('org-dropdown').value;
  fetch(`/api/organization/${org}`)
    .then(res => res.json())
    .then(bots => {
      let dropdown = document.getElementById('bot-dropdown');
      dropdown.innerHTML = '';
      bots.forEach(bot => {
        let option = document.createElement('option');
        option.value = bot.id;
        option.text = bot.name;
        dropdown.appendChild(option);
      });
    });
}

function runBot() {
  let botId = document.getElementById('bot-dropdown').value;
  // Implement your run logic here
  alert('Run bot: ' + botId);
}

// document.addEventListener("DOMContentLoaded", () => {
//   console.log("Bot click listener ready ✅");

//   // Select the exact grid container
//   const container = document.querySelector(".grid.grid-cols-1");
//   if (!container) {
//     console.warn("Bot container not found");
//     return;
//   }

//   container.addEventListener("click", (e) => {
//     const card = e.target.closest(".bot-card");
//     if (!card) return;

//     const botId = card.dataset.botId;
//     console.log("Clicked bot:", botId);

//     if (!botId) {
//       alert("Missing bot ID!");
//       return;
//     }

//     window.location.href = `/bot-control/logs?bot=${encodeURIComponent(botId)}`;
//   });
// });


document.addEventListener("DOMContentLoaded", () => {
  console.log("Bot click listener ready ✅");

  const container = document.querySelector(".grid.grid-cols-1");
  if (!container) return;

  container.addEventListener("click", (e) => {
    const card = e.target.closest(".bot-card");
    if (!card) return;

    const botId = card.dataset.botId;
    if (!botId) {
      alert("Missing bot ID!");
      return;
    }

    // Create a form dynamically to POST the bot_id
    const form = document.createElement("form");
    form.method = "POST";
    form.action = "/api/botcontrol/bot-control/logs";

    const input = document.createElement("input");
    input.type = "hidden";
    input.name = "bot_id";
    input.value = botId;

    form.appendChild(input);
    document.body.appendChild(form);
    form.submit();
  });
});
