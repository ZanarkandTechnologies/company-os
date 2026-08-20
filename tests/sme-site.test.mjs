import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {resolve} from "node:path";
import test from "node:test";
import {createSmeSiteServer} from "../scripts/serve-sme-site.mjs";
import {COMPANY_CHANGE_ROUTES} from "../web/shared/system-router.js";

const projectRoot = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(projectRoot, path), "utf8");

test("SME site uses the shared Hermes brandkit and exposes the durable operating model", () => {
  const html = read("web/sme/index.html");
  const brandkit = read("web/shared/hermes-brandkit.css");
  const site = read("web/sme/site.css");

  assert.match(html, /\/shared\/hermes-brandkit\.css/);
  assert.match(html, /\/shared\/site-shell\.js|\/sme\/app\.js/);
  assert.match(html, /Connected applications/);
  assert.match(html, /Company wiki/);
  assert.match(html, /Decision ledger/);
  assert.match(html, /No agent memory[\s\S]*required/);
  assert.match(html, /Approved by/);
  assert.match(html, /Responsible/);
  assert.match(html, /Supersedes/);
  assert.match(html, /Dream into skill/);
  assert.match(html, /prefers-reduced-motion|app\.js/);
  assert.doesNotMatch(html, /gradient|glass|99\.99|trusted by|agent brain/i);

  for (const token of ["#090a08", "#ede9df", "#c8ff57", "#d36a32"]) assert.match(brandkit, new RegExp(token));
  assert.match(brandkit, /font-family: var\(--h-font-sans\)/);
  assert.match(brandkit, /border-radius: 0/);
  assert.match(brandkit, /:focus-visible/);
  assert.match(brandkit, /prefers-reduced-motion/);
  assert.ok([...site.matchAll(/border-radius:\s*([^;]+);/g)].every((match) => match[1].trim() === "0"));
});

test("company change router has one canonical durable destination per change type", () => {
  assert.deepEqual(Object.keys(COMPANY_CHANGE_ROUTES).sort(), ["app", "decision", "fact", "procedure"]);
  assert.equal(COMPANY_CHANGE_ROUTES.app.destination, "Connected application");
  assert.equal(COMPANY_CHANGE_ROUTES.fact.destination, "Company wiki");
  assert.equal(COMPANY_CHANGE_ROUTES.decision.destination, "Decision ledger");
  assert.equal(COMPANY_CHANGE_ROUTES.procedure.destination, "Skill compiler");
  assert.match(COMPANY_CHANGE_ROUTES.decision.record, /approval \+ responsibility/);
  assert.match(COMPANY_CHANGE_ROUTES.procedure.outcome, /Versioned skill/);
});

test("SME static server exposes the site and shared modules without path escape", async () => {
  const server = createSmeSiteServer();
  await new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolveListen);
  });
  const {port} = server.address();
  const baseUrl = `http://127.0.0.1:${port}`;
  try {
    const root = await fetch(`${baseUrl}/`, {redirect: "manual"});
    assert.equal(root.status, 302);
    assert.equal(root.headers.get("location"), "/sme/");

    const page = await fetch(`${baseUrl}/sme/`);
    assert.equal(page.status, 200);
    assert.match(page.headers.get("content-type"), /text\/html/);
    assert.match(await page.text(), /Hermes SME/);

    const css = await fetch(`${baseUrl}/shared/hermes-brandkit.css`);
    assert.equal(css.status, 200);
    assert.match(css.headers.get("content-type"), /text\/css/);

    const module = await fetch(`${baseUrl}/shared/system-router.js`);
    assert.equal(module.status, 200);
    assert.match(module.headers.get("content-type"), /application\/javascript/);

    const escape = await fetch(`${baseUrl}/shared/%2e%2e/%2e%2e/package.json`);
    assert.equal(escape.status, 404);
  } finally {
    await new Promise((resolveClose) => server.close(resolveClose));
  }
});
