// Le frontend interroge le backend toutes les 10 secondes.
// Plus tard, on pourra remplacer ce polling par des WebSockets pour du vrai temps réel.
async function refreshDays() {
  try {
    const response = await fetch("/api/days");
    if (!response.ok) return;
    const days = await response.json();
    document.querySelectorAll(".day-card").forEach((card, index) => {
      const day = days[index];
      if (!day) return;
      const availability = card.querySelector(".available, .full");
      if (availability) {
        availability.textContent = day.remaining > 0
          ? `🟢 ${day.remaining} place${day.remaining > 1 ? "s" : ""} disponible${day.remaining > 1 ? "s" : ""}`
          : "🔴 Complet";
      }
    });
  } catch (e) {
    console.log("Actualisation indisponible");
  }
}
setInterval(refreshDays, 10000);
