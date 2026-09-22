import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { loadLeanPlan } from '../erduo-broll-loop-engineering/scripts/lean-plan.mjs';

const SRT = `1\n00:00:00,000 --> 00:00:00,401\nOpening.\n\n2\n00:00:00,700 --> 00:00:01,001\nResolve.\n`;
const leanPlanCli = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../erduo-broll-loop-engineering/scripts/lean-plan.mjs');

function plan(overrides = {}) {
  return {
    schemaVersion: 'lean-1',
    title: 'Fractional closure',
    inputs: { srt: 'input/original.srt', design: 'input/design.md' },
    profile: { width: 1920, height: 1080, fps: 24 },
    shots: [
      { id: 'S01', startMs: 0, endMs: 700, cueIds: [1], intent: 'Set the question.', subject: 'A visible question.', material: { route: 'native' }, composition: 'compositions/S01.html' },
      { id: 'S02', startMs: 700, endMs: 1001, cueIds: [2], intent: 'Resolve it.', subject: 'A visible resolution.', material: { route: 'generate' }, composition: 'compositions/S02.html' },
    ],
    ...overrides,
  };
}

async function fixture(value = plan(), srt = SRT) {
  const project = await mkdtemp(path.join(os.tmpdir(), 'lean-plan-'));
  await mkdir(path.join(project, 'input'));
  await writeFile(path.join(project, 'input', 'original.srt'), srt);
  await writeFile(path.join(project, 'input', 'design.md'), '# design\n');
  await writeFile(path.join(project, 'broll-plan.json'), JSON.stringify(value));
  return project;
}

async function rejects(value, expression, srt = SRT) {
  const project = await fixture(value, srt);
  try {
    await assert.rejects(loadLeanPlan(project), expression);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
}

function runCli(project) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [leanPlanCli, '--project', project], { stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
    child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
    child.once('error', reject);
    child.once('close', (code) => resolve({ code, stdout, stderr }));
  });
}

test('accepts a two-shot plan and preserves a fractional-frame SRT ending', async () => {
  const project = await fixture();
  try {
    const loaded = await loadLeanPlan(project);
    assert.equal(loaded.plan.shots.length, 2);
    assert.equal(loaded.cues.at(-1).endMs, 1001);
    assert.equal(loaded.plan.shots.at(-1).endMs, 1001);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
});

test('CLI validates the documented command and prints one concise line', async () => {
  const project = await fixture();
  try {
    const result = await runCli(project);
    assert.equal(result.code, 0, result.stderr);
    assert.match(result.stdout, /^Lean plan valid: Fractional closure — 2 shots, 2 cues, 1001ms\n$/u);
    assert.equal(result.stderr, '');
  } finally {
    await rm(project, { recursive: true, force: true });
  }
});

test('rejects a gap in the authoritative timeline', async () => {
  const value = plan();
  value.shots[1].startMs = 701;
  await rejects(value, /gap or overlap/u);
});

test('rejects a timeline that does not close at the final SRT time', async () => {
  const value = plan();
  value.shots[1].endMs = 1000;
  await rejects(value, /final SRT cue end/u);
});

test('rejects malformed original SRT timing', async () => {
  await rejects(plan(), /invalid timing/u, '1\n00:00:00,000 --> 00:00:bad\nBroken.\n');
});

test('rejects an SRT cue that no shot claims', async () => {
  const value = plan();
  value.shots[1].cueIds = [];
  await rejects(value, /must include overlapping SRT cue 2/u);
});

test('rejects a cue assigned outside its shot', async () => {
  const value = plan();
  value.shots[0].cueIds = [2];
  await rejects(value, /does not overlap/u);
});

test('rejects duplicate shot ids', async () => {
  const value = plan();
  value.shots[1].id = 'S01';
  await rejects(value, /duplicates/u);
});

test('rejects a shot id that cannot safely name render files', async () => {
  const value = plan();
  value.shots[0].id = 'S 01';
  await rejects(value, /ASCII filename-safe/u);
});

test('rejects an odd h264 output dimension', async () => {
  const value = plan({ profile: { width: 1921, height: 1080, fps: 24 } });
  await rejects(value, /must be even/u);
});

test('requires input shots to already be chronological', async () => {
  const value = plan();
  value.shots.reverse();
  await rejects(value, /coverage must start at 0/u);
});

test('requires each shot to claim every SRT cue it overlaps', async () => {
  const srt = `1\n00:00:00,000 --> 00:00:00,800\nSpans the cut.\n`;
  const value = plan({
    shots: [
      { id: 'S01', startMs: 0, endMs: 400, cueIds: [1], intent: 'Begin.', subject: 'Beginning.', material: { route: 'native' }, composition: 'compositions/S01.html' },
      { id: 'S02', startMs: 400, endMs: 800, cueIds: [], intent: 'Finish.', subject: 'Finish.', material: { route: 'native' }, composition: 'compositions/S02.html' },
    ],
  });
  await rejects(value, /must include overlapping SRT cue 1/u, srt);
});

test('rejects missing original input', async () => {
  const value = plan({ inputs: { srt: 'input/missing.srt', design: 'input/design.md' } });
  await rejects(value, /inputs\.srt is missing/u);
});
