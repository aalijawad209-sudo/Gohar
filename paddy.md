const API_URL = "http://127.0.0.1:8000/chat";
const welcome = document.getElementById("welcome");
const conversation = document.getElementById("conversation");
const form = document.getElementById("chatForm");
const input = document.getElementById("question");
const newChat = document.getElementById("newChat");

function addMessage(role, content, source = "") {
  const row = document.createElement("div");
  row.className = `message ${role}`;
  if (role === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "🌾";
    row.appendChild(avatar);
  }
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (role === "assistant") {
    const title = document.createElement("div");
    title.className = "answer-title";
    title.textContent = "Gohar ki salah";
    bubble.appendChild(title);
  }
  const body = document.createElement("div");
  body.textContent = content;
  bubble.appendChild(body);
  if (source) {
    const note = document.createElement("div");
    note.className = "source-note";
    note.textContent = source;
    bubble.appendChild(note);
  }
  row.appendChild(bubble);
  conversation.appendChild(row);
  conversation.scrollTop = conversation.scrollHeight;
  return row;
}

function showConversation() {
  welcome.classList.add("hidden");
  conversation.classList.remove("hidden");
}
function resetChat() {
  conversation.replaceChildren();
  conversation.classList.add("hidden");
  welcome.classList.remove("hidden");
  input.value = "";
  input.focus();
}
newChat.addEventListener("click", resetChat);

document.querySelectorAll("[data-prompt]").forEach(button => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt;
    form.requestSubmit();
  });
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 120) + "px";
});

function demoAnswer(question) {
  const q = question.toLowerCase();
  if (q.includes("mausam") || q.includes("baarish") || q.includes("weather")) {
    return "Mausam ki live jaankari is demo mein connected nahi hai. Apne district ka latest forecast IMD ya kisi trusted weather service se check karein. Baarish ki sambhavna ho toh pesticide/fertiliser apply karne se pehle local advisory aur product label dekhein.";
  }
  if (q.includes("khaad") || q.includes("fertili") || q.includes("nitrogen") || q.includes("urea")) {
    return "Sahi khaad aur quantity crop, crop age, soil test aur pehle di gayi khaad par depend karti hai. Pehle crop ka naam, kitne din ki fasal hai aur soil-test details batayein. Bina in details ke exact dose suggest karna safe nahi hoga.";
  }
  if (q.includes("keede") || q.includes("pest") || q.includes("rog") || q.includes("disease")) {
    return "Keede ya rog ki sahi pehchaan ke liye crop ka naam, fasal ki age, affected hissa aur symptoms jaan-na zaroori hai. Agar possible ho toh clear photo kisi local krishi expert ko dikhayein. Bina identification ke pesticide use na karein.";
  }
  return "Patte peele hone ke kai kaaran ho sakte hain, jaise nutrient deficiency, paani ka jama hona ya disease. Pehle check karein ki paani toh nahi ruk raha aur pīlāpan purane patton mein hai ya naye patton mein. Aapki fasal kaunsi hai aur kitne din ki hai? Is demo mein answer rule-based hai; Gemma integration backend setup ke baad chalegi.";
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  showConversation();
  addMessage("user", question);
  input.value = "";
  input.style.height = "auto";
  const loading = addMessage("assistant", "Sawal samajh raha hoon...");
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question})
    });
    if (!response.ok) throw new Error("API unavailable");
    const data = await response.json();
    loading.remove();
    addMessage("assistant", data.answer, data.source ? `Knowledge source: ${data.source}` : "AI-generated response. Important decisions ko local agricultural expert se verify karein.");
  } catch (error) {
    loading.remove();
    addMessage("assistant", demoAnswer(question), "Demo response — live Gemma backend abhi connected nahi hai. Farming decisions ko trusted local guidance se verify karein.");
  }
});
