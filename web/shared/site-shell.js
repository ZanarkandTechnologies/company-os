export function setupSiteShell({navSelector = "[data-section-nav]"} = {}) {
  const nav = document.querySelector(navSelector);
  const year = String(new Date().getFullYear());
  document.querySelectorAll("[data-current-year]").forEach((node) => {
    node.textContent = year;
  });

  if (!nav || !("IntersectionObserver" in window)) return;
  const links = [...nav.querySelectorAll('a[href^="#"]')];
  const sections = links.flatMap((link) => {
    const section = document.querySelector(link.getAttribute("href"));
    return section ? [{link, section}] : [];
  });
  if (!sections.length) return;

  const setActive = (id) => {
    for (const {link, section} of sections) {
      const active = section.id === id;
      link.toggleAttribute("data-active", active);
      if (active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
  };

  const observer = new IntersectionObserver((entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (visible) setActive(visible.target.id);
  }, {rootMargin: "-20% 0px -65%", threshold: [0, 0.25, 0.6]});

  sections.forEach(({section}) => observer.observe(section));
}
