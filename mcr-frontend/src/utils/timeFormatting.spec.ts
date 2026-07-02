import { describe, it, expect } from 'vitest';
import { formatDurationLabel, formatDurationMinutes } from './timeFormatting';

describe('formatDurationMinutes tests', () => {
  it('should handle undefined argument', () => {
    expect(formatDurationMinutes(undefined)).toBeDefined();
  });

  it('should only display minutes if <= 60min', () => {
    expect(formatDurationMinutes(45)).toBe('Moins de 45 min');
  });

  it('should format hours and minutes if > 60min & < 24h', () => {
    expect(formatDurationMinutes(120)).toBe('Moins de 2 h');
    expect(formatDurationMinutes(130)).toBe('Moins de 2 h 10 min');
  });

  it('should format hours only if >= 24h', () => {
    expect(formatDurationMinutes(1440)).toBe('Plus de 24 h');
    expect(formatDurationMinutes(1441)).toBe('Plus de 24 h');
  });
});

describe('formatDurationLabel tests', () => {
  it.each([
    [14400, '4 h'],
    [5400, '1 h 30 min'],
    [90, '1 min 30 s'],
    [172800, '2 j'],
    [90060, '1 j 1 h 1 min'],
    [45, '45 s'],
    [0, '0 s'],
  ])('formats %d seconds as "%s"', (seconds, expected) => {
    expect(formatDurationLabel(seconds)).toBe(expected);
  });
});
