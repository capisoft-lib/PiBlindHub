"use strict";

const tokenPanel = document.getElementById("token-panel");
const controls = document.getElementById("controls");
const tokenForm = document.getElementById("token-form");
const tokenInput = document.getElementById("token");
const connection = document.getElementById("connection");
const message = document.getElementById("message");
let movementHeld = false;
let pollTimer = null;

function token() {
  return sessionStorage.getItem("piblindhub-token") || "";
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token()}`);
  if (options.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, {...options, headers, cache: "no-store"});
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.detail || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return body;
}

async function sendCommand(command) {
  const result = await api("/api/v1/commands", {
    method: "POST",
    body: JSON.stringify({command})
  });
  message.textContent = `${command}: ${result.lifecycle}`;
  return result;
}

async function stopMovement() {
  if (!token()) return;
  movementHeld = false;
  try {
    await sendCommand("stop");
  } catch (error) {
    message.textContent = `STOP non confirmé : ${error.message}`;
  }
}

async function refreshStatus() {
  try {
    const status = await api("/api/v1/status");
    connection.textContent = status.fault ? "Défaut" : "Connecté";
    connection.className = `badge ${status.fault ? "fault" : "online"}`;
    document.getElementById("state").textContent = status.state;
    const position = status.position;
    document.getElementById("position").textContent = position.value === null
      ? "Inconnue"
      : `${position.value.toFixed(1)} % (${position.confidence})`;
    const outputs = status.outputs;
    document.getElementById("outputs").textContent = !status.output_readback_confirmed
      ? "État non confirmé"
      : outputs.up_active ? "Montée active"
        : outputs.down_active ? "Descente active" : "Arrêtées";
    document.getElementById("stop-reason").textContent = status.last_stop_reason || "—";
    if (status.fault) message.textContent = `Défaut : ${status.fault}`;
    tokenPanel.classList.add("hidden");
    controls.classList.remove("hidden");
  } catch (error) {
    connection.textContent = "Hors ligne";
    connection.className = "badge offline";
    if (error.status === 401) disconnect();
  }
}

function disconnect() {
  sessionStorage.removeItem("piblindhub-token");
  controls.classList.add("hidden");
  tokenPanel.classList.remove("hidden");
  connection.textContent = "Hors ligne";
  connection.className = "badge offline";
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
}

function bindHoldButton(id, command) {
  const button = document.getElementById(id);
  button.addEventListener("pointerdown", async event => {
    event.preventDefault();
    button.setPointerCapture(event.pointerId);
    movementHeld = true;
    try {
      await sendCommand(command);
      // A release can race the movement request. Once acceptance is known,
      // send another STOP if release already happened so ordering is safe.
      if (!movementHeld) await stopMovement();
    } catch (error) {
      movementHeld = false;
      message.textContent = error.message;
    }
  });
  for (const eventName of ["pointerup", "pointercancel", "lostpointercapture"]) {
    button.addEventListener(eventName, () => {
      if (movementHeld) stopMovement();
    });
  }
}

tokenForm.addEventListener("submit", async event => {
  event.preventDefault();
  sessionStorage.setItem("piblindhub-token", tokenInput.value.trim());
  tokenInput.value = "";
  await refreshStatus();
  if (!pollTimer) pollTimer = setInterval(refreshStatus, 1000);
});

bindHoldButton("up", "move_up");
bindHoldButton("down", "move_down");
document.getElementById("stop").addEventListener("click", stopMovement);
document.getElementById("disconnect").addEventListener("click", disconnect);
document.addEventListener("visibilitychange", () => {
  if (document.hidden && movementHeld) stopMovement();
});
if (token()) {
  refreshStatus();
  pollTimer = setInterval(refreshStatus, 1000);
}
