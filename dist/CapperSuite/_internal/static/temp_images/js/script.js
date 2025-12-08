// static/temp_images/js/script.js
let currentStep=1, fetchedMessages=[], combinedDataCache=[], sortOrder={}, allCappers=[], fuseInstance=null;
let pendingDeleteIndex = -1; // Store index for deletion
const steps = ['Connect', 'Select', 'Process', 'Review'];

document.addEventListener('DOMContentLoaded', async () => {
    initStepper();
    injectCustomModals(); // Inject the new delete modal HTML
    
    const d = document.getElementById('targetDate');
    if(d) {
        const now = new Date(); const utc = now.getTime() + (now.getTimezoneOffset()*60000);
        const et = new Date(utc - (3600000*5)); et.setDate(et.getDate()-1);
        d.value = et.toISOString().split('T')[0];
        triggerScorePrefetch();
    }
    try {
        const res = await fetch('/api/check_auth');
        const data = await res.json();
        document.getElementById('auth-loading').classList.add('hidden');
        if(data.authorized) { document.getElementById('auth-success').classList.remove('hidden'); loadChannels(); }
        else document.getElementById('auth-phone').classList.remove('hidden');
        const cRes = await fetch('/api/get_cappers'); allCappers = await cRes.json();
        if(allCappers.length && typeof Fuse !== 'undefined') fuseInstance = new Fuse(allCappers,{keys:['name'],threshold:0.4});
    } catch(e) {}
});

// --- UI INJECTION ---
function injectCustomModals() {
    const deleteModalHTML = `
    <div id="customDeleteModal" class="fixed inset-0 z-[200] bg-black/60 backdrop-blur-sm hidden flex items-center justify-center p-4 opacity-0 transition-opacity duration-300">
        <div class="bg-white rounded-2xl shadow-2xl max-w-sm w-full overflow-hidden transform scale-95 transition-all duration-300 border border-gray-100" id="customDeleteContent">
            <div class="p-6 text-center">
                <div class="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span class="material-icons text-red-500 text-3xl">delete_outline</span>
                </div>
                <h3 class="text-xl font-bold text-gray-900 mb-2 tracking-tight">Delete Pick?</h3>
                <p class="text-sm text-gray-500 mb-8 leading-relaxed">Are you sure you want to remove this pick from the list? This action cannot be undone.</p>
                <div class="flex gap-3 justify-center">
                    <button onclick="closeDeleteModal()" class="flex-1 px-4 py-3 bg-gray-50 hover:bg-gray-100 text-gray-700 rounded-xl text-sm font-bold transition-colors border border-gray-200">Cancel</button>
                    <button onclick="confirmDelete()" class="flex-1 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl text-sm font-bold shadow-lg shadow-red-200 transition-all transform active:scale-95 flex items-center justify-center gap-2">
                        <span class="material-icons text-sm">delete</span> Delete
                    </button>
                </div>
            </div>
        </div>
    </div>`;
    document.body.insertAdjacentHTML('beforeend', deleteModalHTML);
}

// --- STEPPER LOGIC ---
function initStepper() {
    document.getElementById('stepper').innerHTML = steps.map((s,i) => `
        <div class="flex items-center ${i===steps.length-1?'':'flex-grow'} step-item" id="step-${i+1}">
            <div class="step-dot bg-white text-gray-400 border-2 border-gray-200 shadow-sm transition-all duration-300">${i+1}</div>
            ${i===steps.length-1?'':`<div class="step-line h-0.5 bg-gray-200 flex-grow mx-2 transition-all duration-300" id="line-${i+1}"></div>`}
        </div>`).join('');
    updateStepper();
}
function updateStepper() {
    const btn = document.getElementById('backBtn');
    if(btn) btn.disabled = currentStep===1;
    for(let i=1; i<=4; i++) {
        const d=document.querySelector(`#step-${i} .step-dot`), l=document.querySelector(`#line-${i}`), p=document.getElementById(`page-${i}`);
        if(i < currentStep) { 
            d.className='step-dot bg-green-500 text-white border-green-500'; 
            d.innerHTML='<span class="material-icons text-sm">check</span>'; 
            if(l) l.className='step-line bg-green-500 h-0.5 flex-grow mx-2'; 
        }
        else if(i===currentStep) { 
            d.className='step-dot bg-blue-600 text-white border-blue-600 shadow-lg scale-110 ring-2 ring-blue-100'; 
            d.innerHTML=i; 
            if(l) l.className='step-line bg-gray-200 h-0.5 flex-grow mx-2'; 
        }
        else { 
            d.className='step-dot bg-white text-gray-400 border-2 border-gray-200'; 
            d.innerHTML=i; 
            if(l) l.className='step-line bg-gray-200 h-0.5 flex-grow mx-2'; 
        }
        if(p) { 
            if(i===currentStep) { p.classList.remove('hidden'); p.classList.add('flex'); } 
            else { p.classList.add('hidden'); p.classList.remove('flex'); } 
        }
    }
}
function goToStep(s) { if(s===3 && currentStep===2) runOCRProcess(); currentStep=s; updateStepper(); }
function goBack() { if(currentStep>1) goToStep(currentStep-1); }

// --- UTILS ---
function showLoader(m) { document.getElementById('loaderText').innerText=m; document.getElementById('globalLoader').classList.remove('hidden'); }
function hideLoader() { document.getElementById('globalLoader').classList.add('hidden'); }
function showToast(m) { const t=document.getElementById('toast'); document.getElementById('toastMsg').innerText=m; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),3000); }

// --- PAGE 1: CONNECT ---
async function sendCode() {
    await fetch('/api/send_code', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone:document.getElementById('phoneNumber').value})});
    document.getElementById('auth-phone').classList.add('hidden'); document.getElementById('auth-code').classList.remove('hidden');
}
async function verifyCode() {
    const res = await (await fetch('/api/verify_code', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:document.getElementById('otpCode').value, password:document.getElementById('2faPassword').value})})).json();
    if(res.status === 'SUCCESS') { document.getElementById('auth-code').classList.add('hidden'); document.getElementById('auth-success').classList.remove('hidden'); loadChannels(); } else alert("Failed");
}
async function loadChannels() {
    const cs = await (await fetch('/api/get_channels')).json();
    document.getElementById('channelList').innerHTML = cs.map(c => `
        <div class="flex items-center p-3 hover:bg-blue-50 rounded-lg cursor-pointer border-b border-gray-50 transition group" onclick="toggleChan(this)">
            <input type="checkbox" value="${c.id}" class="custom-checkbox mr-3 ch-select pointer-events-none">
            <span class="text-sm font-semibold text-gray-700 group-hover:text-blue-700">${c.name}</span>
        </div>`).join('');
}
function toggleChan(el) {
    const cb = el.querySelector('input'); cb.checked = !cb.checked;
    const c = document.querySelectorAll('.ch-select:checked').length;
    const b = document.getElementById('btnFetch');
    const t = document.getElementById('btnFetchText');
    
    b.disabled = c===0;
    if(c>0) {
        b.classList.remove('bg-gray-200', 'text-gray-400', 'cursor-not-allowed');
        b.classList.add('bg-blue-600', 'hover:bg-blue-700', 'text-white', 'shadow-lg', 'cursor-pointer');
        t.innerHTML = `Fetch (${c}) Picks`;
    } else {
        b.classList.add('bg-gray-200', 'text-gray-400', 'cursor-not-allowed');
        b.classList.remove('bg-blue-600', 'hover:bg-blue-700', 'text-white', 'shadow-lg', 'cursor-pointer');
        t.innerHTML = `Select a Channel to Fetch`;
    }
}
async function triggerScorePrefetch() { await fetch('/api/prefetch_scores', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({date:document.getElementById('targetDate').value})}); }

// --- PAGE 2: SELECT ---
async function fetchMessages() {
    const ids = Array.from(document.querySelectorAll('.ch-select:checked')).map(c=>c.value);
    if(ids.length === 0) return;
    showLoader('Fetching...');
    try {
        fetchedMessages = await (await fetch('/api/fetch_messages', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({channel_id:ids, date:document.getElementById('targetDate').value})})).json();
        renderGrid(); goToStep(2);
    } catch(e){ alert(e); } finally { hideLoader(); }
}
function renderGrid() {
    const g = document.getElementById('messageGrid'); g.innerHTML='';
    if(!fetchedMessages.length) { g.innerHTML='<div class="col-span-3 text-center py-10 text-gray-400">No messages found.</div>'; return; }
    fetchedMessages.forEach((m,i) => {
        const img = m.image ? `<div class="relative mt-2 rounded overflow-hidden h-32 bg-gray-100 group-hover:opacity-90 transition" onclick="event.stopPropagation();openModal('${m.image}')"><img src="${m.image}" class="w-full h-full object-contain"></div>`:'';
        g.insertAdjacentHTML('beforeend', `<div id="card-${i}" class="card p-4 selected cursor-pointer border-2 hover:border-blue-300 transition transform hover:-translate-y-1" onclick="toggleMsg(${i})">
            <div class="flex justify-between mb-2"><span class="bg-blue-50 text-blue-700 text-[10px] font-bold px-2 py-1 rounded truncate">${m.channel_name}</span><div class="w-5 h-5 rounded-full border border-gray-200 check-indicator bg-blue-600 border-blue-600 flex items-center justify-center shadow-sm"><span class="material-icons text-white text-xs">check</span></div></div>
            <div class="text-xs text-gray-400 mb-2">${m.date}</div><div class="text-sm text-gray-700 line-clamp-4 pointer-events-none mb-2">${m.text||''}</div>${img}</div>`);
    });
}
function toggleMsg(i) {
    fetchedMessages[i].selected = !fetchedMessages[i].selected;
    const c = document.getElementById(`card-${i}`), ind = c.querySelector('.check-indicator'), ic = ind.querySelector('span');
    if(fetchedMessages[i].selected) { c.classList.remove('opacity-60','grayscale'); ind.classList.add('bg-blue-600','border-blue-600'); ic.classList.remove('hidden'); } 
    else { c.classList.add('opacity-60','grayscale'); ind.classList.remove('bg-blue-600','border-blue-600'); ic.classList.add('hidden'); }
}

// --- PAGE 3: PROCESS ---
function switchTab(t) {
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active')); 
    document.getElementById(`tab-${t}`).classList.add('active');
    ['prompts','responses'].forEach(x => document.getElementById(`content-${x}`).classList.add('hidden'));
    document.getElementById(`content-${t}`).classList.remove('hidden');

    const btn = document.getElementById('step3ActionBtn');
    if (t === 'prompts') {
        btn.innerText = "Go to Step 2 (Paste)";
        btn.className = "w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-bold shadow-md transition-all transform active:scale-[0.99]";
        btn.onclick = () => switchTab('responses');
    } else {
        btn.innerText = "Validate & Grade Picks";
        btn.className = "w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-bold shadow-md transition-all transform active:scale-[0.99]";
        btn.onclick = () => validateAndProceed();
    }
}

async function runOCRProcess() {
    showLoader('Processing...');
    const sel = fetchedMessages.filter(m=>m.selected);
    try {
        const d = await (await fetch('/api/generate_prompt', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:sel, watermark:document.getElementById('watermarkInput').value})})).json();
        d.updated_messages.forEach(u => { const l=fetchedMessages.find(m=>m.id===u.id); if(l){l.ocr_text=u.ocr_text; l.text=u.text;} });
        renderBatches(d.prompts); renderOCR(d.updated_messages); if(!document.getElementById('watermarkInput').value) detectWatermark();
    } catch(e){alert(e);} finally{hideLoader();}
}
function renderBatches(ps) {
    const pc=document.getElementById('promptsContainer'), rc=document.getElementById('responsesContainer');
    pc.innerHTML=''; rc.innerHTML='';
    ps.forEach((p,i)=>{
        pc.insertAdjacentHTML('beforeend', `
            <div class="bg-gray-50 p-3 rounded-lg border border-gray-200 relative shadow-sm mb-4">
                <div class="flex justify-between items-center mb-2">
                    <h4 class="text-xs font-bold text-gray-600">Batch ${i+1}</h4>
                    <button onclick="copyText('p-${i}', this)" class="text-xs bg-white border border-gray-300 px-3 py-1 rounded hover:bg-gray-100 shadow-sm font-bold text-gray-600 transition-all">Copy Prompt</button>
                </div>
                <textarea id="p-${i}" class="w-full h-24 text-[10px] bg-white border rounded p-2 resize-y font-mono text-gray-600" readonly>${p}</textarea>
            </div>`);
        rc.insertAdjacentHTML('beforeend', `<div class="mb-4"><label class="text-xs font-bold block mb-1 text-gray-600">Batch ${i+1} Response</label><textarea id="r-${i}" class="response-input w-full h-32 border rounded-lg p-2 text-xs focus:ring-2 focus:ring-blue-500 outline-none shadow-sm font-mono" placeholder="Paste AI JSON here..."></textarea></div>`);
    });
}

function renderOCR(ms) { 
    const container = document.getElementById('ocrPreview');
    const selected = ms.filter(m => m.selected);
    if (selected.length === 0) { container.innerHTML = '<div class="text-gray-400 text-xs text-center mt-4">No items selected</div>'; return; }
    container.innerHTML = selected.map(m => `
        <div class="bg-white p-3 rounded-lg border shadow-sm mb-3 group relative hover:shadow-md transition">
            <div class="text-blue-600 font-bold text-xs mb-1 flex items-center gap-1"><span class="material-icons text-[10px]">chat</span> ${m.channel_name}</div>
            ${m.image ? `<div class="relative h-32 bg-gray-100 rounded mb-2 overflow-hidden cursor-pointer border border-gray-100" onclick="openModal('${m.image}')"><img src="${m.image}" class="w-full h-full object-contain"><div class="absolute inset-0 bg-black/5 hover:bg-black/0 transition"></div></div>` : ''}
            <div class="text-[10px] text-gray-700 font-mono bg-gray-50 p-2 rounded border max-h-32 overflow-y-auto">
                <span class="font-bold text-gray-400 uppercase">Caption</span><br/>${m.text || '<span class="italic text-gray-300">No Caption</span>'}
                <hr class="my-2 border-gray-200"><span class="font-bold text-gray-400 uppercase">OCR extraction</span><br/>${m.ocr_text || '<span class="italic text-gray-300">No OCR Data</span>'}
            </div>
        </div>`).join(''); 
}

async function detectWatermark() { const d=await(await fetch('/api/detect_watermark', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:fetchedMessages.filter(m=>m.selected)})})).json(); if(d.watermark) document.getElementById('watermarkInput').value=d.watermark; }

async function validateAndProceed() {
    const inputs = document.querySelectorAll('.response-input'); let raw = [];
    inputs.forEach(ip => {
        try {
            let t = ip.value.trim(); if(!t) return;
            if(t.includes('```')) t = t.split('```json')[1]?.split('```')[0] || t.split('```')[1]?.split('```')[0] || t;
            const j = JSON.parse(t.substring(t.indexOf('['))); if(Array.isArray(j)) raw=raw.concat(j);
        } catch(e){}
    });
    if(!raw.length) { alert("No valid JSON found in responses. Please paste AI output."); return; }
    
    combinedDataCache = raw; 
    showLoader('Validating...');
    
    const hasUnknowns = raw.some(r => !r.capper_name || r.capper_name === 'Unknown' || r.capper_name === 'N/A');
    
    if (hasUnknowns) {
        try {
            const res = await (await fetch('/api/generate_smart_fill', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({picks:raw, original_messages:fetchedMessages})})).json();
            if(res.prompt) {
                hideLoader();
                const section = document.getElementById('revisionSection');
                document.getElementById('revisionPromptBox').value = res.prompt;
                section.classList.remove('hidden');
                const headerDiv = section.querySelector('div.flex');
                if(headerDiv && !headerDiv.querySelector('.copy-btn-sf')) {
                   const btn = document.createElement('button');
                   btn.className = 'copy-btn-sf bg-white border border-amber-200 text-amber-700 px-2 py-1 rounded text-xs font-bold hover:bg-amber-100 ml-2 transition-all';
                   btn.onclick = function() { copyText('revisionPromptBox', this); };
                   btn.innerText = 'Copy Prompt';
                   headerDiv.appendChild(btn);
                }
                const skipBtn = section.querySelector('button.text-gray-500');
                if(skipBtn) skipBtn.onclick = () => { section.classList.add('hidden'); runGrading(); };
                showToast("Unknowns detected. Smart Fill prompt generated.");
                return; 
            }
        } catch(e) { console.error(e); }
    }
    runGrading();
}

async function processRevisions() {
    showLoader('Merging Smart Fill...');
    try {
        let t = document.getElementById('revisionResponseInput').value;
        if(t.includes('```')) t = t.split('```json')[1]?.split('```')[0] || t;
        const fix = JSON.parse(t);
        if (fix.length > 0 && fix[0].hasOwnProperty('capper_name')) {
             combinedDataCache.forEach(orig => {
                 const match = fix.find(f => f.message_id === orig.message_id && f.pick === orig.pick);
                 if(match && match.capper_name && match.capper_name !== 'Unknown') { orig.capper_name = match.capper_name; }
             });
        }
        document.getElementById('revisionSection').classList.add('hidden');
        await runGrading(); 
    } catch(e){ hideLoader(); alert("Invalid JSON response provided."); }
}

async function runGrading() {
    showLoader('Grading Picks...');
    try {
        const response = await fetch('/api/grade_picks', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({picks:combinedDataCache, date:document.getElementById('targetDate').value})});
        if (!response.ok) throw new Error('Backend Error');
        combinedDataCache = await response.json();
        if(fuseInstance && Array.isArray(combinedDataCache)) {
            combinedDataCache.forEach(p => { 
                const n = (p.capper_name||'').toLowerCase();
                if(n && n !== 'unknown' && n !== 'n/a' && n.length > 2) { 
                    try { const s = fuseInstance.search(p.capper_name); if(s.length && s[0].item.name !== p.capper_name) { p._suggestion = s[0].item.name; } } catch (err) {}
                } 
            });
        }
        renderTable(); currentStep=4; updateStepper();
    } catch(e){ console.error(e); alert("Grading Error: " + e.message); } finally { hideLoader(); }
}

// --- PAGE 4: REVIEW ---
function renderTable() {
    const b = document.getElementById('reviewBody'); b.innerHTML='';
    const selCount = combinedDataCache.filter(r => r._selected).length;
    let hasErrors = false;

    const theadTr = document.querySelector('thead tr');
    if(theadTr) {
        const allSelected = combinedDataCache.length > 0 && combinedDataCache.every(r => r._selected);
        theadTr.innerHTML = `
            <th class="p-3 text-center w-10 sticky top-0 bg-gray-50 z-10 border-b"><input type="checkbox" id="header-cb" onclick="toggleSelectAll(this)" class="custom-checkbox" ${allSelected?'checked':''}></th>
            <th class="p-3 text-center w-10 sticky top-0 bg-gray-50 z-10 border-b">Src</th>
            <th class="p-3 cursor-pointer sticky top-0 bg-gray-50 z-10 border-b" onclick="sortTable('capper_name')">Capper <span class="text-red-500">*</span></th>
            <th class="p-3 sticky top-0 bg-gray-50 z-10 border-b">League <span class="text-red-500">*</span></th>
            <th class="p-3 sticky top-0 bg-gray-50 z-10 border-b">Pick <span class="text-red-500">*</span></th>
            <th class="p-3 text-right sticky top-0 bg-gray-50 z-10 border-b">Odds</th>
            <th class="p-3 text-right sticky top-0 bg-gray-50 z-10 border-b">Units</th>
            <th class="p-3 text-center sticky top-0 bg-gray-50 z-10 border-b">Result</th>
            <th class="p-3 w-10 sticky top-0 bg-gray-50 z-10 border-b"></th>
        `;
    }

    combinedDataCache.forEach((r,i) => {
        // --- VALIDATION LOGIC ---
        const isCapperMissing = !r.capper_name || r.capper_name === 'Unknown' || r.capper_name === 'N/A';
        const isLeagueMissing = !r.league || r.league === 'Unknown';
        const isPickMissing = !r.pick;
        
        if(isCapperMissing || isLeagueMissing || isPickMissing) hasErrors = true;

        const capperClass = isCapperMissing ? 'error-cell' : '';
        const leagueClass = isLeagueMissing ? 'error-cell' : '';
        const pickClass = isPickMissing ? 'error-cell' : '';
        
        let cls = r.result?.toLowerCase().includes('win')?'bg-result-win':r.result?.toLowerCase().includes('loss')?'bg-result-loss':r.result?.toLowerCase().includes('push')?'bg-result-push':'bg-result-unknown';
        const safeTarget = r._suggestion ? r._suggestion.replace(/'/g, "\\'") : '';
        const unitClass = (parseFloat(r.units) > 10) ? 'text-red-600 font-bold' : 'text-blue-600';
        const oddsDisplay = (r.odds === null || r.odds === undefined || r.odds === 'null') ? '' : r.odds;

        const suggestionHTML = r._suggestion ? `
            <div class="flex items-center gap-2 mt-1 animate-pulse">
                <div class="text-[10px] bg-amber-50 text-amber-800 px-2 py-1 rounded border border-amber-200 cursor-pointer hover:bg-amber-100 flex-grow truncate" 
                     onclick="combinedDataCache[${i}].capper_name='${safeTarget}'; delete combinedDataCache[${i}]._suggestion; renderTable()">
                     Did you mean: <strong>${r._suggestion}</strong>?
                </div>
                <button onclick="event.stopPropagation(); fixAllSimilar('${safeTarget}')" class="p-1 bg-green-100 text-green-700 rounded hover:bg-green-200 border border-green-200 shadow-sm transition-colors"><span class="material-icons text-[16px] leading-none">done_all</span></button>
            </div>` : '';

        b.insertAdjacentHTML('beforeend', `
        <tr class="hover:bg-blue-50 border-b border-gray-50 transition-colors ${r._selected ? 'bg-blue-50' : ''}">
            <td class="p-3 text-center"><input type="checkbox" class="custom-checkbox" ${r._selected ? 'checked' : ''} onclick="toggleRow(${i})"></td>
            <td class="p-3 text-center"><button onclick="viewSource(${i})" class="text-gray-400 hover:text-blue-600 transition"><span class="material-icons text-sm">visibility</span></button></td>
            
            <td class="p-3">
                <div contenteditable="true" onblur="updateD(${i},'capper_name',this.innerText)" class="font-bold text-gray-800 outline-none focus:text-blue-700 p-1 ${capperClass}">${r.capper_name||''}</div>
                ${suggestionHTML}
            </td>
            
            <td class="p-3">
                <div contenteditable="true" onblur="updateD(${i},'league',this.innerText)" class="bg-gray-100 px-2 py-0.5 rounded text-xs font-bold text-gray-600 w-fit outline-none ${leagueClass}">${r.league||''}</div>
            </td>
            
            <td class="p-3 text-sm font-medium text-gray-700 min-w-[200px]">
                <div contenteditable="true" onblur="updateD(${i},'pick',this.innerText)" class="outline-none p-1 ${pickClass}">${r.pick || ''}</div>
            </td>
            
            <td class="p-3 text-xs font-mono text-right text-gray-500 outline-none" contenteditable="true" onblur="updateD(${i},'odds',this.innerText)">${oddsDisplay}</td>
            <td class="p-3 text-sm font-bold text-right ${unitClass} outline-none" contenteditable="true" onblur="updateD(${i},'units',this.innerText)">${r.units}</td>
            <td class="p-3 text-center"><span class="px-2 py-1 rounded text-[10px] font-bold uppercase ${cls} outline-none cursor-pointer" contenteditable="true" onblur="updateD(${i},'result',this.innerText)">${r.result||'?'}</span></td>
            <td class="p-3 text-right"><button onclick="deleteRow(${i})" class="text-gray-300 hover:text-red-500 transition"><span class="material-icons text-sm">delete</span></button></td>
        </tr>`);
    });
    
    updateUploadButton(hasErrors);
    updateBatchActions(selCount);
}

function updateUploadButton(hasErrors) {
    const btn = document.querySelector("button[onclick='upload()']");
    if (!btn) return;
    if(hasErrors) {
        btn.classList.add('bg-gray-400', 'cursor-not-allowed');
        btn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
        btn.disabled = true;
        btn.innerHTML = `<span class="material-icons text-sm">warning</span> Fix Errors`;
        
        const t = document.getElementById('toast');
        if(!t.classList.contains('show')) showToast("Please fix highlighted fields before uploading.");
    } else {
        btn.classList.remove('bg-gray-400', 'cursor-not-allowed');
        btn.classList.add('bg-blue-600', 'hover:bg-blue-700');
        btn.disabled = false;
        btn.innerHTML = `<span class="material-icons text-sm">cloud_upload</span> Upload`;
    }
}

function updateBatchActions(count) {
    let bar = document.getElementById('batchActions');
    if (!bar) {
        const container = document.querySelector('#page-4 .card');
        if(container) {
            bar = document.createElement('div'); bar.id = 'batchActions';
            bar.className = 'hidden absolute bottom-0 inset-x-0 bg-white border-t p-4 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] flex justify-between items-center z-20 transition-transform duration-300 transform translate-y-full';
            container.appendChild(bar);
        }
    }
    if (bar) {
        if (count > 0) {
            bar.classList.remove('hidden', 'translate-y-full');
            bar.classList.add('translate-y-0');
            bar.innerHTML = `<span class="font-bold text-gray-700">${count} Selected</span><button onclick="deleteSelectedRows()" class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded shadow-sm text-sm font-bold transition-colors flex items-center gap-2"><span class="material-icons text-sm">delete</span> Delete Selected</button>`;
        } else { 
            bar.classList.add('translate-y-full');
            setTimeout(() => bar.classList.add('hidden'), 300);
        }
    }
}

function toggleSelectAll(cb) { combinedDataCache.forEach(r => r._selected = cb.checked); renderTable(); }
function toggleRow(i) { combinedDataCache[i]._selected = !combinedDataCache[i]._selected; renderTable(); }
function deleteSelectedRows() {
    const initialLen = combinedDataCache.length;
    combinedDataCache = combinedDataCache.filter(r => !r._selected);
    showToast(`Deleted ${initialLen - combinedDataCache.length} rows`);
    renderTable();
}

function fixAllSimilar(targetName) {
    let count = 0;
    combinedDataCache.forEach(row => { if (row._suggestion === targetName) { row.capper_name = targetName; delete row._suggestion; count++; } });
    if (count > 0) { showToast(`Fixed ${count} occurrences`); renderTable(); }
}

function updateD(i,k,v) { 
    combinedDataCache[i][k]=v; 
    renderTable(); // Re-render immediately to clear error states if fixed
}

// --- NEW DELETE MODAL LOGIC ---
function deleteRow(i) {
    pendingDeleteIndex = i;
    const modal = document.getElementById('customDeleteModal');
    const content = document.getElementById('customDeleteContent');
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        content.classList.remove('scale-95');
        content.classList.add('scale-100');
    }, 10);
}

function confirmDelete() {
    if (pendingDeleteIndex > -1) {
        combinedDataCache.splice(pendingDeleteIndex, 1);
        renderTable();
        closeDeleteModal();
        showToast('Pick deleted');
    }
}

function closeDeleteModal() {
    const modal = document.getElementById('customDeleteModal');
    const content = document.getElementById('customDeleteContent');
    modal.classList.add('opacity-0');
    content.classList.remove('scale-100');
    content.classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
        pendingDeleteIndex = -1;
    }, 300);
}

function addNewRow() { combinedDataCache.push({capper_name:'Unknown',pick:'New Pick',odds:'',units:1,result:'Unknown',_selected:false}); renderTable(); }

async function upload() {
    const invalid = combinedDataCache.some(r => !r.capper_name || r.capper_name === 'Unknown' || !r.league || !r.pick);
    if(invalid) { renderTable(); return; }

    const btn=document.querySelector("button[onclick='upload()']"); const og=btn.innerText; btn.innerText='Uploading...';
    try { 
        // MODIFIED: Include date from input
        const targetDate = document.getElementById('targetDate').value;
        const res = await fetch('/api/upload', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
                picks: combinedDataCache,
                date: targetDate
            })
        }); 
        const data = await res.json();
        
        if(data.success) {
            showToast(`Success! Uploaded ${data.count} picks.`);
            if(data.details && data.details.length > 0) {
                alert("Upload complete with some warnings:\n" + data.details.join("\n"));
            }
        } else {
            alert("Upload Failed:\n" + (data.error || "Unknown error") + "\n" + (data.details ? data.details.join("\n") : ""));
        }
    }
    catch(e){alert("Network Error: " + e);} finally{btn.innerText=og;}
}

// --- MODALS & HELPERS ---
function openModal(src) { document.getElementById('modalImg').src=src; document.getElementById('imageModal').classList.remove('hidden'); }
function closeModal() { document.getElementById('imageModal').classList.add('hidden'); }

function copyText(id, btnElement) { 
    const el = document.getElementById(id); if (!el) return;
    const txt = el.value || el.innerText;
    
    const originalText = btnElement ? btnElement.innerText : '';

    navigator.clipboard.writeText(txt).then(() => {
        showToast('Copied to clipboard!');
        if(btnElement) {
            btnElement.innerText = 'Copied!';
            btnElement.classList.add('bg-green-50', 'text-green-600', 'border-green-200');
            setTimeout(() => {
                btnElement.innerText = originalText;
                btnElement.classList.remove('bg-green-50', 'text-green-600', 'border-green-200');
            }, 2000);
        }
    }).catch(err => {
        console.error("Clipboard API failed", err);
        alert("Copy failed. Please select text manually.");
    });
}

function exportDebugData() { 
    const debugExport = fetchedMessages.filter(m => m.selected).map(msg => {
        return {
            source_message: {
                id: msg.id,
                channel: msg.channel_name,
                date: msg.date,
                caption: msg.text,
                raw_ocr: msg.ocr_text
            },
            extracted_picks: combinedDataCache.filter(p => p.message_id === msg.id)
        };
    });
    navigator.clipboard.writeText(JSON.stringify(debugExport,null,2)); 
    showToast('Full Debug Data Copied'); 
}

function viewSource(i) {
    const p = combinedDataCache[i], m = fetchedMessages.find(x=>x.id===p.message_id); 
    if(!m) return alert('Original message not found in cache');
    document.getElementById('sourceModalText').innerText = m.text || '[No Caption]'; 
    document.getElementById('sourceModalOCR').innerText = m.ocr_text || '[No OCR Data]';
    const ic = document.getElementById('sourceModalImageContainer'), img = document.getElementById('sourceModalImg');
    if(m.image){
        ic.classList.remove('hidden'); ic.classList.add('flex'); img.src = m.image;
        img.onclick = () => openModal(m.image); img.style.cursor = 'zoom-in';
    } else { ic.classList.add('hidden'); ic.classList.remove('flex'); }
    document.getElementById('sourceModal').classList.remove('hidden'); 
    setTimeout(()=>document.getElementById('sourceModal').classList.remove('opacity-0'),10);
}

function closeSourceModal() { const m=document.getElementById('sourceModal'); m.classList.add('opacity-0'); setTimeout(()=>m.classList.add('hidden'),200); }
function sortTable(k) { sortOrder[k]=!sortOrder[k]; combinedDataCache.sort((a,b)=>(a[k]||'').localeCompare(b[k]||'')*(sortOrder[k]?1:-1)); renderTable(); }

// --- APP HEARTBEAT ---
setInterval(() => { fetch('/api/heartbeat', { method: 'POST' }).catch(() => {}); }, 2000);

// --- ADDED: Copy Raw OCR Function ---
function copyRawOCR() {
    const selected = fetchedMessages.filter(m => m.selected);
    
    if (selected.length === 0) {
        showToast("No messages selected");
        return;
    }

    let combinedText = "";
    
    selected.forEach((m, index) => {
        combinedText += `--- Message ${index + 1} [${m.channel_name}] ---\n`;
        if (m.text) combinedText += `[CAPTION]:\n${m.text}\n`;
        if (m.ocr_text) combinedText += `[OCR]:\n${m.ocr_text}\n`;
        combinedText += "\n========================================\n\n";
    });

    navigator.clipboard.writeText(combinedText).then(() => {
        showToast(`Copied ${selected.length} items to clipboard!`);
    }).catch(err => {
        console.error('Async: Could not copy text: ', err);
        alert("Failed to copy to clipboard.");
    });
}
