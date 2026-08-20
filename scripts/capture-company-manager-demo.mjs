#!/usr/bin/env node
/**
 * Captures a deterministic, local-only browser proof for Howie's inset-panel Gantt dashboard.
 *
 * Usage (the bundled Codex Playwright runtime is supplied by NODE_PATH):
 *   NODE_PATH=/path/to/node_modules HOWIE_PLAYWRIGHT_CHROMIUM=/path/to/chrome \
 *     node scripts/capture-company-manager-demo.mjs --output tickets/TASK-0002/artifacts/browser
 */
import { createRequire } from "node:module";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, resolve } from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const root = resolve(import.meta.dirname, "..");
const defaultOutput = resolve(root, "tickets/TASK-0002/artifacts/inset-panel/browser");
const args = process.argv.slice(2);
const outputFlag = args.indexOf("--output");
const outputDir = outputFlag >= 0 ? resolve(args[outputFlag + 1]) : defaultOutput;
const chromiumPath = process.env.HOWIE_PLAYWRIGHT_CHROMIUM;

if (!chromiumPath) throw new Error("Set HOWIE_PLAYWRIGHT_CHROMIUM to the local Chromium executable.");

mkdirSync(outputDir, { recursive: true });
const workspace = mkdtempSync(resolve(tmpdir(), "howie-dependency-browser-"));
const consoleErrors = [];
const steps = [];
let server;
let browser;

const sleep = milliseconds => new Promise(resolveSleep => setTimeout(resolveSleep, milliseconds));

async function capture(page, name, observation, options = {}) {
  const path = resolve(outputDir, `${name}.png`);
  await page.screenshot({ path, fullPage: options.fullPage ?? true });
  steps.push({ name, screenshot: `browser/${basename(path)}`, observation });
}

async function clickAction(page, action, expectedText) {
  await page.locator(`[data-action="${action}"]`).first().click();
  await page.waitForFunction(text => document.body.textContent?.includes(text), expectedText);
  await sleep(650);
}

async function selectPage(page, view) {
  await page.locator(`[data-page="${view}"]`).click();
  await page.waitForFunction(expected => document.querySelector(`[data-page="${expected}"]`)?.getAttribute("aria-pressed") === "true", view);
  await sleep(120);
}

async function runEvals(page) {
  await page.locator("[data-eval-run]").click();
  await page.waitForFunction(() => document.getElementById("eval-summary")?.textContent?.includes("3 passed · 0 gaps · 0 errors"));
  await page.waitForFunction(() => document.querySelectorAll(".eval-message").length >= 4);
  await sleep(180);
}

try {
  process.env.HOWIE_DASHBOARD_WORKSPACE_PATH = workspace;
  const { createDashboardServer } = await import(`./serve-dashboard.mjs?dependency-browser-proof=${Date.now()}`);
  server = createDashboardServer();
  await new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolveListen);
  });
  const address = server.address();
  const baseUrl = `http://127.0.0.1:${address.port}`;

  browser = await chromium.launch({ executablePath: chromiumPath, headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.on("console", message => {
    if (message.type() === "error" && !message.text().includes("favicon.ico")) consoleErrors.push(message.text());
  });
  page.on("response", response => {
    if (response.status() >= 400) consoleErrors.push(`HTTP ${response.status()} ${response.url()}`);
  });
  page.on("pageerror", error => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await capture(page, "01-empty-week", "The operating page is a single, empty weekly Gantt without developer controls competing with it.");

  await selectPage(page, "proof");
  await clickAction(page, "seed", "Frozen dependency scenario loaded locally.");
  await selectPage(page, "week");
  await page.waitForFunction(() => document.querySelector('.gantt .bar-wrapper[data-id="TASK-1001"]') && document.querySelector('.gantt .bar-wrapper[data-id="TASK-1002"]'));
  await capture(page, "02-weekly-gantt", "The weekly plan is the dominant surface; each bar carries its status and visible upstream dependency cue.");

  await page.locator('.gantt .bar-wrapper[data-id="TASK-1001"]').click();
  await page.waitForFunction(() => document.getElementById("ticket-drawer")?.getAttribute("aria-hidden") === "false");
  await sleep(280);
  await capture(page, "03-ticket-drawer", "Clicking the upstream report opens a centred ticket modal with owner, next chase, requirements, and downstream output.");
  await page.locator("#drawer-close").click();

  await selectPage(page, "proof");
  await clickAction(page, "preview_human_request", "Telegram request preview recorded. No message was sent.");
  await capture(page, "04-proof-preview", "System Proof records the bounded Telegram preview and keeps its activity trace separate from the operator page.");

  await clickAction(page, "simulate_human_response", "Local simulated reply recorded; readiness recomputed.");
  await clickAction(page, "pulse", "Local pulse completed; eligible local work started and any request remains a preview only.");
  await selectPage(page, "week");
  await capture(page, "05-gantt-ready", "The next local pulse dispatches the dependency-ready mock worker without changing the weekly schedule's shape.");

  await selectPage(page, "proof");
  await clickAction(page, "publish", "Local upstream output published for review.");
  await clickAction(page, "review", "Local review recorded; downstream readiness recomputed.");
  await page.waitForFunction(() => !document.getElementById("toast")?.classList.contains("show"));
  await selectPage(page, "week");
  await page.waitForFunction(() => document.querySelector('.gantt .bar-wrapper[data-id="TASK-1001"]') && document.body.textContent?.includes("Done"));
  await capture(page, "06-gantt-unblocked", "An approved upstream output changes its bar to Done and clears the displayed downstream edge from dependent work.");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('.gantt .bar-wrapper[data-id="TASK-1002"]').click();
  await sleep(280);
  await capture(page, "07-narrow-drawer", "At narrow width, a ticket opens as a full, readable modal without page-level horizontal overflow.", { fullPage: false });
  const narrowViewport = await page.evaluate(() => ({
    width: window.innerWidth,
    height: window.innerHeight,
    documentWidth: document.documentElement.scrollWidth,
    hasPageHorizontalOverflow: document.documentElement.scrollWidth > window.innerWidth
  }));

  await page.setViewportSize({ width: 1440, height: 980 });
  await page.locator("#drawer-close").click();
  await selectPage(page, "evals");
  await runEvals(page);
  await capture(page, "08-eval-trace", "The Evals tab stages the mock Drive and meeting summary in an isolated workspace, renders the actual local trace, and lists the resulting files without mutating the company board.");

  const report = {
    ticket_id: "TASK-0002-inset-panel",
    base_url: "local ephemeral server",
    viewport: { width: 1440, height: 980 },
    lifecycle: ["empty weekly plan", "seeded Gantt", "ticket drawer", "telegram preview", "simulated reply", "eligible upstream work", "approved upstream output", "narrow ticket drawer", "isolated filesystem eval trace"],
    console_errors: consoleErrors,
    narrow_viewport: narrowViewport,
    screenshots: steps
  };
  writeFileSync(resolve(outputDir, "browser-proof.json"), `${JSON.stringify(report, null, 2)}\n`);
  if (consoleErrors.length) throw new Error(`Browser console/page errors: ${consoleErrors.join(" | ")}`);
  if (narrowViewport.hasPageHorizontalOverflow) throw new Error("Narrow viewport has page-level horizontal overflow.");
  await context.close();
  console.log(JSON.stringify(report, null, 2));
} finally {
  if (browser) await browser.close().catch(() => {});
  if (server) await new Promise(resolveClose => server.close(resolveClose));
  delete process.env.HOWIE_DASHBOARD_WORKSPACE_PATH;
  rmSync(workspace, { recursive: true, force: true });
}
