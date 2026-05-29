/* ============================================================
   AI Coaching Orchestrator — Frontend Application Logic
   ============================================================ */

let currentThreadId = null;
let pollInterval = null;

// Current plan data for the workout table tabs
let currentFitnessData = { Gym: [], Yoga: [], Calisthenics: [] };
let activeTab = "Gym";

// ---------------------------------------------------------------------------
// DOM References
// ---------------------------------------------------------------------------
const onboardForm       = document.getElementById('onboard-form');
const onboardSection    = document.getElementById('onboarding-section');
const dashboardSection  = document.getElementById('dashboard-section');
const statusBadge       = document.getElementById('status-badge');
const logsContainer     = document.getElementById('logs-container');
const logCount          = document.getElementById('log-count');
const macroStrip        = document.getElementById('macro-strip');
const seniorCoachBox    = document.getElementById('senior-coach-box');
const directivesList    = document.getElementById('directives-list');
const hitlAlert         = document.getElementById('hitl-alert');
const downloadAlert     = document.getElementById('download-alert');
const resumeBtn         = document.getElementById('resume-btn');
const downloadBtn       = document.getElementById('download-btn');
const trackingPanel     = document.getElementById('tracking-panel');
const workoutPanel      = document.getElementById('workout-panel');
const workoutTabs       = document.getElementById('workout-tabs');
const workoutTbody      = document.getElementById('workout-tbody');

// ---------------------------------------------------------------------------
// Onboard Form Submission
// ---------------------------------------------------------------------------
onboardForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    btnText.textContent = '⏳ Initializing Agents...';
    submitBtn.disabled = true;

    const reqBody = {
        age:              parseInt(document.getElementById('age').value),
        weight_kg:        parseFloat(document.getElementById('weight').value),
        target_weight_kg: parseFloat(document.getElementById('target-weight').value),
        activity_level:   document.getElementById('activity').value,
        primary_goal:     document.getElementById('goal').value,
        experience_level: document.getElementById('experience').value,
        injuries:         document.getElementById('injuries').value
                            .split(',').map(s => s.trim()).filter(Boolean)
    };

    try {
        const res = await fetch('/api/onboard', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reqBody)
        });

        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const data = await res.json();
        currentThreadId = data.thread_id;

        onboardSection.classList.add('hidden');
        dashboardSection.classList.remove('hidden');
        startPolling();
    } catch (err) {
        console.error(err);
        btnText.textContent = '❌ Error — Try Again';
        submitBtn.disabled = false;
    }
});

// ---------------------------------------------------------------------------
// Polling
// ---------------------------------------------------------------------------
function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollStatus(); // immediate first call
    pollInterval = setInterval(pollStatus, 3000);
}

async function pollStatus() {
    if (!currentThreadId) return;
    try {
        const res = await fetch(`/api/status/${currentThreadId}`);
        const data = await res.json();

        if (data.status === 'error' || data.status === 'not_found') return;

        updateStatus(data.status, data.next_nodes);
        updateMacroStrip(data.macro_strategy);
        updateDirectives(data.macro_strategy);
        updateLogs(data.validation_logs);
        updateTrackingPanel(data.tracking_strategy);
        updateWorkoutPanel(data);

        if (data.status === 'completed') {
            clearInterval(pollInterval);
        }
    } catch (err) {
        console.error('Polling error:', err);
    }
}

// ---------------------------------------------------------------------------
// Status Badge
// ---------------------------------------------------------------------------
function updateStatus(status, nextNodes) {
    if (status === 'running') {
        statusBadge.textContent = '⚡ Agents Running';
        statusBadge.className = 'badge badge-running';
        hitlAlert.classList.add('hidden');
    } else if (status === 'paused') {
        statusBadge.textContent = '⏸ Paused — Action Required';
        statusBadge.className = 'badge badge-paused';
        hitlAlert.classList.remove('hidden');
    } else if (status === 'completed') {
        statusBadge.textContent = '✅ Plan Finalized';
        statusBadge.className = 'badge badge-completed';
        hitlAlert.classList.add('hidden');
        downloadAlert.classList.remove('hidden');
        downloadBtn.href = `/api/download/${currentThreadId}`;
    }
}

// ---------------------------------------------------------------------------
// Senior Coach Directives
// ---------------------------------------------------------------------------
function updateDirectives(macro) {
    if (!macro || !macro.specialist_directives) return;
    const directives = macro.specialist_directives;
    if (Object.keys(directives).length === 0) return;

    seniorCoachBox.classList.remove('hidden');
    directivesList.innerHTML = Object.entries(directives).map(([domain, directive]) => `
        <div class="directive-item">
            <span class="directive-domain">🎯 ${domain}</span>
            <span class="directive-text">${directive}</span>
        </div>
    `).join('');
}

// ---------------------------------------------------------------------------
// Macro Strip
// ---------------------------------------------------------------------------
function updateMacroStrip(macro) {
    if (!macro) return;
    macroStrip.classList.remove('hidden');
    document.querySelector('#macro-cal .macro-val').textContent = macro.target_calories + ' kcal';
    document.querySelector('#macro-protein .macro-val').textContent = macro.protein_g + 'g';
    document.querySelector('#macro-carbs .macro-val').textContent = macro.carbs_g + 'g';
    document.querySelector('#macro-fats .macro-val').textContent = macro.fats_g + 'g';
    document.querySelector('#macro-split .macro-val').textContent = macro.training_split || '—';
}

// ---------------------------------------------------------------------------
// Validation Logs
// ---------------------------------------------------------------------------
function updateLogs(logs) {
    if (!logs || logs.length === 0) return;
    logCount.textContent = logs.length;

    logsContainer.innerHTML = '';
    // Show newest first
    [...logs].reverse().forEach(log => {
        const statusClass = log.status; // "Approved" | "Rejected" | "Modified"
        const statusColorClass = `log-status-${log.status.toLowerCase()}`;
        const div = document.createElement('div');
        div.className = `log-item ${statusClass}`;
        div.innerHTML = `
            <div class="log-meta">
                <span>${log.domain} — Attempt #${log.attempt}</span>
                <span class="${statusColorClass}">${log.status}</span>
            </div>
            ${log.feedback ? `<div class="log-feedback">${log.feedback}</div>` : ''}
        `;
        logsContainer.appendChild(div);
    });
}

// ---------------------------------------------------------------------------
// Tracking Coach Panel
// ---------------------------------------------------------------------------
function updateTrackingPanel(tracking) {
    if (!tracking) return;
    trackingPanel.classList.remove('hidden');

    const fill = (listId, items, prefix = '') => {
        const ul = document.getElementById(listId);
        ul.innerHTML = (items || []).map(item => `<li>${prefix}${item}</li>`).join('');
    };

    fill('tips-list',       tracking.implementation_tips);
    fill('metrics-list',    tracking.weekly_checkin_metrics);
    fill('milestones-list', tracking.milestone_targets);
    fill('warnings-list',   tracking.red_flag_warnings);

    document.getElementById('coach-notes-text').textContent = tracking.coach_notes || '';
}

// ---------------------------------------------------------------------------
// Workout Plan Preview
// ---------------------------------------------------------------------------
function updateWorkoutPanel(data) {
    if (!data.macro_strategy || !data.macro_strategy.specialist_directives) return;

    // Build fitness data from API — we need to poll the plan content
    // The status endpoint returns macro + logs; full session data lives in the state.
    // We'll show the panel only after completion and re-fetch to get workout details.
    if (data.status !== 'completed') return;

    fetchAndRenderWorkoutPlan();
}

async function fetchAndRenderWorkoutPlan() {
    // Re-use the status endpoint — it already has all the state info we need
    // We'll parse the fitness plan if available via a dedicated endpoint
    // For now, show the workout panel shell and populate from download endpoint indirectly
    workoutPanel.classList.remove('hidden');
    workoutTabs.innerHTML = '';
    workoutTbody.innerHTML = '<tr><td colspan="11" style="text-align:center; padding:20px; color: var(--muted);">Plan complete — download the Excel file for the full workout table with demo links.</td></tr>';

    // Create tabs based on available directives in last known macro data
    // (The full exercise list is in the Excel; here we note what domains were activated)
}

// ---------------------------------------------------------------------------
// Resume (HITL Approval)
// ---------------------------------------------------------------------------
resumeBtn.addEventListener('click', async () => {
    if (!currentThreadId) return;
    resumeBtn.textContent = '⏳ Resuming...';
    resumeBtn.disabled = true;

    try {
        await fetch(`/api/resume/${currentThreadId}`, { method: 'POST' });
        setTimeout(() => {
            resumeBtn.textContent = '✅ Approve & Resume';
            resumeBtn.disabled = false;
        }, 3500);
    } catch (err) {
        console.error(err);
        resumeBtn.textContent = '✅ Approve & Resume';
        resumeBtn.disabled = false;
    }
});
