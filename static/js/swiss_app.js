
// --- DATA STORE ---
const state = {
    step: 1,
    isAuthenticated: false,
    channels: [],
    selectedChannels: [],
    messages: [], // All fetched messages
    selectedMessages: [], // Messages selected for processing
    processedData: {}, // Map of ID -> JSON Result
    refineryStage: 'BULK', // BULK or REFINEMENT
    masterPrompt: "",
    revisionPrompt: "",
    masterPrompt: "",
    revisionPrompt: "",
    failedItems: [], // Items that need refinement
    filters: {} // Map of column -> filter string
};

// --- UTILS ---
const getEl = (id) => document.getElementById(id);

const showToast = (msg) => {
    const t = getEl('toast');
    const msgEl = getEl('toastMsg');
    if (!t || !msgEl) return;

    msgEl.innerText = msg;
    t.classList.remove('hidden');
    setTimeout(() => t.classList.add('hidden'), 3000);
};

function copyActivePrompt() {
    const promptArea = getEl('activePromptText');
    if (!promptArea || !promptArea.value) {
        showToast("No prompt to copy");
        return;
    }

    navigator.clipboard.writeText(promptArea.value).then(() => {
        showToast("Prompt copied to clipboard!");
    }).catch(err => {
        // Fallback for older browsers
        promptArea.select();
        document.execCommand('copy');
        showToast("Prompt copied!");
    });
}

let loaderInterval = null;

const showLoader = (text, duration, callback) => {
    const l = getEl('globalLoader');
    const bar = getEl('loaderBar');
    const title = getEl('loaderTitle');
    const percent = getEl('loaderPercent');
    const status = getEl('loaderStatus');

    if (!l) return;

    // Reset
    if (loaderInterval) clearInterval(loaderInterval);
    title.innerText = text;
    l.classList.remove('hidden');
    bar.style.transition = "width 0.5s ease-out";
    bar.style.width = "0%";
    percent.innerText = "0%";

    // Randomize ID
    const loaderIdEl = getEl('loaderId');
    if (loaderIdEl) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        const nums = '0123456789';
        const randomId = chars[Math.floor(Math.random() * 26)] + chars[Math.floor(Math.random() * 26)] + '-' + nums[Math.floor(Math.random() * 10)] + nums[Math.floor(Math.random() * 10)];
        loaderIdEl.innerText = randomId;
    }

    // Mode 1: Polling (Real Progress)
    if (duration === 'poll') {
        let stalledCount = 0;
        let lastPercent = 0;

        loaderInterval = setInterval(async () => {
            const res = await apiCall('/api/progress', 'GET');
            if (res) {
                let p = res.percent;
                const s = res.status;

                // Smoothing: Don't jump backwards
                if (p < lastPercent) p = lastPercent;

                // Stalled detection
                if (p === lastPercent && p < 100) {
                    stalledCount++;
                    // If stuck for 3 seconds (6 ticks) at high %, fake it to completion slowly
                    if (stalledCount > 6 && p > 70) {
                        p += 1; // Creep forward
                    }
                } else {
                    stalledCount = 0;
                }

                lastPercent = p;
                if (p > 100) p = 100;

                bar.style.transition = "width 0.5s ease-out";
                bar.style.width = p + "%";
                percent.innerText = Math.floor(p) + "%";
                if (s) status.innerText = s.toUpperCase();
            }
        }, 500);
        return;
    }

    // Mode 2: Indefinite (Spinning / Waiting) - Duration 0
    if (!duration) {
        bar.style.transition = "none"; // Instant reset
        bar.style.width = "100%";
        bar.classList.add("animate-pulse"); // Add pulse if possible, or just solid
        percent.innerText = "BUSY";
        return;
    } else {
        bar.classList.remove("animate-pulse");
    }

    // Mode 3: Fake Progress (Legacy) - Linear
    // Mode 4: Time-based linear (4 min to 99%)
    if (duration === 'auto' || (typeof duration === 'object' && duration.mode === 'auto-continue')) {
        // CRITICAL: Clear any existing interval first to prevent stacking
        if (loaderInterval) clearInterval(loaderInterval);

        bar.style.transition = "width 0.5s linear";
        bar.style.maxWidth = "100%";
        bar.classList.remove("animate-pulse");
        bar.style.opacity = "1";

        const EXPECTED_DURATION_MS = (typeof duration === 'object' && duration.expectedDuration)
            ? duration.expectedDuration
            : 300000; // Default 5 minutes if not specified

        let startTime = Date.now();

        // Support continuing from a starting percentage
        const startPercent = (typeof duration === 'object' && duration.startPercent) ? duration.startPercent : 0;
        const endPercent = 99;
        const range = endPercent - startPercent;

        loaderInterval = setInterval(() => {
            let elapsed = Date.now() - startTime;
            // Progress from startPercent to endPercent over expected duration
            let progress = startPercent + Math.min(range, (elapsed / EXPECTED_DURATION_MS) * range);

            // After expected time, continue creeping very slowly
            if (elapsed > EXPECTED_DURATION_MS) {
                progress = endPercent + ((elapsed - EXPECTED_DURATION_MS) / 60000) * 0.5;
                if (progress > 99.9) progress = 99.9; // Never hit 100
            }

            bar.style.width = progress + "%";
            percent.innerText = Math.floor(progress) + "%";
        }, 500);
        return;
    }

    // Default Legacy Linear
    let progress = 0;
    loaderInterval = setInterval(() => {
        progress += 2;
        bar.style.width = progress + "%";
        percent.innerText = progress + "%";
        if (progress >= 100) {
            clearInterval(loaderInterval);
            setTimeout(() => {
                l.classList.add('hidden');
                if (callback) callback();
            }, 200);
        }
    }, duration ? duration / 50 : 50);
};

const hideLoader = () => {
    const l = getEl('globalLoader');
    if (loaderInterval) clearInterval(loaderInterval);
    if (l) l.classList.add('hidden');
};

const apiCall = async (endpoint, method, body) => {
    try {
        const headers = { 'Content-Type': 'application/json' };
        const response = await fetch(endpoint, {
            method: method,
            headers: headers,
            body: JSON.stringify(body)
        });
        return await response.json();
    } catch (e) {
        console.error(e);
        showToast("API Error: " + e.message);
        return null;
    }
};

// --- INIT ---
window.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
});

async function checkAuth() {
    const res = await apiCall('/api/check_auth', 'GET');
    if (res && res.authorized) {
        state.isAuthenticated = true;
        getEl('authContainer').classList.add('hidden');
        getEl('authSuccess').classList.remove('hidden');
        await loadChannels();
    } else {
        state.isAuthenticated = false;
        // Show auth form
    }
}

// --- CAPPER RECONCILIATION ---
let activeCapperCell = null;

function showCapperSuggestions(cell, msgId, idx, currentName) {
    if (activeCapperCell === cell) return;
    activeCapperCell = cell;

    // Remove existing suggestions
    const existing = document.getElementById('capperSuggestions');
    if (existing) existing.remove();

    // Get match data from state
    let entry = state.processedData[msgId];
    if (!entry) return;
    let row = Array.isArray(entry) ? entry[idx] : entry;
    let matches = row.capper_matches || [];

    const rect = cell.getBoundingClientRect();

    const div = document.createElement('div');
    div.id = 'capperSuggestions';
    div.className = "fixed bg-white shadow-xl border border-gray-200 z-50 rounded-lg overflow-hidden text-xs font-mono w-64 animate-fade-in";
    div.style.top = (rect.bottom + 5) + "px";
    div.style.left = rect.left + "px";

    // Header
    div.innerHTML = `<div class="bg-gray-50 p-2 border-b border-gray-100 font-bold text-gray-400 uppercase tracking-widest flex justify-between items-center">
        <span>Suggestions</span>
        <button onclick="this.parentElement.parentElement.remove(); activeCapperCell=null;" class="hover:text-black">&times;</button>
    </div>`;

    const list = document.createElement('div');
    list.className = "max-h-60 overflow-y-auto";

    // Option 1: Create New
    const createOption = document.createElement('div');
    createOption.className = "p-3 hover:bg-blue-50 cursor-pointer border-b border-gray-100 flex items-center gap-2 group";
    createOption.onclick = async () => {
        const confirmName = currentName.trim();
        if (!confirmName) return;

        // Call API to create
        const res = await apiCall('/api/create_capper', 'POST', { name: confirmName });
        if (res.success) {
            updateRowData(msgId, idx, 'capper_name', confirmName);
            // Mark as verified manually
            row.capper_verified = true;
            renderTable();
            showToast(`Created Capper: ${confirmName}`);
        } else {
            showToast("Error: " + res.error);
        }
        div.remove();
        activeCapperCell = null;
    };
    createOption.innerHTML = `
        <span class="material-icons text-sm text-gray-400 group-hover:text-blue-600">add_circle</span>
        <div>
            <div class="font-bold text-blue-600">Create New</div>
            <div class="text-[10px] text-gray-500">"${currentName}"</div>
        </div>
    `;
    list.appendChild(createOption);

    // Option 2: Matches
    if (matches.length > 0) {
        matches.forEach(m => {
            const el = document.createElement('div');
            el.className = "p-3 hover:bg-green-50 cursor-pointer border-b border-gray-100 flex items-center gap-2";

            let badgeColor = "bg-gray-100 text-gray-500";
            if (m.score === 100) badgeColor = "bg-green-100 text-green-700";
            else if (m.score > 80) badgeColor = "bg-yellow-100 text-yellow-700";
            else badgeColor = "bg-red-100 text-red-700";

            el.innerHTML = `
                <div class="${badgeColor} text-[9px] font-bold px-1.5 py-0.5 rounded">${m.score}%</div>
                <div>
                    <div class="font-bold text-gray-800">${m.name}</div>
                    <div class="text-[9px] text-gray-400">${m.type}</div>
                </div>
            `;
            el.onclick = () => {
                updateRowData(msgId, idx, 'capper_name', m.name);
                row.capper_verified = true; // User validated it
                renderTable();
                div.remove();
                activeCapperCell = null;
            };
            list.appendChild(el);
        });
    } else {
        list.innerHTML += `<div class="p-3 text-gray-400 italic text-center">No fuzzy matches found</div>`;
    }

    div.appendChild(list);
    document.body.appendChild(div);

    // Close on click outside
    setTimeout(() => {
        document.addEventListener('click', function onClick(e) {
            if (!div.contains(e.target) && e.target !== cell) {
                div.remove();
                activeCapperCell = null;
                document.removeEventListener('click', onClick);
            }
        });
    }, 100);
}

// --- INIT ---
async function handleAuth() {
    const btn = getEl('authBtn');
    const otpGroup = getEl('otpGroup');
    const phoneInput = getEl('phoneInput');
    const otpInput = getEl('otpInput');

    if (otpGroup.classList.contains('hidden')) {
        // Step 1: Send Code
        const phone = phoneInput.value;
        if (!phone) { showToast("Enter Phone Number"); return; }

        btn.innerHTML = `<span class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2"></span> SENDING...`;

        const res = await apiCall('/api/send_code', 'POST', { phone: phone });

        if (res && res.status === 'success') {
            otpGroup.classList.remove('hidden');
            phoneInput.disabled = true;
            btn.innerHTML = `<span>Confirm Identity</span> <span class="material-icons text-sm">lock</span>`;
            otpInput.focus();
        } else {
            showToast("Error Sending Code");
            btn.innerText = "Request Access";
        }
    } else {
        // Step 2: Verify
        const code = otpInput.value;
        const passwordInput = getEl('passwordInput');
        const passwordGroup = getEl('passwordGroup');
        const password = passwordInput ? passwordInput.value : '';

        if (!code) { showToast("Enter Code"); return; }

        btn.innerHTML = `VERIFYING...`;

        const res = await apiCall('/api/verify_code', 'POST', { code: code, password: password });

        if (res && (res.status === true || res.status === 'success' || res.status === 'SUCCESS')) {
            getEl('authContainer').classList.add('hidden');
            getEl('authSuccess').classList.remove('hidden');
            state.isAuthenticated = true;
            await loadChannels();
            showToast("System Authenticated");
        } else if (res && res.status === '2FA_REQUIRED') {
            // SHOW 2FA
            showToast("2FA Password Required");
            passwordGroup.classList.remove('hidden');
            passwordInput.focus();
            btn.innerHTML = `<span>Authenticate 2FA</span> <span class="material-icons text-sm">vpn_key</span>`;
        } else {
            showToast("Verification Failed: " + (res.error || "Invalid Code"));
            btn.innerHTML = `<span>Confirm Identity</span> <span class="material-icons text-sm">lock</span>`;
        }
    }
}

async function loadChannels() {
    showLoader("SYNCING FEED SOURCES", "poll");
    const res = await apiCall('/api/get_channels', 'GET');

    // Ensure bar shows 100% for a moment before hiding
    const bar = getEl('loaderBar');
    const percent = getEl('loaderPercent');
    if (bar) bar.style.width = "100%";
    if (percent) percent.innerText = "100%";
    await new Promise(r => setTimeout(r, 400)); // Brief pause at 100%

    hideLoader();

    if (res && Array.isArray(res)) {
        state.channels = res;
        renderChannels(res);
    }
}

function renderChannels(channels) {
    const grid = getEl('channelGrid');
    grid.innerHTML = '';

    channels.forEach(ch => {
        // ch has: id, name, photo
        const name = ch.name || "Unknown";

        // POLISH: Semantic Button
        const el = document.createElement('button');
        el.className = `grid-item w-full text-left p-6 flex flex-col justify-between cursor-pointer transition-all duration-300 hover:scale-[1.02] group relative select-none h-48 overflow-hidden bg-white focus:outline-none focus:ring-4 focus:ring-blue-500 focus:ring-inset`;
        el.onclick = () => toggleChannel(el, ch.id);
        el.setAttribute('aria-label', `Select Channel ${name}`);

        // Background Image Logic
        const bgStyle = ch.photo
            ? `background-image: url('${ch.photo}'); background-size: cover; background-position: center;`
            : ``;

        // Initials or Icon (only if no photo, or overlay)
        const initials = name.substring(0, 2).toUpperCase();

        // Inner Content
        const overlayClass = ch.photo ? 'bg-black/40 group-hover:bg-black/20' : 'bg-transparent';
        const textClass = ch.photo ? 'text-white' : 'text-black';
        const subTextClass = ch.photo ? 'text-gray-200' : 'text-gray-400';
        const borderClass = ch.photo ? 'border-transparent' : 'border-gray-200';

        el.style.cssText = bgStyle;

        el.innerHTML = `
            <div class="absolute inset-0 ${overlayClass} transition-all duration-300 z-0 ch-overlay"></div>
            
            <div class="flex justify-between items-start z-10 relative">
                ${!ch.photo ? `<div class="w-8 h-8 bg-gray-100 rounded-none flex items-center justify-center font-bold text-xs border ${borderClass}">${initials}</div>` : `<div class="w-8 h-8"></div>`}
                <div class="w-6 h-6 border-2 border-white/50 ch-check flex items-center justify-center bg-black/20 backdrop-blur-sm transition-all duration-200"></div>
            </div>
            
            <div class="z-10 relative">
                <div class="font-bold text-sm uppercase tracking-tight mb-1 truncate ${textClass} drop-shadow-md" title="${name}">${name}</div>
                <div class="font-mono text-[10px] ${subTextClass} uppercase flex gap-2 drop-shadow-sm">
                    <span>${ch.id}</span>
                </div>
            </div>
            
            <div class="absolute top-0 left-0 z-30 ch-selected-badge hidden">
                <div class="bg-blue-600 text-white text-[10px] font-bold px-2 py-1 uppercase">Selected</div>
            </div>
        `;
        grid.appendChild(el);
    });
}

function toggleChannel(el, id) {
    const checkbox = el.querySelector('.ch-check');
    const overlay = el.querySelector('.ch-overlay');
    const badge = el.querySelector('.ch-selected-badge');

    if (state.selectedChannels.includes(id)) {
        // Deselect
        state.selectedChannels = state.selectedChannels.filter(x => x !== id);
        checkbox.innerHTML = '';
        checkbox.classList.remove('bg-blue-600', 'border-blue-600', 'scale-110');
        checkbox.classList.add('border-white/50', 'bg-black/20');
        overlay.classList.remove('bg-black/60');
        overlay.classList.add('bg-black/40');
        if (badge) badge.classList.add('hidden');
    } else {
        // Select
        state.selectedChannels.push(id);
        checkbox.innerHTML = '<span class="material-icons text-[14px] text-white">check</span>';
        checkbox.classList.remove('border-white/50', 'bg-black/20');
        checkbox.classList.add('bg-blue-600', 'border-blue-600', 'scale-110');
        overlay.classList.remove('bg-black/40');
        overlay.classList.add('bg-black/60');
        if (badge) badge.classList.remove('hidden');
    }

    const btn = getEl('fetchBtn');
    const btnText = btn.querySelector('span');
    btnText.innerText = state.selectedChannels.length > 0 ? `Fetch Data (${state.selectedChannels.length})` : "Initialize Data Fetch";

    if (state.selectedChannels.length > 0) {
        btn.disabled = false;
        btn.classList.remove('cursor-not-allowed', 'bg-gray-50', 'text-gray-200', 'bg-white', 'text-black');
        btn.classList.add('bg-black', 'text-white');
    } else {
        btn.disabled = true;
        btn.classList.add('cursor-not-allowed', 'bg-gray-50', 'text-gray-200');
        btn.classList.remove('bg-black', 'text-white', 'bg-white', 'text-black');
    }
}

async function startFetch() {
    if (state.selectedChannels.length === 0) return;

    const dateVal = document.querySelector('input[type="date"]').value;

    showLoader("ACQUIRING DATA STREAMS", "poll");

    const res = await apiCall('/api/fetch_messages', 'POST', {
        channel_id: state.selectedChannels,
        date: dateVal || null
    });

    hideLoader();

    if (res && Array.isArray(res)) {
        state.messages = res;
        changeStep(2);
        renderMessages();
    } else {
        showToast("No messages found");
    }
}

// --- NAVIGATION ---
function changeStep(n) {
    state.step = n;
    // Hide all pages
    [1, 2, 3, 4].forEach(i => {
        const p = getEl('page-' + i);
        if (p) p.classList.add('hidden');

        const ind = getEl('step-' + i + '-ind');
        if (ind) {
            if (i <= n) ind.classList.replace('bg-gray-200', 'bg-black');
            else ind.classList.replace('bg-black', 'bg-gray-200');
        }
    });
    // Show target
    const target = getEl('page-' + n);
    if (target) target.classList.remove('hidden');

    // Polish: Reset scroll
    window.scrollTo(0, 0);
}

// --- NAVIGATION ---

// Simple markdown to HTML parser
function parseMarkdown(text) {
    if (!text) return '';
    return text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')  // **bold**
        .replace(/\*(.+?)\*/g, '<em>$1</em>')              // *italic*
        .replace(/__(.+?)__/g, '<strong>$1</strong>')      // __bold__
        .replace(/_(.+?)_/g, '<em>$1</em>')                // _italic_
        .replace(/`(.+?)`/g, '<code class="bg-gray-100 px-1 text-xs">$1</code>')  // `code`
        .replace(/\n/g, '<br>');                           // newlines
}

function renderMessages() {
    const grid = getEl('messageGrid');
    grid.innerHTML = ''; // Clear
    currentRenderIdx = 0;

    // Sort messages
    sortedMsgCache = [...state.messages].sort((a, b) => {
        return (b.date || '').localeCompare(a.date || '');
    });

    // Default Selection
    state.selectedMessages = [...state.messages];
    getEl('selectionCount').innerText = state.selectedMessages.length;

    // Create Sentinel for infinite scroll
    const sentinel = document.createElement('div');
    sentinel.id = 'gridSentinel';
    sentinel.className = 'col-span-full h-8 w-full';
    grid.appendChild(sentinel);

    // Setup Observer
    if (msgObserver) msgObserver.disconnect();

    msgObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            renderNextBatch();
        }
    }, { root: grid, rootMargin: '400px' });

    msgObserver.observe(sentinel);

    // Initial Batch
    renderNextBatch();
}

function toggleMessage(el, msg) {
    const checkbox = el.querySelector('.msg-check');
    const image = el.querySelector('.msg-image');
    const idText = el.querySelector('.msg-id');
    const exists = state.selectedMessages.find(m => m.id === msg.id);

    if (exists) {
        // Deselect
        state.selectedMessages = state.selectedMessages.filter(m => m.id !== msg.id);
        checkbox.innerHTML = '';
        checkbox.classList.remove('bg-blue-600', 'border-blue-600', 'scale-110');
        checkbox.classList.add('border-gray-300');
        if (image) image.classList.add('grayscale');
        if (idText) {
            idText.classList.remove('text-blue-600');
            idText.classList.add('text-gray-300');
        }
    } else {
        // Select
        state.selectedMessages.push(msg);
        checkbox.innerHTML = '<span class="material-icons text-[12px] text-white">check</span>';
        checkbox.classList.remove('border-gray-300');
        checkbox.classList.add('bg-blue-600', 'border-blue-600', 'scale-110');
        if (image) image.classList.remove('grayscale');
        if (idText) {
            idText.classList.remove('text-gray-300');
            idText.classList.add('text-blue-600');
        }
    }
    getEl('selectionCount').innerText = state.selectedMessages.length;
}

// --- STEP 3: REFINERY (AI) ---

// --- STEP 3: REFINERY (AI - 2 STAGE) ---


async function runAutoPilot() {
    if (state.selectedMessages.length === 0) {
        showToast("No Data Selected");
        return;
    }

    // Show loader and manually control bar (0% to 20% during prompt gen)
    const loader = getEl('globalLoader');
    const bar = getEl('loaderBar');
    const percent = getEl('loaderPercent');
    const title = getEl('loaderTitle');
    const status = getEl('loaderStatus');

    if (loader) loader.classList.remove('hidden');
    if (loaderInterval) clearInterval(loaderInterval);
    if (bar) { bar.style.width = "0%"; bar.style.transition = "width 3s ease-out"; }
    if (percent) percent.innerText = "0%";
    if (title) title.innerText = "AUTO-PILOT: ANALYZING DATA";
    if (status) status.innerText = "GENERATING PROMPT";

    // Randomize ID
    const loaderIdEl = getEl('loaderId');
    if (loaderIdEl) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        const nums = '0123456789';
        const randomId = chars[Math.floor(Math.random() * 26)] + chars[Math.floor(Math.random() * 26)] + '-' + nums[Math.floor(Math.random() * 10)] + nums[Math.floor(Math.random() * 10)];
        loaderIdEl.innerText = randomId;
    }

    // Animate to 5% gradually
    setTimeout(() => {
        if (bar) bar.style.width = "5%";
        if (percent) percent.innerText = "5%";
    }, 100);

    // Reset State
    state.refineryStage = 'BULK';
    state.processedData = {};
    state.failedItems = [];

    try {
        const resPrompt = await apiCall('/api/generate_prompt', 'POST', {
            messages: state.selectedMessages,
            watermark: ""
        });

        if (!resPrompt || !resPrompt.master_prompt) {
            hideLoader();
            showToast("Failed to generate prompt");
            return;
        }

        const prompt = resPrompt.master_prompt;

        // Set bar to 20% before switching to AI phase
        // IMPORTANT: Clear any existing polling interval first
        if (loaderInterval) {
            clearInterval(loaderInterval);
            loaderInterval = null;
        }

        if (bar) bar.style.width = "20%";
        if (percent) percent.innerText = "20%";
        if (title) title.innerText = "AUTO-PILOT: EXTRACTING PICKS";
        if (status) status.innerText = "AI PROCESSING";

        // 2. Execute AI (With Backup Fallback) - 20% to 99%
        // Dynamic duration: 3s per item + 5s overhead
        const itemCount = state.selectedMessages.length || 1;
        const dynamicDuration = (itemCount * 3000) + 5000;

        // Use auto-continue mode starting from 20%
        // Note: showLoader will set up its own interval, no polling
        showLoader("AUTO-PILOT: EXTRACTING PICKS", {
            mode: 'auto-continue',
            startPercent: 20,
            expectedDuration: dynamicDuration
        });

        const models = [
            'mistralai/devstral-2512:free',
            'tngtech/deepseek-r1t2-chimera:free'
        ];

        let success = false;
        let resultJson = null;

        for (let i = 0; i < models.length; i++) {
            const model = models[i];
            if (i > 0) {
                if (title) title.innerText = "AUTO-PILOT: RETRYING WITH BACKUP";
                if (status) status.innerText = "FALLBACK MODEL";
            }

            try {
                const resAI = await apiCall('/api/ai_fill', 'POST', {
                    prompt: prompt,
                    model: model
                });

                console.log(`[AutoPilot] Model ${model} response:`, resAI);

                if (resAI && resAI.error) {
                    console.error(`[AutoPilot] API Error: ${resAI.error}`);
                    continue; // Try next model
                }

                if (resAI && (resAI.result !== undefined)) {
                    resultJson = resAI.result;
                    success = true;
                    break;
                }
            } catch (e) {
                console.error(`Auto-Pilot Model ${model} failed`, e);
            }
        }

        if (!success || !resultJson) {
            hideLoader();
            console.error('[AutoPilot] All models failed. Last result:', resultJson);
            showToast("Auto-Pilot Failed: AI Error (check console)");
            return;
        }

        // 3. Process & Validate
        if (title) title.innerText = "AUTO-PILOT: VALIDATING RESULTS";
        if (status) status.innerText = "PROCESSING DATA";
        if (bar) bar.style.width = "95%";
        if (percent) percent.innerText = "95%";

        // Map to State (Headless version of processBulkResponse)
        if (Array.isArray(resultJson)) {
            resultJson.forEach(item => {
                if (item.message_id) {
                    state.processedData[item.message_id] = item;
                }
            });
        }

        // Process results, then update bar to 80% before grading starts
        if (bar) bar.style.width = "80%";
        if (percent) percent.innerText = "80%";
        if (title) title.innerText = "AUTO-PILOT: GRADING";

        // 4. Finalize (don't hide loader - let grading continue smoothly)
        finalizeBatch(); // Triggers auto-grade which continues the bar

    } catch (error) {
        hideLoader();
        console.error(error);
        showToast("Auto-Pilot System Error");
    }
}

async function initRefinery() {
    if (state.selectedMessages.length === 0) {
        showToast("No Data Selected");
        return;
    }

    changeStep(3);

    // Reset State
    state.refineryStage = 'BULK';
    state.processedData = {};
    state.failedItems = [];
    state.masterPrompt = "";
    state.revisionPrompt = "";

    // UI Updates
    updateRefineryCounts();
    renderRefineryUI();

    // Call API to prepare messages (OCR logic) and get MASTER PROMPT
    showLoader("PREPARING INTELLIGENCE", "poll");

    const res = await apiCall('/api/generate_prompt', 'POST', {
        messages: state.selectedMessages,
        watermark: ""
    });

    hideLoader();

    if (res && res.updated_messages) {
        state.selectedMessages = res.updated_messages;
        if (res.master_prompt) {
            state.masterPrompt = res.master_prompt;
            getEl('activePromptText').value = res.master_prompt;
        }
    }

    renderRefineryUI();
}

// --- AUTO REVIEW (AI) ---
let pendingReviewChanges = [];

async function runAutoReview() {
    // 1. Gather data
    let picks = [];
    const msgMap = {};
    state.messages.forEach(m => msgMap[m.id] = m);

    // ProcessedData values can be arrays (split picks) or objects
    Object.values(state.processedData).forEach(entry => {
        if (Array.isArray(entry)) {
            entry.forEach(p => {
                const m = msgMap[p.message_id];
                picks.push({
                    ...p,
                    original_text: m ? ((m.text || "") + "\n" + (m.ocr_text || "")) : ""
                });
            });
        } else {
            const m = msgMap[entry.message_id];
            picks.push({
                ...entry,
                original_text: m ? ((m.text || "") + "\n" + (m.ocr_text || "")) : ""
            });
        }
    });

    if (picks.length === 0) { showToast("No picks to review"); return; }

    showLoader("AI ANALYST REVIEWING", "auto");

    const res = await apiCall('/api/auto_review', 'POST', { picks: picks });

    hideLoader();

    if (res && res.changes && res.changes.length > 0) {
        pendingReviewChanges = res.changes;
        renderReviewModal(res.changes);
    } else {
        showToast("AI found no issues.");
    }
}

function renderReviewModal(changes) {
    const modal = getEl('reviewModal');
    const tbody = getEl('reviewTableBody');
    const count = getEl('reviewChangeCount');

    if (!modal || !tbody) return;

    tbody.innerHTML = '';
    count.innerText = changes.length;

    changes.forEach(c => {
        const tr = document.createElement('tr');
        const isDelete = c.field === 'DELETE';
        tr.className = isDelete
            ? "bg-red-50 hover:bg-red-100 transition-colors"
            : "hover:bg-purple-50 transition-colors";

        if (isDelete) {
            tr.innerHTML = `
                <td class="p-3 border-b border-red-200 font-bold text-red-600 align-top">${c.id}</td>
                <td class="p-3 border-b border-red-200 font-bold text-red-600 align-top uppercase">
                    <span class="material-icons text-sm align-middle mr-1">delete</span>DELETE
                </td>
                <td class="p-3 border-b border-red-200 text-gray-400 align-top" colspan="2">Item will be removed</td>
                <td class="p-3 border-b border-red-200 italic text-red-500 text-[10px] align-top">${c.reason}</td>
            `;
        } else {
            tr.innerHTML = `
                <td class="p-3 border-b border-gray-100 font-bold text-gray-400 align-top">${c.id}</td>
                <td class="p-3 border-b border-gray-100 font-bold text-blue-600 align-top">${c.field}</td>
                <td class="p-3 border-b border-gray-100 text-red-400 line-through decoration-red-400 align-top">${c.old}</td>
                <td class="p-3 border-b border-gray-100 text-green-600 font-bold bg-green-50/50 align-top">${c.new}</td>
                <td class="p-3 border-b border-gray-100 italic text-gray-500 text-[10px] align-top">${c.reason}</td>
            `;
        }
        tbody.appendChild(tr);
    });

    modal.classList.remove('hidden');
}

function closeReviewModal() {
    const modal = getEl('reviewModal');
    if (modal) modal.classList.add('hidden');
    pendingReviewChanges = [];
}

function applyReviewChanges() {
    let appliedCount = 0;
    let deletedCount = 0;

    // First pass: handle deletions
    const toDelete = pendingReviewChanges.filter(c => c.field === 'DELETE');
    toDelete.forEach(c => {
        if (state.processedData[c.id]) {
            delete state.processedData[c.id];
            deletedCount++;
        }
    });

    // Second pass: handle edits (skip deleted items)
    pendingReviewChanges.filter(c => c.field !== 'DELETE').forEach(c => {
        let entry = state.processedData[c.id];
        if (entry) {
            if (Array.isArray(entry)) {
                entry.forEach(sub => {
                    if (String(sub[c.field]).trim() === String(c.old).trim() || c.old === 'Unknown') {
                        sub[c.field] = c.new;
                        appliedCount++;
                    }
                });
            } else {
                if (String(entry[c.field]).trim() === String(c.old).trim() || c.old === 'Unknown') {
                    entry[c.field] = c.new;
                    appliedCount++;
                }
            }
        }
    });

    renderTable();
    closeReviewModal();

    let msg = '';
    if (appliedCount > 0) msg += `${appliedCount} corrections`;
    if (deletedCount > 0) msg += (msg ? ', ' : '') + `${deletedCount} deletions`;
    showToast(`Applied: ${msg || 'No changes'}`);
}

function updateRefineryCounts() {
    const total = state.selectedMessages.length;
    let done = 0;

    // Count successful items in processedData
    Object.values(state.processedData).forEach(item => {
        if (item && !item.error) done++;
    });

    getEl('pendingCount').innerText = total - done;
    getEl('completedCount').innerText = done;

    // Update List Status
    renderRefineryQueue();
}

function renderRefineryQueue() {
    const list = getEl('aiQueueList');
    list.innerHTML = '';

    // Stage 1: Bulk Processing
    const stage1Complete = Object.keys(state.processedData).length > 0;
    const stage1Active = state.refineryStage === 'BULK';

    const stage1El = document.createElement('div');
    stage1El.className = `p-5 border-b border-gray-200 cursor-pointer transition-all border-l-4 ${stage1Active ? 'bg-white border-l-black' : stage1Complete ? 'bg-white border-l-green-500' : 'bg-gray-50 border-l-transparent hover:bg-gray-100'}`;

    let stage1Icon = '<span class="w-6 h-6 border-2 border-gray-300 rounded-full flex items-center justify-center text-gray-400 font-bold text-xs">1</span>';
    if (stage1Complete) {
        stage1Icon = '<span class="material-icons text-green-600 text-xl">check_circle</span>';
    } else if (stage1Active) {
        stage1Icon = '<span class="w-6 h-6 bg-black text-white rounded-full flex items-center justify-center font-bold text-xs animate-pulse">1</span>';
    }

    stage1El.innerHTML = `
        <div class="flex items-center gap-3">
            ${stage1Icon}
            <div class="flex-grow">
                <div class="font-bold text-sm ${stage1Active ? 'text-black' : stage1Complete ? 'text-green-700' : 'text-gray-500'}">Bulk Processing</div>
                <div class="text-[10px] text-gray-500 mt-0.5 font-mono uppercase tracking-tight">${state.selectedMessages.length} messages → Master Prompt</div>
            </div>
        </div>
        ${stage1Complete ? `<div class="mt-2 text-[10px] text-gray-400 pl-9 font-mono uppercase tracking-tight">${Object.keys(state.processedData).length} picks extracted</div>` : ''}
    `;
    list.appendChild(stage1El);

    // Stage 2: Refinement Pass
    const stage2Active = state.refineryStage === 'REFINEMENT';
    const stage2Complete = state.refineryStage === 'COMPLETE' || (stage1Complete && state.failedItems.length === 0);
    const stage2Needed = state.failedItems.length > 0;

    const stage2El = document.createElement('div');

    // Style logic
    let stage2Class = 'bg-gray-50 border-l-transparent opacity-50'; // Default disabled
    if (stage1Complete) {
        if (stage2Active) {
            stage2Class = 'bg-white border-l-black';
        } else if (stage2Complete) {
            stage2Class = 'bg-white border-l-green-500';
        } else {
            // Waiting but stage 1 done? Should be active or complete usually.
            stage2Class = 'bg-gray-50 border-l-transparent hover:bg-gray-100 opacity-100';
        }
    }

    stage2El.className = `p-5 border-b border-gray-200 transition-all border-l-4 ${stage2Class}`;

    let stage2Icon = '<span class="w-6 h-6 border-2 border-gray-300 rounded-full flex items-center justify-center text-gray-400 font-bold text-xs">2</span>';
    if (stage2Complete) {
        stage2Icon = '<span class="material-icons text-green-600 text-xl">check_circle</span>';
    } else if (stage2Active) {
        // Keep orange pulse for warning/fixing context, or switch to black? Mockup is b/w. Let's use orange to highlight "fixing" nature but keep container b/w.
        stage2Icon = '<span class="w-6 h-6 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-xs animate-pulse">2</span>';
    }

    let stage2Status = 'Awaiting Step 1';
    if (stage1Complete && state.failedItems.length === 0) {
        stage2Status = 'No refinement needed';
    } else if (stage2Needed) {
        stage2Status = `${state.failedItems.length} ITEMS NEED FIXING`;
    } else if (stage2Complete) {
        stage2Status = 'All items refined';
    }

    stage2El.innerHTML = `
        <div class="flex items-center gap-3">
            ${stage2Icon}
            <div class="flex-grow">
                <div class="font-bold text-sm ${stage2Active ? 'text-orange-600' : stage2Complete ? 'text-green-700' : 'text-gray-500'}">Refinement Pass</div>
                <div class="text-[10px] text-gray-500 mt-0.5 font-mono uppercase tracking-tight">${stage2Status}</div>
            </div>
        </div>
    `;
    list.appendChild(stage2El);

    // Summary Stats
    const summaryEl = document.createElement('div');
    summaryEl.className = 'p-6 bg-gray-50 border-t border-gray-200 mt-auto';
    summaryEl.innerHTML = `
        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-4">Batch Summary</div>
        <div class="space-y-3">
            <div class="flex justify-between items-center text-xs">
                <span class="text-gray-500">Total Selection</span>
                <span class="font-bold font-mono">${state.selectedMessages.length}</span>
            </div>
            <div class="flex justify-between items-center text-xs">
                <span class="text-gray-500">Successfully Parsed</span>
                <span class="font-bold font-mono text-green-600">${Object.keys(state.processedData).length}</span>
            </div>
        </div>
    `;
    list.appendChild(summaryEl);
}

function renderRefineryUI() {
    const promptArea = getEl('activePromptText');
    const inputArea = getEl('activeJsonInput');
    const status = getEl('jsonStatus');
    const sourceArea = getEl('activeSourceText');

    // Hide item-specific source view (Work Area Re-purposed)
    getEl('aiEmptyState').classList.add('hidden');
    getEl('aiWorkArea').classList.remove('hidden');

    // Setup Validation Button
    const actionBtn = document.querySelector('#aiWorkArea button[onclick="saveAndNext()"]');
    if (actionBtn) {
        actionBtn.onclick = handleStageAction;

        if (state.refineryStage === 'BULK') {
            actionBtn.innerHTML = `<span>Validate Bulk JSON</span> <span class="material-icons text-sm">checklist</span>`;

            // Show Master Prompt
            promptArea.value = state.masterPrompt || "Generating Master Prompt...";
            inputArea.placeholder = "Paste the BULK JSON Array here...";

            // Source Area shows clear Stage 1 instructions
            // Source Area shows clear Stage 1 instructions
            // Source Area shows clear Stage 1 instructions
            sourceArea.innerHTML = `<div class="text-blue-700 font-bold text-xs uppercase tracking-widest mb-1">⚡ STAGE 1: BULK</div>
<div class="leading-none text-[10px] space-y-1">
<div><b>1.</b> Click <span class="font-bold text-blue-600">Auto-Fill</span></div>
<div><b>2.</b> Or paste JSON manually</div>
<div><b>3.</b> Click <span class="bg-black text-white px-1 rounded-sm">Validate</span></div>
</div>
<div class="mt-2 text-[9px] text-gray-400 border-t border-gray-100 pt-1">
Batch: ${state.selectedMessages.length} msgs
</div>`;

            // Show AI Controls
            const aiFooter = getEl('actionFooter');
            const autoFillBtn = getEl('autoFillBtn');
            if (autoFillBtn) autoFillBtn.classList.remove('hidden');

        } else {
            actionBtn.innerHTML = `<span>Merge Revisions</span> <span class="material-icons text-sm">merge</span>`;

            // Show Revision Prompt
            promptArea.value = state.revisionPrompt;
            inputArea.placeholder = "Paste the REVISION JSON Array here...";
            inputArea.value = ""; // Clear previous input

            // Show AI Controls for Refinement too
            const autoFillBtn = getEl('autoFillBtn');
            if (autoFillBtn) {
                autoFillBtn.classList.remove('hidden');
                // Optional: Change text/icon to indicate refinement focus?
                // autoFillBtn.innerHTML = `<span>Fix with AI</span> <span class="material-icons text-sm">auto_fix_high</span>`;
            }

            sourceArea.innerHTML = `<div class="text-orange-600 font-bold text-xs uppercase tracking-widest mb-1">🔧 STAGE 2: REFINEMENT</div>
<div class="leading-none text-[10px] space-y-1">
<div class="font-bold text-orange-700 mb-1">${state.failedItems.length} items to fix</div>
<div><b>1.</b> Click <span class="font-bold text-blue-600">Auto-Fill</span></div>
<div><b>2.</b> Or paste JSON manually</div>
<div><b>3.</b> Click <span class="bg-black text-white px-1 rounded-sm">Merge</span></div>
</div>
<div class="mt-2 text-[9px] text-gray-400 border-t border-gray-100 pt-1">
Includes only failed items.
</div>`;
        }
    }
}



async function handleAutoFill() {
    const prompt = getEl('activePromptText').value;
    // Primary + Backup Models
    const models = [
        'mistralai/devstral-2512:free',
        'tngtech/deepseek-r1t2-chimera:free'
    ];

    if (!prompt) { showToast("No prompt generated yet"); return; }

    const btn = document.querySelector('button[onclick="handleAutoFill()"]');
    const originalContent = btn ? btn.innerHTML : '';
    const wrapper = getEl('jsonInputWrapper');

    // Loading State
    const inputArea = getEl('activeJsonInput');
    if (inputArea) {
        inputArea.disabled = true;
        inputArea.classList.add('bg-gray-50', 'text-gray-400'); // Visual feedback
    }

    if (btn) {
        btn.disabled = true;
        // Force blue background and white text matches hover state
        btn.classList.remove('text-blue-600', 'bg-white');
        btn.classList.add('bg-blue-600', 'text-white');
    }
    if (wrapper) wrapper.classList.add('ai-blue-glow');

    let success = false;

    for (let i = 0; i < models.length; i++) {
        const model = models[i];

        // Update Status Text
        if (btn) {
            btn.innerHTML = `<span class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2"></span> ${i === 0 ? "THINKING..." : "TRYING BACKUP..."}`;
        }

        try {
            console.log(`Attempting AI generation with model: ${model}`);
            const res = await apiCall('/api/ai_fill', 'POST', {
                prompt: prompt,
                model: model
            });

            if (res && (res.result || Array.isArray(res.result))) {
                // Success!
                const inputArea = getEl('activeJsonInput');
                inputArea.value = JSON.stringify(res.result, null, 2);
                showToast(i === 0 ? "AI Generated Content!" : "Backup Model Scored!");
                success = true;
                break; // Exit loop
            } else {
                console.warn(`Model ${model} failed response check:`, res);
                // If it's the last model, show specific error
                if (i === models.length - 1) {
                    const err = res ? res.error : "Unknown Error";
                    showToast("AI Error: " + err);
                    getEl('activeJsonInput').value = "Error: " + err + "\n\nRaw: " + (res?.raw || "");
                }
            }
        } catch (e) {
            console.error(`Model ${model} exception:`, e);
            if (i === models.length - 1) {
                showToast("Request Failed");
                getEl('activeJsonInput').value = "System Error: " + e.message;
            }
        }
    }

    // Cleanup
    if (inputArea) {
        inputArea.disabled = false;
        inputArea.classList.remove('bg-gray-50', 'text-gray-400');
    }
    if (btn) {
        btn.innerHTML = originalContent;
        btn.disabled = false;
        // Revert styles
        btn.classList.remove('bg-blue-600', 'text-white');
        btn.classList.add('text-blue-600', 'bg-white');
    }
    if (wrapper) wrapper.classList.remove('ai-blue-glow');
}


async function handleStageAction() {
    const input = getEl('activeJsonInput');
    const raw = input.value;
    const status = getEl('jsonStatus');

    if (!raw.trim()) {
        input.classList.add('border-red-500');
        showToast("Input is empty");
        return;
    }

    try {
        // Sanitize: JSON doesn't allow leading + on numbers (e.g., +105 for odds)
        // Convert patterns like ": +105" to ": 105"
        const sanitized = raw.replace(/:\s*\+(\d)/g, ': $1');
        const json = JSON.parse(sanitized);
        input.classList.remove('border-red-500');
        input.classList.add('border-green-500');

        status.innerText = "VALID JSON";
        status.classList.remove('hidden');

        if (state.refineryStage === 'BULK') {
            await processBulkResponse(json);
        } else {
            await processRevisionResponse(json);
        }

    } catch (e) {
        input.classList.add('border-red-500');
        status.innerText = "INVALID SYNTAX";
        status.classList.remove('hidden');
        showToast("JSON Error: " + e.message);
    }
}

async function processBulkResponse(jsonInput) {
    let jsonArray = jsonInput;

    // Unwrap if wrapped object
    if (!Array.isArray(jsonArray) && typeof jsonArray === 'object') {
        if (Array.isArray(jsonArray.picks)) jsonArray = jsonArray.picks;
        else if (Array.isArray(jsonArray.result)) jsonArray = jsonArray.result;
        else if (Array.isArray(jsonArray.data)) jsonArray = jsonArray.data;
    }

    if (!Array.isArray(jsonArray)) {
        showToast("Error: Expected a JSON Array");
        console.warn("Invalid JSON Input:", jsonInput);
        return;
    }

    // MAP JSON TO IDS
    // User response might not have IDs if AI hallucinated, but we asked for them.
    // We Map by ID.
    jsonArray.forEach(item => {
        if (item.message_id) {
            state.processedData[item.message_id] = item;
        }
    });

    updateRefineryCounts();

    // VALIDATE
    showLoader("VALIDATING PICKS", 'auto');
    const res = await apiCall('/api/validate_picks', 'POST', {
        picks: Object.values(state.processedData),
        original_messages: state.selectedMessages
    });
    hideLoader();

    if (res && res.status === 'needs_revision') {
        state.refineryStage = 'REFINEMENT';
        state.failedItems = res.failed_items || [];  // Now API returns the actual list
        state.revisionPrompt = res.revision_prompt;

        updateRefineryCounts();
        renderRefineryUI();
        showToast(`${res.failed_count} items need refinement.`);

    } else {
        // CLEAN - All items parsed successfully
        state.failedItems = [];
        showToast("Batch Validated Successfully!");

        // Disable Refinement Actions
        const autoFillBtn = getEl('autoFillBtn');
        const validateBtn = getEl('validateBtn');
        if (autoFillBtn) {
            autoFillBtn.disabled = true;
            autoFillBtn.classList.add('bg-gray-100', 'text-gray-400', 'border-gray-200', 'cursor-not-allowed');
            autoFillBtn.classList.remove('border-blue-600', 'text-blue-600', 'hover:bg-blue-600', 'hover:text-white', 'swiss-btn');
        }
        if (validateBtn) {
            validateBtn.disabled = true;
            validateBtn.classList.add('bg-gray-100', 'text-gray-300', 'cursor-not-allowed');
            validateBtn.classList.remove('bg-black', 'text-white', 'hover:bg-green-600', 'swiss-btn');
        }

        const finishBtn = getEl('finishProcessingBtn');
        finishBtn.disabled = false;
        // Site-consistent "Ready" state (Brutalist Style)
        finishBtn.classList.remove('text-gray-300', 'cursor-not-allowed', 'bg-black', 'text-white', 'bg-green-600', 'hover:bg-green-500', 'shadow-lg'); // Clean old
        finishBtn.classList.add('bg-white', 'text-black', 'border-2', 'border-black', 'px-6', 'h-12', 'hover:bg-black', 'hover:text-white', 'transition-colors', 'duration-300', 'swiss-btn', 'text-xs', 'font-black');
        finishBtn.innerHTML = `<span>Finalize Batch</span> <span class="material-icons ml-2 group-hover:translate-x-1 transition-transform">arrow_forward</span>`;
        finishBtn.onclick = finalizeBatch;
    }
}

async function processRevisionResponse(jsonInput) {
    let jsonArray = jsonInput;
    // Unwrap if wrapped object
    if (!Array.isArray(jsonArray) && typeof jsonArray === 'object') {
        if (Array.isArray(jsonArray.picks)) jsonArray = jsonArray.picks;
        else if (Array.isArray(jsonArray.result)) jsonArray = jsonArray.result;
        else if (Array.isArray(jsonArray.data)) jsonArray = jsonArray.data;
    }

    showLoader("MERGING FIXES", 'auto');

    // We have existing processedData. We need to merge this new array into it.
    // Call merge API
    const res = await apiCall('/api/merge_revisions', 'POST', {
        original_picks: Object.values(state.processedData),
        revised_picks: jsonArray
    });

    hideLoader();

    if (res && res.merged_picks) {
        // Update State
        res.merged_picks.forEach(p => {
            if (p.message_id) state.processedData[p.message_id] = p;
        });

        state.refineryStage = 'COMPLETE'; // or back to BULK? No, usually done.
        updateRefineryCounts();
        showToast("Revisions Merged");

        // Disable Refinement Actions
        const autoFillBtn = getEl('autoFillBtn');
        const validateBtn = getEl('validateBtn');
        if (autoFillBtn) {
            autoFillBtn.disabled = true;
            autoFillBtn.classList.add('bg-gray-100', 'text-gray-400', 'border-gray-200', 'cursor-not-allowed');
            autoFillBtn.classList.remove('border-blue-600', 'text-blue-600', 'hover:bg-blue-600', 'hover:text-white', 'swiss-btn');
        }
        if (validateBtn) {
            validateBtn.disabled = true;
            validateBtn.classList.add('bg-gray-100', 'text-gray-300', 'cursor-not-allowed');
            validateBtn.classList.remove('bg-black', 'text-white', 'hover:bg-green-600', 'swiss-btn');
        }

        const finishBtn = getEl('finishProcessingBtn');
        finishBtn.disabled = false;
        // Site-consistent "Ready" state (Brutalist Style)
        finishBtn.classList.remove('text-gray-300', 'cursor-not-allowed', 'bg-black', 'text-white', 'bg-green-600', 'hover:bg-green-500', 'shadow-lg'); // Clean old
        finishBtn.classList.add('bg-white', 'text-black', 'border-2', 'border-black', 'px-6', 'h-12', 'hover:bg-black', 'hover:text-white', 'transition-colors', 'duration-300', 'swiss-btn', 'text-xs', 'font-black');
        finishBtn.innerHTML = `<span>Finalize Batch</span> <span class="material-icons ml-2 group-hover:translate-x-1 transition-transform">arrow_forward</span>`;
        finishBtn.onclick = finalizeBatch;
    }
}

function selectQueueItem(index) {
    // Disabled in Bulk Mode
    return;
}


async function checkResults() {
    // Collect all picks
    let allPicks = [];
    Object.values(state.processedData).forEach(item => {
        if (Array.isArray(item)) {
            allPicks = allPicks.concat(item);
        } else {
            allPicks.push(item);
        }
    });

    if (allPicks.length === 0) {
        // Just render table if no picks
        renderTable();
        return;
    }

    // Default Date handling logic...
    const dateInput = document.getElementById('targetDateInput');
    let targetDate = dateInput ? dateInput.value : null;

    // IF no date selected, try to infer from first pick
    if (!targetDate && allPicks.length > 0 && allPicks[0].date) {
        targetDate = allPicks[0].date;
    }
    // Fallback to today
    if (!targetDate) {
        targetDate = new Date().toISOString().split('T')[0];
    }

    // Get loader elements - continue from existing progress
    const bar = getEl('loaderBar');
    const percent = getEl('loaderPercent');
    const title = getEl('loaderTitle');
    const loader = getEl('globalLoader');

    // Show loader if hidden, otherwise continue smoothly
    if (loader) loader.classList.remove('hidden');
    if (loaderInterval) clearInterval(loaderInterval);

    try {
        // Grading phase (continue from where we were)
        if (title) title.innerText = "GRADING RESULTS (ESPN)";

        // 1. Grading
        const gradeRes = await apiCall('/api/grade_picks', 'POST', {
            picks: allPicks,
            date: targetDate
        });

        if (bar) bar.style.width = "85%";
        if (percent) percent.innerText = "85%";

        if (gradeRes && Array.isArray(gradeRes)) {
            // Merge results
            gradeRes.forEach(p => {
                if (p.message_id) {
                    let entry = state.processedData[p.message_id];
                    if (Array.isArray(entry)) {
                        let targetIdx = entry.findIndex(sub => sub.pick === p.pick);
                        if (targetIdx > -1) {
                            entry[targetIdx].result = p.result;
                            entry[targetIdx].score_summary = p.score_summary;
                        }
                    } else if (entry) {
                        entry.result = p.result;
                        entry.score_summary = p.score_summary;
                    }
                }
            });
        }

        // 2. Capper Reconciliation
        if (title) title.innerText = "VERIFYING CAPPERS (DATABASE)";
        if (bar) bar.style.width = "92%";
        if (percent) percent.innerText = "92%";

        await reconcileCappers(allPicks);

        // Finalize
        if (title) title.innerText = "COMPLETE";
        if (bar) bar.style.width = "100%";
        if (percent) percent.innerText = "100%";
        await new Promise(r => setTimeout(r, 400));

    } catch (e) {
        console.error("Grading/Reconciliation Error:", e);
        showToast("Error during processing: " + e.message);
    } finally {
        hideLoader();
        renderTable();
    }
}

async function reconcileCappers(picks) {
    const names = [...new Set(picks.map(p => p.capper_name).filter(n => n && n !== "Unknown"))];
    if (names.length === 0) return;

    const res = await apiCall('/api/match_cappers', 'POST', { names: names });
    const matchMap = res && res.matches ? res.matches : {};

    // Distribute results back to state
    Object.values(state.processedData).forEach(entry => {
        const rows = Array.isArray(entry) ? entry : [entry];
        rows.forEach(row => {
            if (row.capper_name && matchMap[row.capper_name]) {
                const matches = matchMap[row.capper_name];
                row.capper_matches = matches;
                // If top match is 100% score, auto-verify?
                // Depending on type. Exact_canonical = 100.
                if (matches.length > 0 && matches[0].score === 100) {
                    // Update name to canonical case
                    if (row.capper_name !== matches[0].name) {
                        row.capper_name = matches[0].name;
                    }
                    row.capper_verified = true;
                } else {
                    row.capper_verified = false;
                }
            }
        });
    });
}

// --- IMAGE VIEWER ---
function viewPropImage(msgId) {
    // Find key in state
    let msg = state.messages.find(m => m.id == msgId);
    if (!msg) {
        msg = state.selectedMessages.find(m => m.id == msgId);
    }

    if (!msg || (!msg.image && (!msg.images || msg.images.length === 0))) {
        showToast("No image available");
        return;
    }

    // Modal
    const div = document.createElement('div');
    div.className = "fixed inset-0 z-[60] bg-black/95 flex items-center justify-center p-4 cursor-zoom-out backdrop-blur-md";
    div.onclick = () => div.remove();

    // Container
    const container = document.createElement('div');
    container.className = "max-w-4xl w-full max-h-full flex flex-col gap-6 overflow-y-auto no-scrollbar items-center py-10";
    container.onclick = (e) => e.stopPropagation();

    // Images
    const images = msg.images && msg.images.length > 0 ? msg.images : [msg.image];

    images.forEach(src => {
        const img = document.createElement('img');
        img.src = src;
        img.className = "max-h-[70vh] w-auto object-contain rounded shadow-2xl border border-white/10";
        container.appendChild(img);
    });

    // Caption
    if (msg.text) {
        const captionDiv = document.createElement('div');
        captionDiv.className = "bg-white/10 backdrop-blur text-white p-6 rounded-lg border border-white/10 max-w-2xl w-full text-sm leading-relaxed whitespace-pre-wrap font-mono shadow-lg";
        captionDiv.innerText = msg.text;
        container.appendChild(captionDiv);
    }

    // Close Button
    const closeBtn = document.createElement('button');
    closeBtn.className = "fixed top-5 right-5 text-white/50 hover:text-white transition-colors z-50";
    closeBtn.innerHTML = `<span class="material-icons text-4xl">close</span>`;
    closeBtn.onclick = () => div.remove();

    div.appendChild(closeBtn);
    div.appendChild(container);

    // Key event to close
    const onKey = (e) => {
        if (e.key === 'Escape') {
            div.remove();
            document.removeEventListener('keydown', onKey);
        }
    };
    document.addEventListener('keydown', onKey);

    document.body.appendChild(div);
}

// --- STEP 4: TABLE ---
let tableSortedOnce = false; // Track if we've done the initial sort
let filterDebounceTimer = null;

window.updateFilter = (column, value) => {
    state.filters[column] = value.toLowerCase();

    if (filterDebounceTimer) clearTimeout(filterDebounceTimer);
    filterDebounceTimer = setTimeout(() => {
        renderTable();
    }, 300);
};

function renderTable() {
    const tbody = getEl('finalTableBody');
    if (!tbody) return;

    // Clear current content
    tbody.innerHTML = '';

    // Create Fragment (Off-DOM memory)
    const fragment = document.createDocumentFragment();

    // Flatten all picks
    let allRows = [];
    state.selectedMessages.forEach(msg => {
        let data = state.processedData[msg.id] || {};
        let rows = Array.isArray(data) ? data : [data];
        rows.forEach((row, idx) => {
            if (row.pick || row.capper_name) {
                allRows.push({ msg, row, idx });
            }
        });
    });

    // Only sort ONCE on initial render
    if (!tableSortedOnce && allRows.length > 0) {
        // Sort by capper confidence: Low to High
        allRows.sort((a, b) => {
            const aVerified = a.row.capper_verified ? 1 : 0;
            const bVerified = b.row.capper_verified ? 1 : 0;
            if (aVerified !== bVerified) return aVerified - bVerified;
            const aScore = (a.row.capper_matches && a.row.capper_matches[0]) ? a.row.capper_matches[0].score : 0;
            const bScore = (b.row.capper_matches && b.row.capper_matches[0]) ? b.row.capper_matches[0].score : 0;
            return aScore - bScore;
        });
        state.tableRowOrder = allRows.map(r => `${r.msg.id}_${r.idx}`);
        tableSortedOnce = true;
    } else if (tableSortedOnce && state.tableRowOrder) {
        // Use stored order
        const orderMap = {};
        state.tableRowOrder.forEach((key, i) => orderMap[key] = i);
        const knownRows = [];
        const newRows = [];
        allRows.forEach(r => {
            const key = `${r.msg.id}_${r.idx}`;
            if (key in orderMap) knownRows.push({ ...r, sortKey: orderMap[key] });
            else newRows.push(r);
        });
        knownRows.sort((a, b) => a.sortKey - b.sortKey);
        allRows = [...knownRows, ...newRows];
        newRows.forEach(r => state.tableRowOrder.push(`${r.msg.id}_${r.idx}`));
    }

    allRows.forEach(({ msg, row, idx }) => {
        // Apply Filters
        for (const [col, filterVal] of Object.entries(state.filters)) {
            if (!filterVal) continue;
            let val = "";
            if (col === 'message_id') val = msg.id;
            else if (col === 'capper_name') val = row.capper_name;
            else if (col === 'league') val = row.league;
            else if (col === 'type') val = row.type;
            else if (col === 'pick') val = row.pick;
            else if (col === 'odds') val = row.odds;
            else if (col === 'units') val = row.units;
            else if (col === 'result') val = row.result;
            if (!String(val || '').toLowerCase().includes(filterVal)) return;
        }

        const tr = document.createElement('tr');
        const rowKey = `${msg.id}_${idx}`;
        const isSelected = state.tableSelection && state.tableSelection.has(rowKey);

        tr.className = `hover:bg-blue-50 transition-colors group ${isSelected ? 'bg-blue-50' : ''}`;
        tr.id = `row-${rowKey}`;

        // Helper to safely encode text
        const safeText = (txt) => (txt || '').replace(/"/g, '&quot;');

        // Performance: Build HTML string once
        tr.innerHTML = `
            <td class="p-4 border-r border-gray-100 text-center">
                <input type="checkbox" onchange="toggleTableRow('${msg.id}', ${idx}, this)" 
                       class="accent-black cursor-pointer w-4 h-4 border-2 border-black row-checkbox" 
                       ${isSelected ? 'checked' : ''} aria-label="Select Row">
            </td>
            <td class="p-4 font-mono border-r border-gray-100 text-gray-400 select-none flex items-center gap-2 text-xs">
                ${msg.id}
                ${(msg.image || (msg.images && msg.images.length)) ?
                `<button onclick="viewPropImage('${msg.id}')" class="text-gray-300 hover:text-blue-500 transition-colors focus:outline-none focus:text-blue-600" aria-label="View Image">
                    <span class="material-icons text-sm">image</span>
                 </button>` : ''}
            </td>
            <td class="p-4 border-r border-gray-100 truncate max-w-[180px] font-bold relative group-focus-within:overflow-visible text-xs">
                ${generateCapperHtml(msg, idx, row)} 
            </td>
            ${generateEditableTd(msg.id, idx, 'league', row.league, 'uppercase text-xs font-bold text-gray-400')}
            ${generateEditableTd(msg.id, idx, 'type', row.type || "BET", 'uppercase text-xs font-bold text-black border-l-4 border-black pl-2')}
            <td class="p-4 border-r border-gray-100 outline-none focus:bg-white focus:ring-2 focus:ring-blue-500 focus:z-10 relative font-bold text-black truncate max-w-[200px] text-xs" 
                contenteditable="true" 
                onblur="updateRowData('${msg.id}', ${idx}, 'pick', this.innerText)">
                ${row.pick || ''}
            </td>
            ${generateEditableTd(msg.id, idx, 'odds', row.odds, 'font-mono text-xs text-gray-600')}
            ${generateEditableTd(msg.id, idx, 'units', row.units, 'font-mono text-xs text-blue-600 font-bold')}
            <td class="p-4 border-r border-gray-100 font-mono text-xs uppercase tracking-widest ${getResultClass(row.result)}" title="${safeText(row.score_summary)}">
                ${row.result || "Pending"}
            </td>
        `;

        fragment.appendChild(tr);
    });

    tbody.appendChild(fragment);
}

// --- RENDERING HELPERS ---

function generateEditableTd(id, idx, field, val, classes) {
    return `<td class="p-4 border-r border-gray-100 outline-none focus:bg-white focus:ring-2 focus:ring-blue-500 focus:z-10 relative ${classes}" 
            contenteditable="true" 
            onkeydown="handleEnterKey(event, this)"
            onblur="updateRowData('${id}', ${idx}, '${field}', this.innerText)">${val || ''}</td>`;
}

// POLISH: Add "Enter to Blur" for better keyboard workflow
function handleEnterKey(e, el) {
    if (e.key === 'Enter') {
        e.preventDefault();
        el.blur();
    }
}

function generateCapperHtml(msg, idx, row) {
    const capperVal = row.capper_name || "Unknown";
    const safeName = (capperVal || '').replace(/'/g, "\\'");

    let html = `<div class="flex items-center gap-1">
        <span contenteditable="true" class="outline-none focus:bg-white focus:ring-1 focus:ring-blue-300 rounded px-1 min-w-[50px] truncate"
              onblur="updateRowData('${msg.id}', ${idx}, 'capper_name', this.innerText)">${capperVal}</span>`;

    if (!row.capper_verified) {
        let label = "New?";
        let labelClass = "bg-amber-100 text-amber-700";
        if (row.capper_matches && row.capper_matches.length > 0) {
            const topMatch = row.capper_matches[0];
            label = `${topMatch.score}%`;
            if (topMatch.score > 80) labelClass = "bg-blue-100 text-blue-700";
            else labelClass = "bg-orange-100 text-orange-700";
        }
        html += `<button onclick="showCapperSuggestions(this, '${msg.id}', ${idx}, '${safeName}')" 
                 class="${labelClass} hover:bg-opacity-80 rounded px-1.5 py-0.5 text-[10px] font-bold flex items-center gap-1 min-w-fit" title="Click to Resolve" aria-label="Resolve Capper Name">
                 <span class="material-icons text-[10px]">warning</span> ${label}
              </button>`;
    } else {
        html += `<span class="material-icons text-[14px] text-green-500 align-middle ml-1" title="Verified">check_circle</span>`;
    }
    html += `</div>`;
    return html;
}

function getResultClass(result) {
    result = result || "Pending";
    if (result === 'Win') return "text-green-600 font-black";
    if (result === 'Loss') return "text-red-600 font-black";
    if (result === 'PUSH') return "text-orange-500 font-black";
    return "text-gray-400";
}

// Global helper to update state from table edits
window.updateRowData = async (msgId, idx, field, value) => {
    // Locate item in state
    let entry = state.processedData[msgId];
    if (!entry) return;

    let targetRow = null;
    if (Array.isArray(entry)) {
        if (entry[idx]) {
            entry[idx][field] = value.trim();
            targetRow = entry[idx];
        }
    } else {
        entry[field] = value.trim();
        targetRow = entry;
    }

    // If capper_name changed, trigger live fuzzy matching
    if (field === 'capper_name' && targetRow && value.trim()) {
        try {
            const res = await apiCall('/api/match_cappers', 'POST', { names: [value.trim()] });
            const matchMap = res && res.matches ? res.matches : {};
            const matches = matchMap[value.trim()] || [];

            targetRow.capper_matches = matches;

            // Auto-verify if 100% match
            if (matches.length > 0 && matches[0].score === 100) {
                if (targetRow.capper_name !== matches[0].name) {
                    targetRow.capper_name = matches[0].name;
                }
                targetRow.capper_verified = true;
            } else {
                targetRow.capper_verified = false;
            }

            // Re-render to show new validation status
            renderTable();
        } catch (e) {
            console.error("Live capper match failed:", e);
        }
    }
};

// --- DELETE & SELECTION LOGIC ---

// Global Selection State
if (!state.tableSelection) state.tableSelection = new Set();
let pendingDeleteAction = null; // Stores { type: 'single'|'bulk', id, idx }

window.toggleTableRow = (msgId, idx, el) => {
    const key = `${msgId}_${idx}`;
    const rowEl = document.getElementById(`row-${key}`);

    if (el.checked) {
        state.tableSelection.add(key);
        if (rowEl) rowEl.classList.add('bg-blue-50');
    } else {
        state.tableSelection.delete(key);
        if (rowEl) rowEl.classList.remove('bg-blue-50');
    }
    updateDeleteButtonUI();
};

window.toggleAllTableRows = (el) => {
    const allCheckboxes = document.querySelectorAll('.row-checkbox');
    state.tableSelection.clear();

    allCheckboxes.forEach(chk => {
        chk.checked = el.checked;
    });

    // Rebuild state perfectly from data
    if (el.checked) {
        // Gather all currently visible items
        Object.keys(state.processedData).forEach(id => {
            let data = state.processedData[id];
            let rows = Array.isArray(data) ? data : [data];
            rows.forEach((row, idx) => {
                if (row.pick || row.capper_name) {
                    state.tableSelection.add(`${id}_${idx}`); // Use ID from key
                }
            });
        });
    }
    updateDeleteButtonUI();
};

window.updateDeleteButtonUI = () => {
    const btn = document.getElementById('deleteSelectedBtn');
    const countEl = document.getElementById('deleteCount');
    if (!btn) return;

    const count = state.tableSelection.size;
    countEl.innerText = count;

    if (count > 0) {
        btn.classList.remove('hidden');
        btn.classList.add('flex');
    } else {
        btn.classList.add('hidden');
        btn.classList.remove('flex');
    }
};

window.promptDeleteRow = (msgId, idx) => {
    pendingDeleteAction = { type: 'single', id: msgId, idx: idx };
    document.getElementById('deleteModalCount').innerText = "1";
    document.getElementById('deleteModal').classList.remove('hidden');
};

window.confirmBulkDelete = () => {
    pendingDeleteAction = { type: 'bulk' };
    document.getElementById('deleteModalCount').innerText = state.tableSelection.size;
    document.getElementById('deleteModal').classList.remove('hidden');
};

window.closeDeleteModal = () => {
    document.getElementById('deleteModal').classList.add('hidden');
    pendingDeleteAction = null;
};

window.confirmDeleteAction = () => {
    if (!pendingDeleteAction) return;

    if (pendingDeleteAction.type === 'single') {
        deleteRow(pendingDeleteAction.id, pendingDeleteAction.idx);
    } else if (pendingDeleteAction.type === 'bulk') {
        const toDelete = Array.from(state.tableSelection);
        toDelete.forEach(key => {
            const parts = key.split('_');
            // msgId is all parts except last, idx is last. 
            // BUT msgId in '54328_0' is '54328'.
            // If msgId has underscores? 'capper_name_123_0' -> 'capper_name_123', '0'.
            const idx = parseInt(parts.pop());
            const id = parts.join('_');

            deleteRow(id, idx, false); // false = don't render yet
        });
        state.tableSelection.clear();
        updateDeleteButtonUI();
        renderTable();
    }

    closeDeleteModal();
};

window.deleteRow = (msgId, idx, shouldRender = true) => {
    // Locate item
    let entry = state.processedData[msgId];
    if (!entry) return;

    if (Array.isArray(entry)) {
        // Soft delete inside array to keep indices valid during iteration
        // Actually, if we just null it, renderTable needs to skip it.
        // Let's modify renderTable skip logic? 
        // Existing renderTable: "if (row.pick || row.capper_name)"
        // So if we empty it, it disappears.
        entry[idx] = {}; // Clear it
    } else {
        delete state.processedData[msgId];
    }

    // Cleanup Checkbox
    state.tableSelection.delete(`${msgId}_${idx}`);

    if (shouldRender) renderTable();
};

// --- MANUAL ENTRY ---
window.addManualRow = () => {
    // Generate a unique ID for the manual entry
    const manualId = `manual_${Date.now()}`;
    const today = new Date().toISOString().split('T')[0];

    // Create a blank row
    const newRow = {
        message_id: manualId,
        capper_name: 'Unknown',
        league: 'Other',
        type: 'BET',
        pick: '',
        odds: '',
        units: '1',
        date: today,
        result: '',
        capper_verified: false,
        capper_matches: []
    };

    // Add to state
    state.processedData[manualId] = newRow;

    // Also add a dummy message entry so the render loop includes it
    if (!state.selectedMessages.find(m => m.id === manualId)) {
        state.selectedMessages.push({ id: manualId, text: 'Manual Entry', date: today });
    }

    // Re-render
    renderTable();

    // Scroll to bottom to show new row
    const tableContainer = document.querySelector('#page-4 .overflow-auto');
    if (tableContainer) tableContainer.scrollTop = tableContainer.scrollHeight;

    showToast('Manual row added');
};

async function finalizeBatch() {
    // Reset sort flag so fresh data gets sorted, but edits won't re-sort
    tableSortedOnce = false;
    state.tableRowOrder = [];
    changeStep(4);
    // Auto-run grading
    await checkResults();
}

async function uploadData() {
    // Gather data from table or state?
    // Gathering from State is safer, but user might have edited table (contenteditable).
    // For now, let's use State as source of truth for simplicity, or ideally we parse table.
    // MVP: Use State.

    const picks = [];
    Object.keys(state.processedData).forEach(id => {
        const item = state.processedData[id];
        if (Array.isArray(item)) {
            item.forEach(i => picks.push(i));
        } else {
            picks.push(item);
        }
    });

    if (picks.length === 0) {
        showToast("No picks to upload");
        return;
    }

    showLoader("UPLOADING MANIFEST TO CORE", 'auto');

    const res = await apiCall('/api/upload', 'POST', {
        picks: picks,
        date: new Date().toISOString().split('T')[0] // or selected date
    });

    hideLoader();

    if (res && res.success) {
        showToast("Upload Successful");
        setTimeout(() => window.location.reload(), 2000);
    } else {
        showToast("Upload Failed: " + (res.error || "Unknown"));
    }
}

async function exportToCSV() {
    // Gather picks
    const picks = [];
    Object.values(state.processedData).forEach(item => {
        if (Array.isArray(item)) picks.push(...item);
        else picks.push(item);
    });

    if (picks.length === 0) {
        showToast("No data to export");
        return;
    }

    showLoader("EXPORTING CSV...", 0); // Indefinite/busy mode

    try {
        const res = await apiCall('/api/export_csv', 'POST', { picks: picks });
        hideLoader();

        if (res && res.success) {
            showToast(`Saved to Desktop: ${res.filename}`);
        } else {
            showToast("Export failed: " + (res?.error || "Unknown error"));
        }
    } catch (e) {
        hideLoader();
        showToast("Export failed: " + e.message);
    }
}

function exportToCSVClientSide(picks) {
    const rows = [];
    // Headers
    rows.push(["ID", "Capper", "Sport", "Type", "Pick", "Odds", "Units", "Date", "Result"]);

    picks.forEach(item => {
        rows.push([
            `"${item.message_id || ''}"`,
            `"${item.capper_name || ''}"`,
            `"${item.league || ''}"`,
            `"${item.type || 'BET'}"`,
            `"${(item.pick || '').replace(/"/g, '""')}"`,
            `"${item.odds || ''}"`,
            `"${item.units || ''}"`,
            `"${item.date || ''}"`,
            `"${item.result || ''}"`
        ]);
    });

    const csvString = rows.map(e => e.join(",")).join("\n");
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = "manifest_export.csv";
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();

    setTimeout(() => {
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }, 100);
}

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    // 1. Set Default Date to Yesterday (Eastern Time)
    try {
        const etNow = new Date(new Date().toLocaleString("en-US", { timeZone: "America/New_York" }));
        etNow.setDate(etNow.getDate() - 1); // Yesterday
        const yyyy = etNow.getFullYear();
        const mm = String(etNow.getMonth() + 1).padStart(2, '0');
        const dd = String(etNow.getDate()).padStart(2, '0');
        const yesterdayStr = `${yyyy}-${mm}-${dd}`;

        const dInput = getEl('targetDateInput');
        if (dInput) dInput.value = yesterdayStr;
    } catch (e) {
        console.error("Date init error", e);
    }
});

// --- PERFORMANCE: VIRTUAL SCROLLER & LAZY LOADING HELPERS ---

let msgObserver = null;
let currentRenderIdx = 0;
let sortedMsgCache = [];
const BATCH_SIZE = 40;

// Lazy Load Observer
const imgObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const img = entry.target;
            const src = img.dataset.src;
            if (src) {
                img.src = src;
                img.onload = () => img.classList.remove('opacity-0'); // Fade in
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        }
    });
}, { rootMargin: "200px" });

function lazyLoadImages(container) {
    const images = container.querySelectorAll('img.lazy-img');
    images.forEach(img => imgObserver.observe(img));
}

function renderNextBatch() {
    const grid = getEl('messageGrid');
    const sentinel = getEl('gridSentinel');

    if (currentRenderIdx >= sortedMsgCache.length) return;

    const end = Math.min(currentRenderIdx + BATCH_SIZE, sortedMsgCache.length);
    const batch = sortedMsgCache.slice(currentRenderIdx, end);

    const fragment = document.createDocumentFragment();

    batch.forEach(msg => {
        const el = document.createElement('div');
        el.className = `grid-item bg-white flex flex-col cursor-pointer group relative h-full select-none animate-fade-in`;
        el.innerHTML = buildMessageHTML(msg);
        el.onclick = () => toggleMessage(el, msg);
        fragment.appendChild(el);
    });

    // Insert before sentinel
    if (sentinel && sentinel.parentNode === grid) {
        grid.insertBefore(fragment, sentinel);
    } else {
        grid.appendChild(fragment);
    }

    // observe new images
    lazyLoadImages(grid);

    currentRenderIdx = end;

    if (currentRenderIdx >= sortedMsgCache.length) {
        if (msgObserver) msgObserver.disconnect();
        if (sentinel) sentinel.remove();
    }
}

function buildMessageHTML(msg) {
    let imgHTML = '';
    if (msg.image) {
        // LAZY LOAD: use data-src and opacity-0
        imgHTML = `<div class="h-40 bg-gray-100 border-b border-gray-100 overflow-hidden relative group/img">
            <img data-src="${msg.image}" 
                 onclick="event.stopPropagation(); viewPropImage('${msg.id}')"
                 class="w-full h-full object-cover transition-opacity duration-500 opacity-0 lazy-img cursor-pointer hover:opacity-90">
            <div class="absolute inset-0 flex items-center justify-center pointer-events-none text-gray-200">
                <span class="material-icons text-xl animate-pulse">image</span>
            </div>
        </div>`;
    } else {
        imgHTML = `<div class="h-40 bg-gray-50 border-b border-gray-100 flex items-center justify-center"><span class="material-icons text-gray-300 text-3xl">text_fields</span></div>`;
    }

    const msgText = parseMarkdown(msg.text || "");
    let msgTime = '--:--';
    if (msg.date) {
        const timeMatch = msg.date.match(/(\d{2}:\d{2})/);
        if (timeMatch) msgTime = timeMatch[1] + " ET";
    }

    // Default Selected State (checked)
    const isSelected = state.selectedMessages.some(m => m.id === msg.id);
    const checkClass = isSelected ? "bg-blue-600 border-blue-600 scale-110" : "border-gray-300";
    const checkContent = isSelected ? '<span class="material-icons text-[12px] text-white">check</span>' : '';
    const idClass = isSelected ? "text-blue-600" : "text-gray-300";

    return `
        ${imgHTML}
        <div class="p-5 flex flex-col flex-grow">
            <div class="flex justify-between items-center mb-3">
                <span class="font-mono text-[10px] uppercase bg-gray-100 px-1 py-0.5 truncate max-w-[120px]" title="${msg.channel_name}">${msg.channel_name || 'Channel'}</span>
                <span class="font-mono text-[10px] text-gray-400">${msgTime}</span>
            </div>
            <p class="font-serif text-sm leading-snug text-gray-800 mb-4 max-h-16 overflow-y-auto whitespace-pre-wrap" tabindex="0">${msgText}</p>
            <div class="mt-auto flex justify-between items-center pt-4 border-t border-gray-100">
                 <span class="text-[10px] font-bold uppercase tracking-widest group-hover:text-blue-600 transition-colors msg-id ${idClass}">Select ID: ${msg.id}</span>
                 <div class="w-4 h-4 border ${checkClass} msg-check flex items-center justify-center transition-all duration-200">${checkContent}</div>
            </div>
        </div>
    `;
}
