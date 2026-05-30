/* ============================================================
   AI Coaching Orchestrator — Frontend Application Logic
   ============================================================ */

let currentThreadId = null;
let pollInterval = null;
let lastPlanHash = null;  // to avoid re-rendering unchanged plans

// ---- DOM refs ----
const onboardSection   = document.getElementById('onboarding-section');
const dashboardSection = document.getElementById('dashboard-section');
const statusBadge      = document.getElementById('status-badge');
const logsContainer    = document.getElementById('logs-container');
const logCount         = document.getElementById('log-count');
const macroStrip       = document.getElementById('macro-strip');
const seniorCoachBox   = document.getElementById('senior-coach-box');
const directivesList   = document.getElementById('directives-list');
const hitlAlert        = document.getElementById('hitl-alert');
const downloadAlert    = document.getElementById('download-alert');
const resumeBtn        = document.getElementById('resume-btn');
const downloadBtn      = document.getElementById('download-btn');
const trackingPanel    = document.getElementById('tracking-panel');
const planViewer       = document.getElementById('plan-viewer');
const planTabs         = document.getElementById('plan-tabs');
const domainTabs       = document.getElementById('domain-tabs');
const domainContent    = document.getElementById('domain-content');
const nutritionContent = document.getElementById('nutrition-content');
const trainingHint     = document.getElementById('training-hint');

// ============================================================
// Training type card interaction
// ============================================================
document.querySelectorAll('input[name="training_type"]').forEach(cb => {
    cb.addEventListener('change', validateTrainingSelection);
});

function validateTrainingSelection() {
    const checked = document.querySelectorAll('input[name="training_type"]:checked');
    if (checked.length === 0) {
        trainingHint.textContent = '⚠️ Please select at least one training type.';
        return false;
    }
    trainingHint.textContent = '';
    return true;
}

function getSelectedTrainingTypes() {
    return [...document.querySelectorAll('input[name="training_type"]:checked')].map(cb => cb.value);
}

// ============================================================
// Onboarding form submission
// ============================================================
document.getElementById('onboard-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validateTrainingSelection()) return;

    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    btnText.textContent = 'Initializing Agents...';
    submitBtn.disabled = true;

    const injuries = document.getElementById('injuries').value
        .split(',').map(s => s.trim()).filter(Boolean);

    const reqBody = {
        age:                    parseInt(document.getElementById('age').value),
        weight_kg:              parseFloat(document.getElementById('weight').value),
        target_weight_kg:       parseFloat(document.getElementById('target-weight').value),
        activity_level:         document.getElementById('activity').value,
        primary_goal:           document.getElementById('goal').value,
        experience_level:       document.getElementById('experience').value,
        injuries:               injuries,
        preferred_training_types: getSelectedTrainingTypes()
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
        btnText.textContent = 'Error — Try Again';
        submitBtn.disabled = false;
    }
});

// ============================================================
// Polling
// ============================================================
function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollStatus();
    pollInterval = setInterval(pollStatus, 3500);
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
        updatePlanViewer(data);

        if (data.status === 'completed') clearInterval(pollInterval);
    } catch (err) {
        console.error('Polling error:', err);
    }
}

// ============================================================
// Status Badge
// ============================================================
function updateStatus(status, nextNodes) {
    if (status === 'running') {
        statusBadge.textContent = '⚡ Agents Running';
        statusBadge.className = 'badge badge-running';
        hitlAlert.classList.add('hidden');
    } else if (status === 'paused') {
        statusBadge.textContent = '⏸ Action Required';
        statusBadge.className = 'badge badge-paused';
        hitlAlert.classList.remove('hidden');
    } else if (status === 'completed') {
        statusBadge.textContent = '✅ Plan Ready';
        statusBadge.className = 'badge badge-completed';
        hitlAlert.classList.add('hidden');
        downloadAlert.classList.remove('hidden');
        downloadBtn.href = `/api/download/${currentThreadId}`;
    }
}

// ============================================================
// Senior Coach directives
// ============================================================
function updateDirectives(macro) {
    if (!macro?.specialist_directives) return;
    const dirs = macro.specialist_directives;
    if (!Object.keys(dirs).length) return;
    seniorCoachBox.classList.remove('hidden');
    directivesList.innerHTML = Object.entries(dirs).map(([domain, text]) => `
        <div class="directive-item">
            <span class="directive-domain">🎯 ${domain}</span>
            <span class="directive-text">${text}</span>
        </div>
    `).join('');
}

// ============================================================
// Macro strip
// ============================================================
function updateMacroStrip(macro) {
    if (!macro) return;
    macroStrip.classList.remove('hidden');
    document.querySelector('#macro-cal .macro-val').textContent    = macro.target_calories + ' kcal';
    document.querySelector('#macro-protein .macro-val').textContent = macro.protein_g + 'g';
    document.querySelector('#macro-carbs .macro-val').textContent   = macro.carbs_g + 'g';
    document.querySelector('#macro-fats .macro-val').textContent    = macro.fats_g + 'g';
    document.querySelector('#macro-split .macro-val').textContent   = macro.training_split || '—';
}

// ============================================================
// Validation Logs
// ============================================================
function updateLogs(logs) {
    if (!logs?.length) return;
    logCount.textContent = logs.length;
    logsContainer.innerHTML = '';
    [...logs].reverse().forEach(log => {
        const div = document.createElement('div');
        div.className = `log-item ${log.status}`;
        div.innerHTML = `
            <div class="log-meta">
                <span>${log.domain} — Attempt #${log.attempt}</span>
                <span class="log-status-${log.status.toLowerCase()}">${log.status}</span>
            </div>
            ${log.feedback ? `<div class="log-feedback">${log.feedback}</div>` : ''}
        `;
        logsContainer.appendChild(div);
    });
}

// ============================================================
// Tracking Coach Panel
// ============================================================
function updateTrackingPanel(tracking) {
    if (!tracking) return;
    trackingPanel.classList.remove('hidden');
    const fill = (id, items) => {
        document.getElementById(id).innerHTML = (items || []).map(i => `<li>${i}</li>`).join('');
    };
    fill('tips-list',       tracking.implementation_tips);
    fill('metrics-list',    tracking.weekly_checkin_metrics);
    fill('milestones-list', tracking.milestone_targets);
    fill('warnings-list',   tracking.red_flag_warnings);
    document.getElementById('coach-notes-text').textContent = tracking.coach_notes || '';
}

// ============================================================
// Full Plan Viewer
// ============================================================
let activePlanTab    = 'workout';
let activeDomainTab  = null;
let planData         = null;

function updatePlanViewer(data) {
    const fp = data.fitness_plan;
    const np = data.nutrition_plan;

    // Only render when there's something to show
    const hasFitness = fp && (
        (fp.gym_sessions?.length) ||
        (fp.yoga_sessions?.length) ||
        (fp.calisthenics_sessions?.length)
    );
    const hasNutrition = !!np;

    if (!hasFitness && !hasNutrition) return;

    // Avoid expensive re-render if data hasn't changed
    const hash = JSON.stringify({fp, np});
    if (hash === lastPlanHash) return;
    lastPlanHash = hash;

    planData = { fp, np };
    planViewer.classList.remove('hidden');

    renderPlanTabs(hasFitness, hasNutrition);
}

function renderPlanTabs(hasFitness, hasNutrition) {
    // Plan-level tabs (Workout / Nutrition)
    planTabs.querySelectorAll('.plan-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            activePlanTab = btn.dataset.tab;
            planTabs.querySelectorAll('.plan-tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-workout').classList.toggle('hidden', activePlanTab !== 'workout');
            document.getElementById('tab-nutrition').classList.toggle('hidden', activePlanTab !== 'nutrition');
        });
    });

    renderWorkoutTab(planData.fp);
    renderNutritionTab(planData.np);
}

// ---- Workout Tab ----
function renderWorkoutTab(fp) {
    if (!fp) return;

    const domains = [];
    if (fp.gym_sessions?.length)             domains.push({ key: 'Gym',          sessions: fp.gym_sessions,             css: 'gym',  icon: '🏋️' });
    if (fp.yoga_sessions?.length)            domains.push({ key: 'Yoga',         sessions: fp.yoga_sessions,            css: 'yoga', icon: '🧘' });
    if (fp.calisthenics_sessions?.length)    domains.push({ key: 'Calisthenics', sessions: fp.calisthenics_sessions,    css: 'cali', icon: '🤸' });

    if (!domains.length) return;

    // Build domain tabs
    domainTabs.innerHTML = domains.map(d => `
        <button class="domain-tab" data-domain="${d.key}">${d.icon} ${d.key}</button>
    `).join('');

    const firstDomain = domains[0].key;
    activeDomainTab = firstDomain;

    domainTabs.querySelectorAll('.domain-tab').forEach(btn => {
        if (btn.dataset.domain === firstDomain) btn.classList.add(`active-${domains[0].css}`);
        btn.addEventListener('click', () => {
            activeDomainTab = btn.dataset.domain;
            domainTabs.querySelectorAll('.domain-tab').forEach(b => b.className = 'domain-tab');
            const d = domains.find(d => d.key === activeDomainTab);
            btn.classList.add(`active-${d.css}`);
            renderSessionList(d);
        });
    });

    renderSessionList(domains[0]);
}

function renderSessionList(domain) {
    domainContent.innerHTML = '';
    domainContent.className = `session-list domain-${domain.css}`;

    domain.sessions.forEach((session, si) => {
        const card = document.createElement('div');
        card.className = 'session-card';

        const exCount = session.exercises?.length || 0;
        const headerHtml = `
            <div class="session-header" id="sh-${si}">
                <span class="session-day">${session.day || '—'}</span>
                <span class="session-focus">${session.focus || ''}</span>
                <span class="session-meta">
                    <span>⏱ ${session.duration_mins || '?'} min</span>
                    <span>📋 ${exCount} exercise${exCount !== 1 ? 's' : ''}</span>
                </span>
                <span class="session-chevron">▼</span>
            </div>
        `;

        const exRows = (session.exercises || []).map(ex => buildExerciseRow(ex)).join('');
        const exListHtml = exCount > 0 ? `
            <div class="exercise-list" id="el-${si}" style="display:none">
                <div class="exercise-header">
                    <span>Exercise</span>
                    <span style="text-align:center">Sets</span>
                    <span style="text-align:center">Reps</span>
                    <span style="text-align:center">Rest</span>
                    <span style="text-align:center">W/U</span>
                    <span style="text-align:center">Tempo</span>
                    <span>Muscles / Goal</span>
                    <span style="text-align:right">Demo</span>
                </div>
                ${exRows}
            </div>
        ` : '';

        card.innerHTML = headerHtml + exListHtml;
        domainContent.appendChild(card);

        // Toggle expand/collapse
        const header = card.querySelector(`#sh-${si}`);
        const exList = card.querySelector(`#el-${si}`);
        if (header && exList) {
            header.addEventListener('click', () => {
                const isOpen = exList.style.display !== 'none';
                exList.style.display = isOpen ? 'none' : 'block';
                header.classList.toggle('open', !isOpen);
            });
        }
    });
}

function buildExerciseRow(ex) {
    const demoBtn = ex.demo_url
        ? `<a class="demo-btn" href="${ex.demo_url}" target="_blank" rel="noopener">▶ Watch</a>`
        : `<span style="color:var(--muted);font-size:0.78rem">—</span>`;

    const notesRow = ex.notes
        ? `<div class="notes-row"><span class="notes-label">📝 Notes:</span>${ex.notes}</div>`
        : '';

    return `
        <div class="exercise-row">
            <div class="ex-name">
                ${ex.name || '—'}
                <small>${ex.muscles_goal || ''}</small>
            </div>
            <div class="ex-sets" style="text-align:center">
                <span class="ex-val">${ex.sets ?? '—'}</span>
                <span class="ex-sub">sets</span>
            </div>
            <div class="ex-reps" style="text-align:center">
                <span class="ex-val">${ex.reps || '—'}</span>
                <span class="ex-sub">reps</span>
            </div>
            <div class="ex-rest" style="text-align:center">
                <span class="ex-val">${ex.rest_seconds ?? '—'}</span>
                <span class="ex-sub">sec</span>
            </div>
            <div class="ex-wu" style="text-align:center">
                <span class="ex-val">${ex.warmup_sets ?? '—'}</span>
                <span class="ex-sub">w/u</span>
            </div>
            <div class="ex-tempo" style="text-align:center">
                <span class="tempo-chip">${ex.tempo || '—'}</span>
            </div>
            <div class="ex-muscles">${ex.muscles_goal || ''}</div>
            <div class="ex-demo">${demoBtn}</div>
        </div>
        ${notesRow}
    `;
}

// ---- Nutrition Tab ----
function renderNutritionTab(np) {
    if (!np) {
        nutritionContent.innerHTML = '<p style="color:var(--muted);padding:20px">Nutrition plan not yet available.</p>';
        return;
    }

    const meals = np.daily_meals || [];
    const totalCal  = meals.reduce((s, m) => s + (m.calories || 0), 0);
    const totalProt = meals.reduce((s, m) => s + (m.protein_g || 0), 0);
    const totalCarb = meals.reduce((s, m) => s + (m.carbs_g || 0), 0);
    const totalFat  = meals.reduce((s, m) => s + (m.fats_g || 0), 0);

    nutritionContent.innerHTML = `
        <div class="meal-list">
            ${meals.map(m => `
                <div class="meal-card">
                    <div class="meal-info">
                        <div class="meal-name">${m.meal_name}</div>
                        <div class="meal-desc">${m.description}</div>
                    </div>
                    <div class="meal-macros">
                        <div class="macro-chip chip-cal">
                            <span class="chip-val">${m.calories}</span>
                            <span class="chip-label">kcal</span>
                        </div>
                        <div class="macro-chip chip-prot">
                            <span class="chip-val">${m.protein_g}g</span>
                            <span class="chip-label">protein</span>
                        </div>
                        <div class="macro-chip chip-carb">
                            <span class="chip-val">${m.carbs_g}g</span>
                            <span class="chip-label">carbs</span>
                        </div>
                        <div class="macro-chip chip-fat">
                            <span class="chip-val">${m.fats_g}g</span>
                            <span class="chip-label">fats</span>
                        </div>
                    </div>
                </div>
            `).join('')}

            <div class="meal-totals">
                <span class="totals-label">📊 Daily Total</span>
                <div class="meal-macros">
                    <div class="macro-chip chip-cal"><span class="chip-val">${totalCal}</span><span class="chip-label">kcal</span></div>
                    <div class="macro-chip chip-prot"><span class="chip-val">${totalProt}g</span><span class="chip-label">protein</span></div>
                    <div class="macro-chip chip-carb"><span class="chip-val">${totalCarb}g</span><span class="chip-label">carbs</span></div>
                    <div class="macro-chip chip-fat"><span class="chip-val">${totalFat}g</span><span class="chip-label">fats</span></div>
                </div>
            </div>

            ${np.hydration_target_L ? `
                <div class="hydration-note">
                    💧 Daily Hydration Target: <strong>${np.hydration_target_L}L</strong>
                </div>
            ` : ''}
        </div>
    `;
}

// ============================================================
// Resume (HITL Approval)
// ============================================================
resumeBtn.addEventListener('click', async () => {
    if (!currentThreadId) return;
    resumeBtn.textContent = '⏳ Resuming...';
    resumeBtn.disabled = true;
    try {
        await fetch(`/api/resume/${currentThreadId}`, { method: 'POST' });
        setTimeout(() => { resumeBtn.innerHTML = '✅ Approve & Resume'; resumeBtn.disabled = false; }, 3500);
    } catch {
        resumeBtn.innerHTML = '✅ Approve & Resume';
        resumeBtn.disabled = false;
    }
});
