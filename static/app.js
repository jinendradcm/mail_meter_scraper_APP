let uploadedFile = "";
let isScraping = false;

// Initialize Lucide icons helper
function refreshIcons() {
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

// Drag and Drop Logic
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileNameDisplay = document.getElementById('fileNameDisplay');

if (dropZone) {
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragging');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragging');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragging');
        const files = e.dataTransfer.files;
        if (files.length) {
            fileInput.files = files;
            handleFileSelect();
        }
    });

    fileInput.addEventListener('change', handleFileSelect);
}

function handleFileSelect() {
    if (fileInput.files.length > 0) {
        fileNameDisplay.innerText = `Selected: ${fileInput.files[0].name}`;
        fileNameDisplay.style.display = 'block';
        addLog(`File selected: ${fileInput.files[0].name}`, 'info');
    }
}

function addLog(message, type = 'info') {
    const logsDiv = document.getElementById("logs");
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour12: false });
    
    const entry = document.createElement("div");
    entry.className = `log-entry ${type === 'success' ? 'log-success' : type === 'error' ? 'log-error' : ''}`;
    
    // Check for Worker/Tab prefix in message
    let w_t_prefix = "";
    if (message.startsWith("[W") || message.startsWith("[Worker")) {
        const parts = message.split("] ");
        if (parts.length > 1) {
            w_t_prefix = parts[0] + "] ";
            message = parts.slice(1).join("] ");
        }
    }

    entry.innerHTML = `
        <span class="log-time">[${timeStr}]</span>
        ${w_t_prefix ? `<span class="log-w-t">${w_t_prefix}</span>` : ''}
        <span class="log-msg">${message}</span>
    `;
    
    logsDiv.appendChild(entry);
    logsDiv.scrollTop = logsDiv.scrollHeight;
}

async function upload() {
    const file = fileInput.files[0];
    if (!file) {
        addLog("Error: No file selected for upload", "error");
        return;
    }

    const uploadBtn = document.getElementById("uploadBtn");
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = `<i data-lucide="loader" class="pulsing" width="18"></i> Uploading...`;
    refreshIcons();

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/upload", {
            method: "POST",
            body: formData,
        });

        const data = await res.json();
        uploadedFile = data.file;

        addLog(`Upload successful: ${file.name}`, 'success');
        document.getElementById("startBtn").disabled = false;
        
        uploadBtn.innerHTML = `<i data-lucide="check-circle" width="18"></i> File Ready`;
        uploadBtn.classList.remove("btn-primary");
        uploadBtn.classList.add("btn-success");
        refreshIcons();
    } catch (err) {
        addLog(`Upload failed: ${err.message}`, 'error');
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = `<i data-lucide="check-circle" width="18"></i> Retry Upload`;
        refreshIcons();
    }
}

async function start() {
    if (!uploadedFile) return;

    const workers = parseInt(document.getElementById("workers").value);
    const tabs = parseInt(document.getElementById("tabs").value);
    const startBtn = document.getElementById("startBtn");

    startBtn.disabled = true;
    startBtn.innerHTML = `<i data-lucide="loader" class="pulsing" width="18"></i> Scraping...`;
    isScraping = true;
    refreshIcons();

    addLog(`Starting scraper with ${workers} workers and ${tabs} tabs/worker...`, 'info');

    try {
        await fetch("/start", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                file_path: uploadedFile,
                workers: workers,
                tabs: tabs,
            }),
        });
    } catch (err) {
        addLog(`Failed to start: ${err.message}`, 'error');
        startBtn.disabled = false;
    }
}

let socket = new WebSocket(`ws://${window.location.host}/ws`);

socket.onmessage = function (event) {
    const msg = event.data;

    if (msg.startsWith("PROGRESS::")) {
        const data = JSON.parse(msg.replace("PROGRESS::", ""));

        document.getElementById("total").innerText = data.total;
        document.getElementById("processed").innerText = data.processed;
        document.getElementById("success").innerText = data.success;
        document.getElementById("failed").innerText = data.failed;
        
        document.getElementById("remainingCount").innerText = data.total - data.processed;

        // Enable download buttons if we have processed something
        if (data.processed > 0) {
            document.getElementById("downloadCsvBtn").disabled = false;
            document.getElementById("downloadJsonBtn").disabled = false;
        }

    } else if (msg === "DONE") {
        addLog("SCRAPING COMPLETED SUCCESSFULLY!", "success");
        isScraping = false;
        
        const startBtn = document.getElementById("startBtn");
        startBtn.disabled = false;
        startBtn.innerHTML = `<i data-lucide="play" width="18"></i> Run Again`;
        refreshIcons();

    } else {
        // Detect result type in log for coloring
        let type = 'info';
        if (msg.includes("FOUND:") || msg.includes("success")) type = 'success';
        if (msg.includes("NOT FOUND") || msg.includes("ERROR")) type = 'error';
        
        addLog(msg, type);
    }
};

socket.onopen = () => {
    console.log("WebSocket connected");
    addLog("Real-time connection established.", "info");
};

socket.onclose = () => {
    addLog("Connection lost. Please refresh the page.", "error");
};

function downloadCSV() {
    window.open("/download/csv", "_blank");
}

function downloadJSON() {
    window.open("/download/json", "_blank");
}
