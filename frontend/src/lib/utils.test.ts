import { describe, expect, it } from 'vitest';

import { cn, formatBytes, formatEta, formatSpeed } from './utils';

describe('formatBytes', () => {
  it('formats zero and negative values as 0 B', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(-5)).toBe('0 B');
  });

  it('formats bytes without a decimal', () => {
    expect(formatBytes(512)).toBe('512 B');
  });

  it('formats kilobytes/megabytes/gigabytes with one decimal', () => {
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(5 * 1024 ** 3)).toBe('5.0 GB');
  });
});

describe('formatSpeed', () => {
  it('appends /s to a byte count', () => {
    expect(formatSpeed(1024)).toBe('1.0 KB/s');
  });
});

describe('formatEta', () => {
  it('returns a dash for missing or invalid values', () => {
    expect(formatEta(null)).toBe('-');
    expect(formatEta(undefined)).toBe('-');
    expect(formatEta(-1)).toBe('-');
    expect(formatEta(Number.POSITIVE_INFINITY)).toBe('-');
  });

  it('formats sub-minute durations as seconds', () => {
    expect(formatEta(0)).toBe('0s');
    expect(formatEta(45)).toBe('45s');
  });

  it('formats minute-scale durations', () => {
    expect(formatEta(125)).toBe('2m 5s');
  });

  it('formats hour- and day-scale durations', () => {
    expect(formatEta(3 * 3600 + 90)).toBe('3h 1m');
    expect(formatEta(2 * 86400 + 3600)).toBe('2d 1h');
  });
});

describe('cn', () => {
  it('merges class names and resolves Tailwind conflicts', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4');
    expect(cn('text-sm', undefined, false, 'font-bold')).toBe('text-sm font-bold');
  });
});
