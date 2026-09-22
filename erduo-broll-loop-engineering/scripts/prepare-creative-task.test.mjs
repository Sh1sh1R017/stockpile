import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { cp, mkdtemp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { prepareCreativeTask } from '../erduo-broll-loop-engineering/scripts/prepare-creative-task.mjs';

const cli = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../erduo-broll-loop-engineering/scripts/prepare-creative-task.mjs');
const SRT = `1\n00:00:00,000 --> 00:00:01,000\nOne.\n\n2\n00:00:01,000 --> 00:00:02,000\nTwo.\n\n3\n00:00:02,000 --> 00:00:03,000\nThree.\n`;

function plan(overrides = {}) {
  return {
    schemaVersion: 'lean-1',
    title: 'Three beats',
    inputs: { srt: 'input/original.srt', design: 'input/design.md' },
    profile: { width: 1920, height: 1080, fps: 24 },
    shots: [
      { id: 'S01', startMs: 0, endMs: 1000, cueIds: [1], intent: 'Open.', subject: 'One.', material: { route: 'native' }, composition: 'compositions/S01.html' },
      { id: 'S02', startMs: 1000, endMs: 2000, cueIds: [2], intent: 'Develop.', subject: 'Two.', material: { route: 'native' }, composition: 'compositions/S02.html' },
      { id: 'S03', startMs: 2000, endMs: 3000, cueIds: [3], intent: 'Land.', subject: 'Three.', material: { route: 'native' }, composition: 'compositions/S03.html' },
    ],
    ...overrides,
  };
}

async function fixture(value = plan()) {
  const parent = await mkdtemp(path.join(os.tmpdir(), 'creative-task-'));
  const project = path.join(parent, "project with space and 'quote");
  await mkdir(path.join(project, 'input'), { recursive: true });
  await mkdir(path.join(project, 'assets'));
  await mkdir(path.join(project, 'direction'));
  await writeFile(path.join(project, 'input', 'original.srt'), SRT);
  await writeFile(path.join(project, 'input', 'design.md'), '# Design\n');
  await writeFile(path.join(project, 'assets', 'index.md'), '# Sources\n');
  await writeFile(path.join(project, 'direction.md'), '# Shared direction\n');
  for (const shot of value.shots) await writeFile(path.join(project, 'direction', `${shot.id}.md`), `# ${shot.id}\n`);
  await writeFile(path.join(project, 'broll-plan.json'), JSON.stringify(value));
  return { parent, project };
}

async function renderFixture(project, { complete = false } = {}) {
  const root = path.join(project, 'lean-renders', 'draft');
  await mkdir(path.join(root, 'checks'), { recursive: true });
  await writeFile(path.join(root, 'preview.mp4'), 'preview');
  const rendered = complete ? ['S01', 'S02', 'S03'] : ['S01', 'S02'];
  for (const id of rendered) await writeFile(path.join(root, 'checks', `${id}.png`), id);
  await writeFile(path.join(root, 'index.json'), JSON.stringify({
    schemaVersion: 'lean-render-index-1',
    complete,
    shots: ['S01', 'S02', 'S03'].map((id) => rendered.includes(id)
      ? { id, status: 'ready', sheet: `lean-renders/draft/checks/${id}.png` }
      : { id, status: 'source-missing' }),
    preview: { output: 'lean-renders/draft/preview.mp4' },
  }));
}

function runCli(args) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [cli, ...args], { stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
    child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
    child.once('error', reject);
    child.once('close', (code) => resolve({ code, stdout, stderr }));
  });
}

test('prepares different minimal read sets for director, creator, and reviewer', async (t) => {
  const { parent, project } = await fixture();
  t.after(() => rm(parent, { recursive: true, force: true }));
  await renderFixture(project);

  const director = await prepareCreativeTask({ project, role: 'director' });
  const creator = await prepareCreativeTask({ project, role: 'creator', shots: 'S01,S02' });
  const reviewer = await prepareCreativeTask({ project, role: 'reviewer' });

  assert.deepEqual(creator.shots, ['S01', 'S02']);
  assert.deepEqual(reviewer.shots, ['S01', 'S02']);
  assert.ok(director.readFiles.some((file) => file.endsWith('creative-director.md')));
  assert.ok(creator.readFiles.some((file) => file.endsWith('assets/index.md')));
  assert.ok(creator.readFiles.some((file) => file.endsWith('direction/S03.md')), 'neighbor seam card is included');
  assert.ok(!reviewer.readFiles.some((file) => file.includes(`${path.sep}compositions${path.sep}`)));
  assert.ok(!reviewer.readFiles.some((file) => file.endsWith('index.json')), 'raw render cost metrics stay with Parent');
  assert.ok(reviewer.readFiles.some((file) => file.endsWith('preview.mp4')));
  assert.ok(reviewer.readFiles.some((file) => file.endsWith('S01.png')));
  assert.ok(!director.readFiles.some((file) => file.endsWith('broll-plan.json')));
});

test('review requires an explicit choice when draft and final both exist', async (t) => {
  const { parent, project } = await fixture();
  t.after(() => rm(parent, { recursive: true, force: true }));
  await renderFixture(project);
  const draft = path.join(project, 'lean-renders', 'draft');
  const final = path.join(project, 'lean-renders', 'final');
  await cp(draft, final, { recursive: true });
  const indexFile = path.join(final, 'index.json');
  await writeFile(indexFile, (await readFile(indexFile, 'utf8')).replaceAll('lean-renders/draft/', 'lean-renders/final/'));
  await assert.rejects(prepareCreativeTask({ project, role: 'reviewer' }), /use --quality/u);
  for (const quality of ['draft', 'final']) {
    const result = await prepareCreativeTask({ project, role: 'reviewer', quality });
    const previews = result.readFiles.filter((file) => file.endsWith('preview.mp4'));
    assert.deepEqual(previews, [path.join(project, 'lean-renders', quality, 'preview.mp4')]);
  }
});

test('fails directly when required handoff material is missing', async (t) => {
  const { parent, project } = await fixture();
  t.after(() => rm(parent, { recursive: true, force: true }));
  await rm(path.join(project, 'direction', 'S03.md'));
  await assert.rejects(
    prepareCreativeTask({ project, role: 'creator', shots: 'S01,S02' }),
    /S03 direction card is missing/u,
  );
  await assert.rejects(
    prepareCreativeTask({ project, role: 'reviewer' }),
    /render review is not ready/u,
  );
});

test('rejects non-contiguous shots and shared owned composition', async (t) => {
  const first = await fixture();
  t.after(() => rm(first.parent, { recursive: true, force: true }));
  await assert.rejects(
    prepareCreativeTask({ project: first.project, role: 'creator', shots: 'S01,S03' }),
    /one contiguous range/u,
  );

  const value = plan();
  value.shots[1].composition = value.shots[0].composition;
  const second = await fixture(value);
  t.after(() => rm(second.parent, { recursive: true, force: true }));
  await assert.rejects(
    prepareCreativeTask({ project: second.project, role: 'creator', shots: 'S01' }),
    /share composition/u,
  );
});

test('CLI returns concise JSON and writes only one Markdown handoff with shell-safe absolute commands', async (t) => {
  const { parent, project } = await fixture();
  t.after(() => rm(parent, { recursive: true, force: true }));
  const result = await runCli(['--project', project, '--role', 'creator', '--shots', 'S02']);
  assert.equal(result.code, 0, result.stderr);
  const output = JSON.parse(result.stdout);
  assert.equal(output.role, 'creator');
  assert.deepEqual(output.shots, ['S02']);
  assert.equal(output.note, 'Handoff prepared; host context is not sandboxed.');

  const body = await readFile(output.taskFile, 'utf8');
  assert.ok(body.includes(`'${process.execPath.replaceAll("'", "'\\''")}'`));
  assert.ok(body.includes(`'${project.replaceAll("'", "'\\''")}'`));
  assert.ok(body.includes("--shots 'S02'"));
  assert.deepEqual(await readdir(path.dirname(output.taskFile)), ['TASK.md']);
  assert.ok(output.taskFile.endsWith(path.join('creative-tasks', 'creator-S02', 'TASK.md')));
});
