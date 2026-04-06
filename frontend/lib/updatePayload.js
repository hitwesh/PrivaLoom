const MAX_PARAMS = 5;
const SLICE_SIZE = 16;

function normalizeByte(byte) {
  return (byte - 127.5) / 127.5;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

async function fileToSlice(file, index) {
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);

  if (!bytes.length) {
    return [0.12, -0.07, 0.04, -0.03, 0.09, -0.06, 0.05, -0.02];
  }

  const slice = [];
  const sizeSignal = Math.log10(file.size + 1) / 10;

  for (let i = 0; i < SLICE_SIZE; i += 1) {
    const source = bytes[(i * 7 + index * 13) % bytes.length];
    const normalized = normalizeByte(source);
    const oscillation = Math.sin((i + 1) * 0.7 + index) * 0.04;
    const value = normalized * 0.45 + sizeSignal * 0.08 + oscillation;
    slice.push(Number(clamp(value, -0.95, 0.95).toFixed(6)));
  }

  return slice;
}

export async function buildUpdateWeightsFromFiles(fileEntries) {
  const selected = (fileEntries || []).slice(0, MAX_PARAMS);

  if (!selected.length) {
    return [[0.21, -0.13, 0.09, -0.06, 0.03, -0.01, 0.08, -0.04]];
  }

  const slices = [];
  for (let index = 0; index < selected.length; index += 1) {
    const entry = selected[index];
    const file = entry?.file || entry;
    if (!file) {
      continue;
    }

    // Deterministically derive numeric update slices from selected files.
    const slice = await fileToSlice(file, index);
    slices.push(slice);
  }

  return slices.length ? slices : [[0.17, -0.08, 0.11, -0.04, 0.06, -0.03, 0.05, -0.02]];
}
