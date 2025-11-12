const API = location.origin; // FastAPI serves frontend too

// Tabs
document.querySelectorAll(".nav-btn").forEach(btn=>{
  btn.onclick=()=> {
    document.querySelectorAll(".nav-btn").forEach(b=>b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
  };
});

const policySelect = document.getElementById("policySelect");
const policySelect2 = document.getElementById("policySelect2");
const downloadBtn = document.getElementById("downloadBtn");

async function loadPolicies() {
  const res = await fetch(`${API}/api/policies`);
  const data = await res.json();
  const opts = (data.policies || []);
  const fill = (sel)=> sel.innerHTML = opts.map(p=>`<option value="${p}">${p}</option>`).join("");
  fill(policySelect); fill(policySelect2);
}
loadPolicies();

// Download from library
downloadBtn.onclick = async ()=>{
  const name = policySelect.value;
  if (!name) return;
  // backend serves static files only as list – so we provide hint:
  alert("Download is available from Streamlit version. For FastAPI, open your /backend/policies folder directly, or extend API to serve files.");
};

// ---- Upload/choose & ask ----
let currentTempDoc = null; // temp doc_id for uploaded file
const uploadBtn = document.getElementById("uploadBtn");
const fileInput = document.getElementById("fileInput");
const uploadInfo = document.getElementById("uploadInfo");
const useLibraryBtn = document.getElementById("useLibraryBtn");

uploadBtn.onclick = async ()=>{
  const f = fileInput.files?.[0];
  if(!f){ alert("Choose a PDF first."); return; }
  const fd = new FormData(); fd.append("file", f);
  uploadInfo.textContent = "Uploading and indexing…";
  const res = await fetch(`${API}/api/upload-temp`, { method:"POST", body: fd });
  const data = await res.json();
  currentTempDoc = data.temp_doc_id;
  uploadInfo.textContent = `Uploaded: ${data.filename}`;
};

useLibraryBtn.onclick = ()=>{
  currentTempDoc = null; // ensure we use selected policy, not temp
  uploadInfo.textContent = `Using policy: ${policySelect2.value}`;
};

const docQuestion = document.getElementById("docQuestion");
const askDocBtn = document.getElementById("askDocBtn");
const summDocBtn = document.getElementById("summDocBtn");
const docChat = document.getElementById("docChat");

function pushMsg(el, who, text){
  const div = document.createElement("div");
  div.className = `msg ${who}`;
  div.textContent = text;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

askDocBtn.onclick = async ()=>{
  const q = docQuestion.value.trim();
  if(!q){ return; }
  pushMsg(docChat, "user", q);

  const payload = currentTempDoc
    ? { question: q, temp_doc_id: currentTempDoc }
    : { question: q, policy_name: policySelect2.value };

  const res = await fetch(`${API}/api/ask`, {
    method:"POST", headers:{ "Content-Type":"application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  pushMsg(docChat, "bot", data.answer || "No answer.");
};

summDocBtn.onclick = async ()=>{
  const q = "Summarize the key points and entitlements from this policy in 5 bullet points.";
  pushMsg(docChat, "user", q);

  const payload = currentTempDoc
    ? { question: q, temp_doc_id: currentTempDoc }
    : { question: q, policy_name: policySelect2.value };

  const res = await fetch(`${API}/api/ask`, {
    method:"POST", headers:{ "Content-Type":"application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  pushMsg(docChat, "bot", data.answer || "No answer.");
};

// ---- General assistant ----
const genQuestion = document.getElementById("genQuestion");
const genChat = document.getElementById("genChat");
document.getElementById("askGenBtn").onclick = async ()=>{
  const q = genQuestion.value.trim();
  if(!q) return;
  pushMsg(genChat, "user", q);
  const res = await fetch(`${API}/api/ask`, {
    method:"POST", headers:{ "Content-Type": "application/json" },
    body: JSON.stringify({ question: q })
  });
  const data = await res.json();
  pushMsg(genChat, "bot", data.answer || "No answer.");
};