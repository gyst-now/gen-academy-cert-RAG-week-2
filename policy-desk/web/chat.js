const form = document.querySelector("#chat");
const input = document.querySelector("#question");
const submit = document.querySelector("#submit");
const log = document.querySelector("#conversation");
const mode = document.querySelector("#mode");
const access = document.querySelector("#access");
const accessWrap = document.querySelector("#access-wrap");
let previousQuestion = null;

fetch("/api/status").then(response => response.json()).then(status => {
  mode.textContent = status.snapshot_ready
    ? (status.generation ? "Cited policy answers" : "Evidence search")
    : "Snapshot required";
  accessWrap.hidden = !status.access_code_required;
}).catch(() => { mode.textContent = "Status unavailable"; });

for (const button of document.querySelectorAll("#examples button")) {
  button.addEventListener("click", () => {
    previousQuestion = null;
    input.value = button.textContent;
    input.focus();
  });
}

function message(text, who) {
  const bubble = document.createElement("article");
  bubble.className = "message " + who;
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  bubble.append(paragraph);
  log.append(bubble);
  return bubble;
}

function addSource(bubble, source, number) {
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  const link = document.createElement("a");
  link.href = source.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = number + ". " + source.title + " · " + source.section;
  summary.append(link);
  const excerpt = document.createElement("p");
  excerpt.textContent = source.excerpt;
  details.append(summary, excerpt);
  bubble.append(details);
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question || submit.disabled) return;
  const context = previousQuestion;
  message(question, "user");
  input.value = "";
  input.disabled = true;
  submit.disabled = true;
  const bubble = message("Searching the handbook…", "assistant");
  bubble.scrollIntoView({block: "nearest"});
  try {
    const headers = {"Content-Type": "application/json"};
    if (access.value) headers["X-Demo-Access"] = access.value;
    const response = await fetch("/api/chat", {
      method: "POST",
      headers,
      body: JSON.stringify({question, previous_question: context}),
    });
    const data = await response.json();
    if (!response.ok) {
      if (response.status === 401) accessWrap.hidden = false;
      throw new Error(typeof data.detail === "string" ? data.detail : "Search failed.");
    }
    bubble.firstChild.textContent = data.answer;
    data.sources.forEach((source, index) => addSource(bubble, source, index + 1));
    previousQuestion = data.status === "clarify"
      ? [context, question].filter(Boolean).join(" ").slice(-1200)
      : null;
  } catch (error) {
    bubble.firstChild.textContent = error.message;
    input.value = question;
  } finally {
    input.disabled = false;
    submit.disabled = false;
    input.focus();
  }
});
