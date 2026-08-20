export const COMPANY_CHANGE_ROUTES = Object.freeze({
  fact: {
    label: "Fact",
    destination: "Company wiki",
    record: "Sourced fact + freshness",
    owner: "Knowledge steward",
    outcome: "Queryable by people and agents at task time.",
    note: "Facts are checked, refreshed, and superseded in the wiki. They do not become private agent memory.",
    tone: "signal"
  },
  decision: {
    label: "Decision",
    destination: "Decision ledger",
    record: "Rationale + approval + responsibility",
    owner: "Named approver and accountable owner",
    outcome: "Auditable before it changes policy or procedure.",
    note: "The ledger preserves context, options, decision, scope, approver, owner, dates, and supersession.",
    tone: "orange"
  },
  procedure: {
    label: "Procedure",
    destination: "Skill compiler",
    record: "Approved procedure + decision refs",
    owner: "Procedure owner",
    outcome: "Versioned skill with guardrails and evals.",
    note: "Only an approved procedure is dreamed into a skill. Facts remain queries; decisions remain ledger records.",
    tone: "signal"
  },
  app: {
    label: "App change",
    destination: "Connected application",
    record: "Application transaction or integration change",
    owner: "Business or integration owner",
    outcome: "The application remains the system of record.",
    note: "People update the app as usual, directly or with agent assistance through the reviewed integration layer.",
    tone: "neutral"
  }
});

export function mountSystemRouter(root, routes = COMPANY_CHANGE_ROUTES) {
  if (!root) return;
  const tabs = [...root.querySelectorAll("[data-route]")];
  const fields = {
    destination: root.querySelector("[data-route-destination]"),
    record: root.querySelector("[data-route-record]"),
    owner: root.querySelector("[data-route-owner]"),
    outcome: root.querySelector("[data-route-outcome]"),
    note: root.querySelector("[data-route-note]"),
    status: root.querySelector("[data-route-status]")
  };
  if (!tabs.length || Object.values(fields).some((field) => !field)) return;

  const select = (key, {focus = false, reflectUrl = true} = {}) => {
    const route = routes[key];
    const tab = tabs.find((candidate) => candidate.dataset.route === key);
    if (!route || !tab) return;
    tabs.forEach((candidate) => {
      const selected = candidate === tab;
      candidate.setAttribute("aria-selected", String(selected));
      candidate.tabIndex = selected ? 0 : -1;
    });
    fields.destination.textContent = route.destination;
    fields.record.textContent = route.record;
    fields.owner.textContent = route.owner;
    fields.outcome.textContent = route.outcome;
    fields.note.textContent = route.note;
    fields.status.className = `route-status route-status--${route.tone}`;
    fields.status.textContent = route.tone === "orange" ? "Approval required" : route.tone === "signal" ? "Durable route" : "System owned";
    root.querySelector('[role="tabpanel"]')?.setAttribute("aria-labelledby", tab.id);
    root.dataset.activeRoute = key;
    if (reflectUrl) {
      const url = new URL(window.location.href);
      url.searchParams.set("change", key);
      window.history.replaceState(null, "", url);
    }
    if (focus) tab.focus();
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => select(tab.dataset.route));
    tab.addEventListener("keydown", (event) => {
      let nextIndex = null;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") nextIndex = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;
      if (nextIndex === null) return;
      event.preventDefault();
      select(tabs[nextIndex].dataset.route, {focus: true});
    });
  });

  const requested = new URL(window.location.href).searchParams.get("change");
  const selected = tabs.find((tab) => tab.dataset.route === requested)
    ?? tabs.find((tab) => tab.getAttribute("aria-selected") === "true")
    ?? tabs[0];
  select(selected.dataset.route, {reflectUrl: false});
}
