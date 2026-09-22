import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { runLeanRender } from '../erduo-broll-loop-engineering/scripts/lean-render.mjs';

const HYPERFRAMES = '/mock/pinned/hyperframes';

async function makeProject(t) {
  const project = await mkdtemp(path.join(os.tmpdir(), 'lean-render-test-'));
  t.after(() => rm(project, { recursive: true, force: true }));
  await Promise.all([
    mkdir(path.join(project, 'input'), { recursive: true }),
    mkdir(path.join(project, 'compositions'), { recursive: true }),
    mkdir(path.join(project, 'assets'), { recursive: true }),
  ]);
  await Promise.all([
    writeFile(path.join(project, 'input', 'original.srt'), [
      '1', '00:00:00,000 --> 00:00:01,000', 'First', '',
      '2', '00:00:01,000 --> 00:00:02,000', 'Second', '',
    ].join('\n')),
    writeFile(path.join(project, 'input', 'design.md'), '# Clean editorial motion\n'),
    writeFile(path.join(project, 'assets', 'shared.css'), ':root { --accent: #ff7a00; }\n'),
    writeFile(path.join(project, 'compositions', 'S01.html'), composition('S01')),
    writeFile(path.join(project, 'compositions', 'S02.html'), composition('S02')),
    writeFile(path.join(project, 'broll-plan.json'), `${JSON.stringify({
      schemaVersion: 'lean-1',
      title: 'Lean sample',
      inputs: { srt: 'input/original.srt', design: 'input/design.md' },
      profile: { width: 1920, height: 1080, fps: 30 },
      shots: [
        {
          id: 'S01', startMs: 0, endMs: 1000, cueIds: [1], intent: 'Open', subject: 'one',
          material: { route: 'native' }, composition: 'compositions/S01.html',
        },
        {
          id: 'S02', startMs: 1000, endMs: 2000, cueIds: [2], intent: 'Resolve', subject: 'two',
          material: { route: 'native' }, composition: 'compositions/S02.html',
        },
      ],
    }, null, 2)}\n`),
  ]);
  return project;
}

function composition(id, { width = 1920, height = 1080, durationMs = 1000 } = {}) {
  return `<!doctype html><html data-composition-id="${id}" data-composition-width="${width}" data-composition-height="${height}" data-composition-duration="${durationMs / 1000}"><head><link rel="stylesheet" href="../assets/shared.css"></head><body>${id}</body></html>\n`;
}

function mockRunner({ failDecode = false, failDecodeGeneration = null } = {}) {
  const calls = [];
  let generation = 0;
  const runner = async ({ executable, args, cwd }) => {
    calls.push({ executable, args: [...args], cwd });
    if (executable === HYPERFRAMES && args[0] === '--version') {
      return { code: 0, stdout: '0.7.104\n', stderr: '' };
    }
    if (executable === HYPERFRAMES && args[0] === 'render') {
      generation += 1;
      const output = args[args.indexOf('--output') + 1];
      const fps = Number(args[args.indexOf('--fps') + 1]);
      const project = args[1];
      const compositionFile = args[args.indexOf('--composition') + 1];
      const source = await readFile(path.join(project, compositionFile), 'utf8');
      const sourceWidth = Number(/data-composition-width="([0-9]+)"/u.exec(source)?.[1] ?? 1920);
      const sourceHeight = Number(/data-composition-height="([0-9]+)"/u.exec(source)?.[1] ?? 1080);
      const sourceDurationMs = Number(/data-composition-duration="([0-9.]+)"/u.exec(source)?.[1] ?? 1) * 1_000;
      const resolution = args.includes('--resolution') ? args[args.indexOf('--resolution') + 1] : null;
      const size = resolution === 'landscape' ? [1920, 1080] : resolution === 'landscape-4k' ? [3840, 2160] : [sourceWidth, sourceHeight];
      const frames = Math.ceil(sourceDurationMs / 1_000 * fps - 1e-9);
      await writeFile(output, JSON.stringify(video({
        width: size[0], height: size[1], fps, durationMs: frames / fps * 1_000, frames, generation,
      })));
      return { code: 0, stdout: '', stderr: '' };
    }
    if (executable === 'ffprobe') {
      const media = JSON.parse(await readFile(args.at(-1), 'utf8'));
      return {
        code: 0,
        stdout: JSON.stringify({
          streams: [{
            codec_type: 'video', codec_name: 'h264', width: media.width, height: media.height,
            avg_frame_rate: `${media.fps}/1`, nb_read_frames: String(media.frames), start_time: '0',
          }],
          format: { format_name: 'mov,mp4', duration: String(media.durationMs / 1000), start_time: '0' },
        }),
        stderr: '',
      };
    }
    if (executable === 'ffmpeg' && args.includes('null')) {
      const decoded = JSON.parse(await readFile(args[args.indexOf('-i') + 1], 'utf8'));
      return failDecode || decoded.generation === failDecodeGeneration
        ? { code: 1, stdout: '', stderr: 'mock decode failure' }
        : { code: 0, stdout: '', stderr: '' };
    }
    if (executable === 'ffmpeg' && args.includes('concat')) {
      const concatFile = args[args.indexOf('-i') + 1];
      const entries = (await readFile(concatFile, 'utf8')).trim().split('\n').filter(Boolean);
      const contents = [];
      for (const entry of entries) {
        const locator = entry.slice("file '".length, -1).replaceAll("'\\''", "'");
        contents.push(JSON.parse(await readFile(locator, 'utf8')));
      }
      const first = contents[0];
      const frames = contents.reduce((sum, item) => sum + item.frames, 0);
      const durationMs = frames / first.fps * 1_000;
      await writeFile(args.at(-1), JSON.stringify(video({
        width: first.width, height: first.height, fps: first.fps, durationMs, frames,
        generation: contents.map(({ generation: value }) => value),
      })));
      return { code: 0, stdout: '', stderr: '' };
    }
    if (executable === 'ffmpeg' && args.includes('-frames:v')) {
      await writeFile(args.at(-1), Buffer.from('89504e470d0a1a0a', 'hex'));
      return { code: 0, stdout: '', stderr: '' };
    }
    if (executable === 'ffmpeg' && args.includes('-vf')) {
      const input = JSON.parse(await readFile(args[args.indexOf('-i') + 1], 'utf8'));
      const filter = args[args.indexOf('-vf') + 1];
      const scale = /(?:^|,)scale=(\d+):(\d+)(?:,|$)/u.exec(filter);
      const trim = /(?:^|,)trim=end_frame=(\d+)(?:,|$)/u.exec(filter);
      const frames = trim ? Number(trim[1]) : input.frames;
      await writeFile(args.at(-1), JSON.stringify(video({
        ...input,
        width: scale ? Number(scale[1]) : input.width,
        height: scale ? Number(scale[2]) : input.height,
        frames,
        durationMs: frames / input.fps * 1_000,
      })));
      return { code: 0, stdout: '', stderr: '' };
    }
    throw new Error(`unexpected mock command: ${executable} ${args.join(' ')}`);
  };
  return { calls, runner };
}

function video({ width, height, fps, durationMs, frames = Math.round(durationMs / 1000 * fps), generation }) {
  return { width, height, fps, durationMs, frames, generation };
}

function renderCalls(calls) {
  return calls.filter(({ executable, args }) => executable === HYPERFRAMES && args[0] === 'render');
}

function srtTimestamp(milliseconds) {
  const hours = Math.floor(milliseconds / 3_600_000);
  const minutes = Math.floor(milliseconds % 3_600_000 / 60_000);
  const seconds = Math.floor(milliseconds % 60_000 / 1_000);
  const ms = milliseconds % 1_000;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}

async function makeFractionalProject(t) {
  const project = await makeProject(t);
  const shots = [];
  const srt = [];
  for (let index = 0; index < 20; index += 1) {
    const id = `S${String(index + 1).padStart(2, '0')}`;
    const startMs = index * 101;
    const endMs = (index + 1) * 101;
    srt.push(String(index + 1), `${srtTimestamp(startMs)} --> ${srtTimestamp(endMs)}`, `Cue ${index + 1}`, '');
    shots.push({
      id, startMs, endMs, cueIds: [index + 1], intent: `Beat ${index + 1}`, subject: `Subject ${index + 1}`,
      material: { route: 'native' }, composition: `compositions/${id}.html`,
    });
    await writeFile(path.join(project, 'compositions', `${id}.html`), composition(id, { durationMs: 101 }));
  }
  await Promise.all([
    writeFile(path.join(project, 'input', 'original.srt'), srt.join('\n')),
    writeFile(path.join(project, 'broll-plan.json'), `${JSON.stringify({
      schemaVersion: 'lean-1', title: 'Fractional boundaries',
      inputs: { srt: 'input/original.srt', design: 'input/design.md' },
      profile: { width: 1920, height: 1080, fps: 30 }, shots,
    }, null, 2)}\n`),
  ]);
  return project;
}

test('an unchanged repeat reuses rendered media, sheets, preview, and prior decode', async (t) => {
  const project = await makeProject(t);
  const mock = mockRunner();
  const first = await runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner });
  assert.deepEqual(first.metrics, {
    requested: 2, rendered: 2, reused: 0, sheetsGenerated: 2,
    previewGenerated: 1, previewReused: 0, elapsedMs: first.metrics.elapsedMs,
  });
  const callsBefore = mock.calls.length;
  const second = await runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner });
  const repeatCalls = mock.calls.slice(callsBefore);
  assert.equal(second.metrics.rendered, 0);
  assert.equal(second.metrics.reused, 2);
  assert.equal(second.metrics.previewReused, 1);
  assert.equal(renderCalls(repeatCalls).length, 0);
  assert.equal(repeatCalls.filter(({ executable }) => executable === 'ffprobe' || executable === 'ffmpeg').length, 0);
});

test('editing S02 rerenders only S02 and regenerates its sheet', async (t) => {
  const project = await makeProject(t);
  const mock = mockRunner();
  await runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner });
  await writeFile(path.join(project, 'compositions', 'S02.html'), `${composition('S02')}<!-- changed -->\n`);
  const callsBefore = mock.calls.length;
  const result = await runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner });
  const rendered = renderCalls(mock.calls.slice(callsBefore));
  assert.equal(result.metrics.rendered, 1);
  assert.equal(result.metrics.reused, 1);
  assert.deepEqual(rendered.map(({ args }) => args[args.indexOf('--composition') + 1]), ['compositions/S02.html']);
  assert.equal(result.metrics.sheetsGenerated, 1);
});

test('changing a shared asset conservatively invalidates every dependent shot', async (t) => {
  const project = await makeProject(t);
  const mock = mockRunner();
  await runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner });
  await writeFile(path.join(project, 'assets', 'shared.css'), ':root { --accent: #16c79a; }\n');
  const callsBefore = mock.calls.length;
  const result = await runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner });
  assert.equal(result.metrics.rendered, 2);
  assert.equal(renderCalls(mock.calls.slice(callsBefore)).length, 2);
});

test('a harmless viewing note does not invalidate visual dependencies', async (t) => {
  const project = await makeProject(t);
  const mock = mockRunner();
  await runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner });
  await writeFile(path.join(project, 'viewing.md'), '# Human review notes\nLooks good.\n');
  const callsBefore = mock.calls.length;
  const result = await runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner });
  assert.equal(result.metrics.rendered, 0);
  assert.equal(result.metrics.reused, 2);
  assert.equal(renderCalls(mock.calls.slice(callsBefore)).length, 0);
});

test('a shot revision changes preview identity and replaces the stale preview', async (t) => {
  const project = await makeProject(t);
  const mock = mockRunner();
  await runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner });
  const cacheFile = path.join(project, 'lean-renders', 'draft', '.cache.json');
  const oldCache = JSON.parse(await readFile(cacheFile, 'utf8'));
  const oldPreview = await readFile(path.join(project, oldCache.preview.output), 'utf8');
  await writeFile(path.join(project, 'compositions', 'S02.html'), `${composition('S02')}<!-- revision two -->\n`);
  const result = await runLeanRender({ project, quality: 'draft', shots: ['S02'], hyperframes: HYPERFRAMES, runner: mock.runner });
  const newCache = JSON.parse(await readFile(cacheFile, 'utf8'));
  const newPreview = await readFile(path.join(project, newCache.preview.output), 'utf8');
  assert.equal(result.metrics.previewGenerated, 1);
  assert.notEqual(newCache.preview.identity, oldCache.preview.identity);
  assert.notEqual(newPreview, oldPreview);
  assert.deepEqual(newCache.preview.shotIds, ['S01', 'S02']);
});

test('draft and final use separate trees and truthful profiles', async (t) => {
  const project = await makeProject(t);
  const mock = mockRunner();
  const draft = await runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner });
  const final = await runLeanRender({ project, quality: 'final', hyperframes: HYPERFRAMES, runner: mock.runner });
  assert.notEqual(draft.outputRoot, final.outputRoot);
  const draftIndex = JSON.parse(await readFile(draft.index, 'utf8'));
  const finalIndex = JSON.parse(await readFile(final.index, 'utf8'));
  assert.deepEqual(draftIndex.profile, { width: 960, height: 540, fps: 15 });
  assert.equal(draftIndex.deliveryStatus, 'draft-preview');
  assert.deepEqual(finalIndex.profile, { width: 1920, height: 1080, fps: 30 });
  assert.equal(finalIndex.deliveryStatus, 'final-render');
  const qualities = renderCalls(mock.calls).map(({ args }) => args[args.indexOf('--quality') + 1]);
  assert.deepEqual(qualities, ['draft', 'draft', 'high', 'high']);
});

test('a requested early shot can produce an explicitly partial preview before later source exists', async (t) => {
  const project = await makeProject(t);
  await rm(path.join(project, 'compositions', 'S02.html'));
  const mock = mockRunner();
  const result = await runLeanRender({
    project, quality: 'final', shots: ['S01'], hyperframes: HYPERFRAMES, runner: mock.runner,
  });
  const index = JSON.parse(await readFile(result.index, 'utf8'));
  assert.equal(result.complete, false);
  assert.equal(result.status, 'partial-preview');
  assert.equal(index.complete, false);
  assert.equal(index.deliveryStatus, 'partial-preview');
  assert.equal(index.shots[1].status, 'source-missing');
  assert.deepEqual(index.preview.shotIds, ['S01']);
});

test('a later shot failure persists earlier completed work for the next run', async (t) => {
  const project = await makeProject(t);
  const mock = mockRunner({ failDecodeGeneration: 2 });
  await assert.rejects(
    runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner }),
    /mock decode failure/u,
  );
  const cache = JSON.parse(await readFile(path.join(project, 'lean-renders', 'draft', '.cache.json'), 'utf8'));
  assert.ok(cache.shots.S01);
  assert.equal(cache.shots.S02, undefined);
  const callsBefore = mock.calls.length;
  const result = await runLeanRender({ project, quality: 'draft', hyperframes: HYPERFRAMES, runner: mock.runner });
  assert.equal(result.metrics.reused, 1);
  assert.equal(result.metrics.rendered, 1);
  assert.deepEqual(renderCalls(mock.calls.slice(callsBefore)).map(({ args }) => args[args.indexOf('--composition') + 1]), ['compositions/S02.html']);
});

test('twenty non-integral shot durations close on one global frame boundary without cumulative drift', async (t) => {
  const project = await makeFractionalProject(t);
  const mock = mockRunner();
  const result = await runLeanRender({ project, quality: 'final', hyperframes: HYPERFRAMES, runner: mock.runner });
  const cache = JSON.parse(await readFile(path.join(project, 'lean-renders', 'final', '.cache.json'), 'utf8'));
  const records = Object.values(cache.shots);
  assert.equal(records.length, 20);
  for (let index = 1; index < records.length; index += 1) {
    assert.equal(records[index].startFrame, records[index - 1].endFrame);
  }
  assert.equal(records.reduce((sum, record) => sum + record.frameCount, 0), 61);
  assert.equal(cache.preview.facts.frameCount, 61);
  assert.ok(Math.abs(cache.preview.facts.durationMs - 61 / 30 * 1_000) <= 1);
  const index = JSON.parse(await readFile(result.index, 'utf8'));
  assert.equal(index.shots.at(-1).endMs, 2020, 'authoritative millisecond plan remains unchanged');
});

test('an unmapped final profile fails if the composition raster does not exactly match', async (t) => {
  const project = await makeProject(t);
  const planFile = path.join(project, 'broll-plan.json');
  const plan = JSON.parse(await readFile(planFile, 'utf8'));
  plan.profile = { width: 1280, height: 720, fps: 30 };
  await writeFile(planFile, `${JSON.stringify(plan, null, 2)}\n`);
  const mock = mockRunner();
  await assert.rejects(
    runLeanRender({ project, quality: 'final', shots: ['S01'], hyperframes: HYPERFRAMES, runner: mock.runner }),
    /final raster 1920x1080 differs from 1280x720/u,
  );
  await assert.rejects(readFile(path.join(project, 'lean-renders', 'final', 'shots', 'S01.mp4')));
});

test('decode failure leaves no successful cache, index, or shot output', async (t) => {
  const project = await makeProject(t);
  const mock = mockRunner({ failDecode: true });
  await assert.rejects(
    runLeanRender({ project, quality: 'draft', shots: ['S01'], hyperframes: HYPERFRAMES, runner: mock.runner }),
    /mock decode failure/u,
  );
  await assert.rejects(readFile(path.join(project, 'lean-renders', 'draft', '.cache.json')));
  await assert.rejects(readFile(path.join(project, 'lean-renders', 'draft', 'index.json')));
  await assert.rejects(readFile(path.join(project, 'lean-renders', 'draft', 'shots', 'S01.mp4')));
});
