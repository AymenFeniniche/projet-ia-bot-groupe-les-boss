let sessionId = null;

function el(id) {
    return document.getElementById(id);
}

function addBubble(text, who) {
    const messages = el("messages");
    const div = document.createElement("div");
    div.className = `bubble ${who}`;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function setLoading(active) {
    let node = document.getElementById("loading");
    if (active && !node) {
        node = document.createElement("div");
        node.id = "loading";
        node.className = "loading";
        node.textContent = "Le bot réfléchit…";
        el("messages").appendChild(node);
        el("messages").scrollTop = el("messages").scrollHeight;
    }
    if (!active && node) node.remove();
}

function renderToolCalls(toolCalls) {
    const box = el("tools");
    box.innerHTML = "";

    if (!toolCalls || toolCalls.length === 0) {
        box.textContent = "Aucun appel d’outil pour ce message.";
        return;
    }

    toolCalls.forEach(call => {
        const item = document.createElement("div");
        item.className = "tool-item";
        item.innerHTML = `<strong>${call.tool}</strong><code>${JSON.stringify(call.args, null, 2)}</code>`;
        box.appendChild(item);
    });
}

function renderSources(sources) {
    const box = el("sources");
    box.innerHTML = "";

    if (!sources || sources.length === 0) {
        box.textContent = "Aucune source.";
        return;
    }

    sources.forEach(src => {
        const a = document.createElement("a");
        a.href = src;
        a.target = "_blank";
        a.rel = "noreferrer";
        a.textContent = src;
        box.appendChild(a);
    });
}

async function newSession() {
    const r = await fetch("/api/session/new", { method: "POST" });

    const raw = await r.text();
    if (!r.ok) {
        console.error("Session error:", raw);
        throw new Error("Session error: " + raw);
    }

    const j = JSON.parse(raw);
    sessionId = j.session_id;
    console.log("Session:", sessionId);
}

async function sendMessage() {
    const input = el("msg");
    const message = input.value.trim();
    if (!message) return;

    addBubble(message, "user");
    input.value = "";
    input.focus();

    setLoading(true);

    try {
        console.log("Sending to /api/chat:", message);

        const r = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, message })
        });

        // on lit d'abord en texte
        const raw = await r.text();

        // si erreur backend (ex: 500), on affiche le contenu brut
        if (!r.ok) {
            setLoading(false);
            console.error("Backend error:", raw);
            addBubble("Erreur backend:\n" + raw, "bot");
            return;
        }

        // sinon on parse JSON
        const data = JSON.parse(raw);
        console.log("Response:", data);

        setLoading(false);
        addBubble(data.answer || "(réponse vide)", "bot");
        renderToolCalls(data.tool_calls);
        renderSources(data.sources);

    } catch (err) {
        setLoading(false);
        addBubble("Erreur réseau lors de la communication avec le backend.", "bot");
        console.error(err);
    }
}

function wireUI() {
    const sendBtn = el("send");
    const msgInput = el("msg");

    if (!sendBtn || !msgInput) {
        console.error("UI not found. Check IDs in chat.html");
        return;
    }

    sendBtn.onclick = sendMessage;
    msgInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendMessage();
    });
}

window.addEventListener("DOMContentLoaded", async () => {
    console.log("DOM loaded. Initializing…");
    wireUI();

    try {
        await newSession();
        addBubble("Bonjour 👋 Pose-moi une question sur les films/séries !", "bot");
    } catch (e) {
        addBubble("Impossible de créer une session.\nVérifie que le backend tourne.", "bot");
        console.error(e);
    }
});
