async function runStokQuery(customCommand) {
  const cmdInput = document.getElementById("stokCommandInput");
  if (customCommand) {
    cmdInput.value = customCommand;
  }
  const command = cmdInput.value.trim() || "[STOK] 219602 WAFER FLAT";
  const statusEl = document.getElementById("stokStatus");
  const waOut = document.getElementById("stokWaOutput");
  const tbody = document.getElementById("stokTableBody");

  statusEl.textContent = "Running " + command + "...";
  try {
    const resp = await fetch("/api/stok/?q=" + encodeURIComponent(command));
    const data = await resp.json();
    waOut.textContent = data.reply_message || "";
    statusEl.textContent =
      "Source: " +
      (data.source_mode || "offline_cache") +
      " | Depo: " +
      (data.depo || "-") +
      " | Wil: " +
      (data.wil || "-") +
      " | Total Items: " +
      (data.total_items || 0);

    tbody.innerHTML = "";
    (data.categories || []).forEach((catObj) => {
      (catObj.items || []).forEach((row, idx) => {
        const tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" +
          (idx + 1) +
          "</td><td><code>" +
          catObj.kategori +
          "</code></td><td class='num'>" +
          row.stok +
          "</td><td>" +
          row.item +
          "</td>";
        tbody.appendChild(tr);
      });
    });
  } catch (err) {
    statusEl.textContent = "Error: " + err.message;
  }
}

function applyCategoryPreset() {
  const wilDepo = document.getElementById("wilDepoInput").value.trim();
  const cat = document.getElementById("kategoriSelect").value;
  const cmd = wilDepo ? `[STOK] ${wilDepo} ${cat}`.trim() : `[STOK] ${cat}`.trim();
  runStokQuery(cmd);
}

async function copyWaText() {
  const txt = document.getElementById("stokWaOutput").textContent;
  if (!txt) return;
  await navigator.clipboard.writeText(txt);
  const btn = document.getElementById("copyWaBtn");
  const old = btn.textContent;
  btn.textContent = "Copied!";
  setTimeout(() => {
    btn.textContent = old;
  }, 1400);
}

window.addEventListener("DOMContentLoaded", () => {
  runStokQuery("[STOK] 219602 WAFER FLAT");
});
