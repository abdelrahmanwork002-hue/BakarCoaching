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

        if (data.status === 'error') {
            clearInterval(pollInterval);
            statusBadge.textContent = '❌ Error';
            statusBadge.className = 'badge badge-paused';
            hitlAlert.classList.add('hidden');
            // Show a friendly error panel
            const errDiv = document.createElement('div');
            errDiv.className = 'alert-panel alert-warn';
            errDiv.innerHTML = `
                <div class="alert-icon">⚠️</div>
                <div class="alert-body">
                    <strong>Agent Error — Please Try Again</strong>
                    <p style="font-size:0.8rem;margin-top:6px;word-break:break-word;opacity:0.7">${data.message || 'An unexpected error occurred.'}</p>
                </div>
                <button onclick="location.reload()" class="primary-btn" style="width:auto">🔄 Restart</button>
            `;
            dashboardSection.prepend(errDiv);
            return;
        }

        if (data.status === 'not_found') return;

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


// ============================================================
// EXERCISE LIBRARY & WEB SEARCH TAB CONTROL
// ============================================================

const navBtnCoaching = document.getElementById('nav-btn-coaching');
const navBtnLibrary  = document.getElementById('nav-btn-library');
const librarySection = document.getElementById('library-section');

let exerciseLibrary = [];

navBtnCoaching.addEventListener('click', () => {
    navBtnCoaching.classList.add('active');
    navBtnLibrary.classList.remove('active');
    librarySection.classList.add('hidden');
    
    // Restore the correct coaching section depending on whether we onboarded
    if (currentThreadId) {
        dashboardSection.classList.remove('hidden');
    } else {
        onboardSection.classList.remove('hidden');
    }
});

navBtnLibrary.addEventListener('click', () => {
    navBtnLibrary.classList.add('active');
    navBtnCoaching.classList.remove('active');
    librarySection.classList.remove('hidden');
    
    // Hide onboarding and dashboard sections
    onboardSection.classList.add('hidden');
    dashboardSection.classList.add('hidden');
    
    // Load the exercise library
    fetchLibrary();
});

// ============================================================
// LOAD AND RENDER EXERCISE LIBRARY
// ============================================================

async function fetchLibrary() {
    try {
        const res = await fetch('/api/exercises');
        const data = await res.json();
        if (data.status === 'success') {
            exerciseLibrary = data.exercises;
            renderLibrary();
        }
    } catch (err) {
        console.error('Error fetching exercise library:', err);
    }
}

function renderLibrary() {
    const grid = document.getElementById('exercises-grid-container');
    const filterType = document.getElementById('filter-type').value;
    const filterMuscle = document.getElementById('filter-muscle').value;
    const filterLevel = document.getElementById('filter-level').value;
    const filterText = document.getElementById('filter-text').value.toLowerCase();
    
    grid.innerHTML = '';
    
    const filtered = exerciseLibrary.filter(ex => {
        if (filterType && !ex.training_types.includes(filterType)) return false;
        if (filterMuscle && !ex.targeted_muscles.includes(filterMuscle)) return false;
        if (filterLevel && !ex.levels.includes(filterLevel)) return false;
        if (filterText && !ex.name.toLowerCase().includes(filterText) && !ex.description.toLowerCase().includes(filterText)) return false;
        return true;
    });
    
    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="glass-panel" style="grid-column:1/-1;text-align:center;color:var(--muted);padding:40px;">
                🔍 No exercises match your filters. Use the search bar above to scrape and add new ones!
            </div>
        `;
        return;
    }
    
    filtered.forEach(ex => {
        const card = document.createElement('div');
        card.className = 'exercise-card';
        
        // Level badge CSS class
        let levelClass = 'level-beginner';
        if (ex.levels.includes('Advanced')) {
            levelClass = 'level-advanced';
        } else if (ex.levels.includes('Intermediate')) {
            levelClass = 'level-intermediate';
        }
        
        // Muscles pills
        const musclePillsHtml = ex.targeted_muscles.map(m => {
            const focuses = ex.muscle_focus[m] || [];
            const focusIcons = focuses.map(f => {
                if (f === 'Strength') return `<span class="focus-strength">💪 Strength</span>`;
                if (f === 'Mobility') return `<span class="focus-mobility">🤸 Mobility</span>`;
                return f;
            }).join(' / ');
            return `
                <div class="muscle-pill">
                    <strong>${m}</strong>: ${focusIcons}
                </div>
            `;
        }).join('');
        
        // Progressions html
        const progressionsHtml = ex.next_level_progressions?.length 
            ? `<div class="progression-row" style="margin-top:4px;">➡️ <strong>Next Progressions:</strong> ${ex.next_level_progressions.join(', ')}</div>`
            : '';
            
        // Training Types tags
        const typeTagsHtml = ex.training_types.map(t => `<span class="type-tag ${t}">${t}</span>`).join('');
        
        card.innerHTML = `
            <div class="ex-card-header">
                <div class="ex-card-title">${ex.name}</div>
                <span class="level-badge ${levelClass}">${ex.levels.join(' / ')}</span>
            </div>
            <div class="ex-card-tags">
                ${typeTagsHtml}
            </div>
            <div class="ex-card-desc">${ex.description}</div>
            
            <div class="ex-card-muscles">
                <div class="muscle-list-title">Targeted Muscles & Focus</div>
                <div class="muscle-pills">
                    ${musclePillsHtml}
                </div>
            </div>
            
            ${progressionsHtml}
            
            <div class="ex-card-footer">
                <a class="demo-btn" href="${ex.demo_url}" target="_blank" rel="noopener">▶ Watch Demo Video</a>
            </div>
        `;
        
        grid.appendChild(card);
    });
}

// Add filter event listeners
['filter-type', 'filter-muscle', 'filter-level'].forEach(id => {
    document.getElementById(id).addEventListener('change', renderLibrary);
});
document.getElementById('filter-text').addEventListener('input', renderLibrary);

// ============================================================
// WEB SEARCH TRIGGER (BROWSER SEARCH FLOW)
// ============================================================

const searchForm = document.getElementById('library-search-form');
const searchInput = document.getElementById('library-search-input');
const searchLoader = document.getElementById('search-loader');
const searchBtn = document.getElementById('library-search-btn');

searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = searchInput.value.trim();
    if (!query) return;
    
    // Show loader
    searchLoader.classList.remove('hidden');
    searchBtn.disabled = true;
    searchInput.disabled = true;
    
    try {
        const res = await fetch('/api/exercises/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        const data = await res.json();
        if (data.status === 'success') {
            exerciseLibrary = data.exercises;
            renderLibrary();
            searchInput.value = '';
            
            // Success Message
            const alertText = data.new_exercises.length > 0 
                ? `⚡ Found & Classified ${data.new_exercises.length} new exercises!`
                : `🔍 Search finished. Checked for new exercises.`;
            alert(alertText);
        } else {
            alert('Error running browser search agent: ' + data.detail);
        }
    } catch (err) {
        console.error('Error running web search flow:', err);
        alert('Failed to connect to search agent.');
    } finally {
        searchLoader.classList.add('hidden');
        searchBtn.disabled = false;
        searchInput.disabled = false;
    }
});

// ============================================================
// MANUAL ADD EXERCISE FORM DYNAMIC FIELDS & SETUP
// ============================================================

const toggleAddBtn = document.getElementById('toggle-add-form-btn');
const manualPanel = document.getElementById('manual-exercise-panel');
const cancelAddBtn = document.getElementById('cancel-add-btn');
const manualForm = document.getElementById('manual-exercise-form');

toggleAddBtn.addEventListener('click', () => {
    manualPanel.classList.toggle('hidden');
    if (!manualPanel.classList.contains('hidden')) {
        setupMuscleSelectorGrid();
        manualPanel.scrollIntoView({ behavior: 'smooth' });
    }
});

cancelAddBtn.addEventListener('click', () => {
    manualPanel.classList.add('hidden');
    manualForm.reset();
});

const STANDARD_MUSCLES = [
    "Chest", "Back", "Shoulders", "Quads", "Hamstrings", 
    "Glutes", "Calves", "Biceps", "Triceps", "Core", 
    "Wrists/Forearms", "Hips"
];

function setupMuscleSelectorGrid() {
    const container = document.getElementById('muscle-focus-selector-grid');
    container.innerHTML = '';
    
    STANDARD_MUSCLES.forEach(muscle => {
        const div = document.createElement('div');
        div.className = 'muscle-focus-selector-item';
        div.id = `muscle-item-${muscle.replace('/', '-')}`;
        
        div.innerHTML = `
            <label class="muscle-checkbox-row">
                <input type="checkbox" name="manual_muscles" value="${muscle}" class="muscle-cb">
                <span>${muscle}</span>
            </label>
            <div class="focus-options-row">
                <label class="focus-option">
                    <input type="checkbox" name="focus_${muscle}_strength" value="Strength" checked>
                    <span>Strength</span>
                </label>
                <label class="focus-option">
                    <input type="checkbox" name="focus_${muscle}_mobility" value="Mobility">
                    <span>Mobility</span>
                </label>
            </div>
        `;
        
        // Add event listener to toggle active styles and input status
        const cb = div.querySelector('.muscle-cb');
        cb.addEventListener('change', () => {
            if (cb.checked) {
                div.classList.add('selected');
            } else {
                div.classList.remove('selected');
            }
        });
        
        container.appendChild(div);
    });
}

// Manual Form Submit
manualForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('manual-ex-name').value.trim();
    const demoUrl = document.getElementById('manual-ex-demo').value.trim();
    const description = document.getElementById('manual-ex-desc').value.trim();
    
    // Training Types (Cali, Gym, Yoga)
    const trainingTypes = [...document.querySelectorAll('input[name="manual_training_types"]:checked')].map(cb => cb.value);
    
    // Levels (Beginner, Intermediate, Advanced)
    const levels = [...document.querySelectorAll('input[name="manual_levels"]:checked')].map(cb => cb.value);
    
    // Progressions
    const progressionsRaw = document.getElementById('manual-ex-progressions').value;
    const next_level_progressions = progressionsRaw 
        ? progressionsRaw.split(',').map(s => s.trim()).filter(Boolean)
        : [];
        
    // Targeted Muscles & Focuses
    const selectedMuscles = [...document.querySelectorAll('input[name="manual_muscles"]:checked')].map(cb => cb.value);
    if (selectedMuscles.length === 0) {
        alert('⚠️ Please select at least one targeted muscle.');
        return;
    }
    
    const muscleFocus = {};
    selectedMuscles.forEach(muscle => {
        const focuses = [];
        const isStrength = document.querySelector(`input[name="focus_${muscle}_strength"]`).checked;
        const isMobility = document.querySelector(`input[name="focus_${muscle}_mobility"]`).checked;
        
        if (isStrength) focuses.push('Strength');
        if (isMobility) focuses.push('Mobility');
        
        if (focuses.length === 0) {
            focuses.push('Strength'); // fallback
        }
        
        muscleFocus[muscle] = focuses;
    });
    
    const reqBody = {
        name,
        description,
        targeted_muscles: selectedMuscles,
        muscle_focus: muscleFocus,
        training_types: trainingTypes,
        demo_url: demoUrl,
        levels,
        next_level_progressions
    };
    
    try {
        const res = await fetch('/api/exercises', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reqBody)
        });
        
        const data = await res.json();
        if (data.status === 'success') {
            exerciseLibrary = data.exercises;
            renderLibrary();
            manualPanel.classList.add('hidden');
            manualForm.reset();
            alert('🎉 Custom exercise added successfully!');
        } else {
            alert('Error adding exercise: ' + data.detail);
        }
    } catch (err) {
        console.error('Error saving manual exercise:', err);
        alert('Failed to connect to server to save exercise.');
    }
});
