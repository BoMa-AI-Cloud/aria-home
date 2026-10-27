type Total = { cases: number; fully_correct: number };

const labels: Array<[string, string]> = [
  ["combined", "Combined (all sources)"],
  ["thermostat_only", "Thermostat only"],
  ["room_sensor_only", "Room sensor only"],
  ["electrical_only", "Electrical only"],
  ["calendar_only", "Calendar only"],
];

let evaluationLoaded = false;

async function loadEvaluation() {
  if (evaluationLoaded) return;
  evaluationLoaded = true;
  const response = await fetch("/api/evaluation/offline");
  if (!response.ok) throw new Error("evaluation results unavailable");
  const data = (await response.json()) as { totals: Record<string, Total> };
  const tbody = document.getElementById("evaluation-rows");
  const note = document.getElementById("evaluation-note");
  if (!tbody || !note) return;
  for (const [key, label] of labels) {
    const total = data.totals[key];
    if (!total) continue;
    const row = document.createElement("tr");
    const condition = document.createElement("td");
    condition.textContent = label;
    const score = document.createElement("td");
    score.textContent = `${total.fully_correct}/${total.cases}`;
    row.append(condition, score);
    tbody.append(row);
  }
  const combined = data.totals["combined"];
  if (combined) {
    note.textContent = `${combined.cases} builder-labelled synthetic cases. Not a benchmark of real homes.`;
  }
}

function showCard() {
  const name = window.location.hash.replace("#", "") || "opening";
  document.querySelectorAll<HTMLElement>("[data-card]").forEach((section) => {
    section.hidden = section.dataset.card !== name;
  });
  if (name === "evaluation") void loadEvaluation();
}

window.addEventListener("hashchange", showCard);
showCard();
