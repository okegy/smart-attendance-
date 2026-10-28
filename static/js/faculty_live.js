/**
 * Faculty Dashboard Live Polling
 * Polls the server every 3 seconds for attendance updates.
 */

(function() {
    'use strict';
    
    if (!window.SESSION_ID) return;
    
    const POLL_INTERVAL = 3000;
    const isFullMonitor = window.IS_FULL_MONITOR || false;
    
    let lastDataHash = '';

    function fetchLiveData() {
        fetch(`/faculty/api/session/${window.SESSION_ID}/live/`)
            .then(res => res.json())
            .then(data => {
                // Simple hash to avoid DOM updates if nothing changed
                const hash = JSON.stringify(data);
                if (hash === lastDataHash) return;
                lastDataHash = hash;
                
                updateUI(data);
            })
            .catch(err => console.error("Live poll failed:", err));
    }

    function updateUI(data) {
        if (!isFullMonitor) {
            updateDashboardWidgets(data);
        } else {
            updateFullMonitorGrid(data);
        }
    }

    function updateDashboardWidgets(data) {
        // Update stats
        const totalEl = document.getElementById('stats-total');
        if (totalEl) totalEl.textContent = data.total_unique;
        
        const violationsEl = document.getElementById('stats-violations');
        if (violationsEl) {
            violationsEl.textContent = data.violations.length;
            if (data.violations.length > 0) {
                violationsEl.parentElement.classList.add('pulse-amber', 'border-amber-500/50');
            } else {
                violationsEl.parentElement.classList.remove('pulse-amber', 'border-amber-500/50');
            }
        }

        // Update Feed Table
        const tbody = document.getElementById('live-feed-table');
        if (tbody) {
            if (data.attendees.length === 0) {
                tbody.innerHTML = `<tr><td colspan="3" class="text-center py-8 text-slate-500">No attendance yet.</td></tr>`;
            } else {
                tbody.innerHTML = '';
                // Sort by most recent period
                const sorted = [...data.attendees].sort((a, b) => {
                    const latestA = a.periods[a.periods.length-1].time;
                    const latestB = b.periods[b.periods.length-1].time;
                    return latestB.localeCompare(latestA); // Descending
                });
                
                sorted.forEach(student => {
                    const periodsHTML = student.periods.map(p => 
                        `<span class="inline-block w-6 h-6 rounded bg-emerald-500/20 text-emerald-400 text-[10px] leading-6 text-center border border-emerald-500/30 mr-1" title="${p.status}">P${p.period}</span>`
                    ).join('');
                    
                    const latestTime = student.periods[student.periods.length-1].time;
                    
                    tbody.innerHTML += `
                        <tr class="border-b border-glass/30 hover:bg-white/5 transition-colors">
                            <td class="py-3 pl-2">
                                <div class="font-medium text-white">${student.name}</div>
                                <div class="text-xs text-slate-500 font-mono">${student.roll}</div>
                            </td>
                            <td class="py-3 text-center">${periodsHTML}</td>
                            <td class="py-3 pr-2 text-right text-xs text-slate-400">${latestTime}</td>
                        </tr>
                    `;
                });
            }
        }

        // Update Alerts
        const alertsContainer = document.getElementById('alerts-container');
        if (alertsContainer) {
            if (data.violations.length === 0) {
                alertsContainer.innerHTML = `<div class="text-slate-500 text-sm py-4 text-center">No proxy violations detected yet.</div>`;
            } else {
                alertsContainer.innerHTML = '';
                data.violations.forEach(v => {
                    alertsContainer.innerHTML += `
                        <div class="bg-rose-500/10 border border-rose-500/20 rounded-lg p-3 text-sm relative" id="viol-${v.id}">
                            <div class="text-rose-400 font-bold mb-1"><i class="fa-solid fa-triangle-exclamation mr-1"></i> Proxy Attempt Blocked</div>
                            <div class="text-slate-300">
                                <span class="font-mono text-white">${v.attempted}</span> attempted via <span class="font-mono text-white">${v.original}</span>'s device.
                            </div>
                            <div class="text-xs text-slate-500 mt-2 flex justify-between items-center">
                                <span>Period ${v.period} • ${v.time} • IP: ${v.ip}</span>
                                <button onclick="resolveViolation(${v.id})" class="text-rose-400 hover:text-white transition-colors bg-rose-500/20 px-2 py-1 rounded">Dismiss</button>
                            </div>
                        </div>
                    `;
                });
            }
        }
    }

    function updateFullMonitorGrid(data) {
        const grid = document.getElementById('student-grid');
        const stats = document.getElementById('grid-stats');
        
        if (!grid) return;
        
        if (stats) stats.innerHTML = `<i class="fa-solid fa-user-check mr-1 text-emerald-400"></i> ${data.total_unique} Present`;
        
        if (data.attendees.length === 0) {
            grid.innerHTML = `<div class="col-span-full text-center py-12 text-slate-500">Waiting for students to scan...</div>`;
            return;
        }
        
        grid.innerHTML = '';
        data.attendees.forEach(student => {
            const periodsHTML = student.periods.map(p => 
                `<div class="text-center px-2 py-1 bg-emerald-500/20 border border-emerald-500/30 rounded text-emerald-400 text-xs font-bold">
                    P${p.period}
                </div>`
            ).join('');
            
            grid.innerHTML += `
                <div class="bg-[#121326] border border-glass rounded-xl p-4 flex flex-col justify-between hover:border-emerald-500/30 transition-colors">
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <div class="font-bold text-white">${student.name}</div>
                            <div class="text-xs font-mono text-emerald-400">${student.roll}</div>
                        </div>
                    </div>
                    <div class="flex gap-2 flex-wrap">
                        ${periodsHTML}
                    </div>
                </div>
            `;
        });
    }

    // Export resolve function globally for inline onclick
    window.resolveViolation = function(id) {
        fetch(`/faculty/violation/${id}/resolve/`, { method: 'POST', headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }})
        .then(() => fetchLiveData())
        .catch(err => console.error("Error resolving violation", err));
    };

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Start polling
    fetchLiveData(); // Initial fetch
    setInterval(fetchLiveData, POLL_INTERVAL);

})();
