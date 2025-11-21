// static/js/home.js
const fmt = (n)=> new Intl.NumberFormat().format(n);


async function loadHome() {
  try {
    const statsRes = await fetch('/api/home/stats');
    const stats = await statsRes.json();

    const total = stats.total_bots;
    const activeCount = stats.active_bots;
    const totalUsers = stats.total_users;

    console.log(total, activeCount, totalUsers);
    // KPI Updates
    document.getElementById('kpi-total').textContent = fmt(total);
    document.getElementById('kpi-active').textContent = fmt(activeCount);
    document.getElementById('kpi-users').textContent = fmt(totalUsers);

    // Bars
    document.getElementById('kpi-total-bar').style.width = '100%';
    document.getElementById('kpi-active-bar').style.width = Math.min(100, (activeCount / (total || 1)) * 100) + '%';

  } catch (error) {
    console.error("Failed to load dashboard stats:", error);
  }
}


// async function loadHome() {
//   const [botsRes, activeRes, orgRes] = await Promise.all([
//     fetch('/api/bots/allbots'),
//     fetch('/api/bots/active'),
//     fetch('/api/bots/organizations')
//   ]);
//   const bots = await botsRes.json();
//   const active = await activeRes.json();
//   const orgs = await orgRes.json();

//   // KPIs
//   const total = bots.length;
//   const activeCount = active.length;
//   document.getElementById('kpi-total').textContent = fmt(total);
//   document.getElementById('kpi-active').textContent = fmt(activeCount);
//   document.getElementById('kpi-orgs').textContent = fmt(orgs.length);
//   document.getElementById('kpi-total-bar').style.width = Math.min(100, (total/ (total || 1))*100) + '%';
//   document.getElementById('kpi-active-bar').style.width = Math.min(100, (activeCount/ (total || 1))*100) + '%';

  // Active list
  // const activeWrap = document.getElementById('active-list');
  // activeWrap.innerHTML = '';
  // active.slice(0,6).forEach(b => {
  //   const el = document.createElement('div');
  //   // Updated classes for light theme card
  //   el.className = 'flex items-center justify-between p-3 rounded-xl bg-white shadow-sm border border-gray-200';
  //   el.innerHTML = `
  //     <div>
  //       <div class="font-medium">${b.name}</div>
  //       <div class="text-xs text-gray-500">Org: ${b.organization} • Last run: ${b.last_run}</div>
  //     </div>
  //     <a href="/bot-control" class="text-sm px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white">Manage</a>
  //   `; // <-- ADDED text-white HERE
  //   activeWrap.appendChild(el);
  // });

  // Recent runs (infer from bots by last_run time)
//   const recentWrap = document.getElementById('recent-list');
//   recentWrap.innerHTML = '';
//   bots
//     .slice(0, 8)
//     .forEach(b => {
//       const row = document.createElement('div');
//       // Updated classes for light theme card
//       row.className = 'flex items-center justify-between p-3 rounded-xl bg-white shadow-sm border border-gray-200';
//       row.innerHTML = `
//         <div>
//           <div class="font-medium">${b.name}</div>
//           <div class="text-xs text-gray-500">Status: ${b.status} • Last: ${b.last_run}</div>
//         </div>
//         <button data-id="${b.id}" class="runBtn text-sm px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white">Run</button>
//       `; // <-- ADDED text-white HERE
//       recentWrap.appendChild(row);
//     });

//   recentWrap.addEventListener('click', async (e) => {
//     if (e.target.matches('.runBtn')) {
//       const id = e.target.getAttribute('data-id');
//       await fetch('/api/bots/' + id + '/run', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})});
//       e.target.textContent = 'Triggered';
//       e.target.disabled = true;
//     }
//   });
// }

document.addEventListener('DOMContentLoaded', loadHome);