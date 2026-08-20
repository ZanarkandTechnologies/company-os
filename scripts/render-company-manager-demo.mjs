#!/usr/bin/env node
/**
 * Local, dependency-free technical-demo renderer.
 *
 * Remotion is intentionally not added to this small proof checkout.  This
 * adapter turns verified browser captures plus a local macOS system voice into
 * a deterministic MP4 without network access, uploads, or provider spend.
 */
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const ticketId = "TASK-0002";
const runDir = resolve(root, "tickets/TASK-0002/artifacts/demo/2026-08-10-dependency-proof");
const browserDir = resolve(root, "tickets/TASK-0002/artifacts/browser");
const names = ["01-empty-plan", "02-dependencies-blocked", "03-telegram-preview", "04-timeline-after-reply", "05-dependencies-unblocked", "06-table-readiness", "07-narrow-table"];
const images = names.map(name => resolve(browserDir, `${name}.png`));
const durations = [10, 11, 10, 11, 11, 12, 11];
const narrationScript = resolve(runDir, "narration-script.txt");
const narration = resolve(runDir, "narration.aiff");
const output = resolve(runDir, "final.mp4");
const framesDir = resolve(runDir, "frames");
const frameSeconds = [12, 38, 60, 70];

for (const path of [...images, narrationScript]) {
  if (!existsSync(path)) throw new Error(`Missing verified demo input: ${path}`);
}

function execute(command, args) {
  execFileSync(command, args, { stdio: "inherit" });
}

execute("/usr/bin/say", ["-v", "Samantha", "-r", "175", "-o", narration, "-f", narrationScript]);

const inputArgs = images.flatMap((path, index) => ["-loop", "1", "-framerate", "30", "-t", String(durations[index]), "-i", path]);
// H.264/yuv420p requires even dimensions; the tallest source capture is 1543px.
const canvas = { width: 1440, height: 1542 };
const normalizedInputs = images.map((_, index) => (
  `[${index}:v]scale=${canvas.width}:${canvas.height}:force_original_aspect_ratio=decrease,` +
  `pad=${canvas.width}:${canvas.height}:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1[v${index}]`
)).join(";");
const filterInputs = images.map((_, index) => `[v${index}]`).join("");
const filter = `${normalizedInputs};${filterInputs}concat=n=${images.length}:v=1:a=0,format=yuv420p[v]`;
execute("/opt/homebrew/bin/ffmpeg", [
  "-y", ...inputArgs, "-i", narration,
  "-filter_complex", filter,
  "-map", "[v]", "-map", `${images.length}:a:0`,
  "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
  "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", output
]);

mkdirSync(framesDir, { recursive: true });
for (const second of frameSeconds) {
  execute("/opt/homebrew/bin/ffmpeg", [
    "-y", "-ss", String(second), "-i", output, "-frames:v", "1", "-update", "1",
    resolve(framesDir, `frame-${second}s.png`)
  ]);
}
execute("/opt/homebrew/bin/ffmpeg", ["-v", "error", "-i", output, "-map", "0:a", "-f", "null", "-"]);

const mediaProbe = JSON.parse(execFileSync("/opt/homebrew/bin/ffprobe", [
  "-v", "error", "-count_frames", "-show_entries",
  "stream=index,codec_type,codec_name,width,height,channels,avg_frame_rate,nb_read_frames,duration:format=duration,size,bit_rate",
  "-of", "json", output
], { encoding: "utf8" }));
writeFileSync(resolve(runDir, "media-probe.json"), `${JSON.stringify(mediaProbe, null, 2)}\n`);

writeFileSync(resolve(runDir, "render-receipt.json"), `${JSON.stringify({
  ticket_id: ticketId,
  renderer: "local_ffmpeg_fallback",
  reason: "Remotion is unavailable in this checkout; no dependency or external render route was added.",
  visual_inputs: images.map(path => path.slice(root.length + 1)),
  narration_input: narrationScript.slice(root.length + 1),
  narration_output: narration.slice(root.length + 1),
  output: output.slice(root.length + 1),
  canvas,
  representative_frames: frameSeconds.map(second => resolve(framesDir, `frame-${second}s.png`).slice(root.length + 1)),
  voice: "macOS Samantha system voice",
  network_or_provider_use: false
}, null, 2)}\n`);

console.log(output);
