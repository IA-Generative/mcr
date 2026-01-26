import { describe, it, expect } from 'vitest';
import { formatDurationMinutes } from './timeFormatting';

describe('formatDurationMinutes tests', () => {
  it('should handle undefined argument', () => {
    expect(formatDurationMinutes(undefined)).toBeDefined();
  });

  it('should only display minutes if <= 60min', () => {
    expect(formatDurationMinutes(45)).toBe('Moins de 45min');
  });

  it('should format hours and minutes if > 60min & < 24h', () => {
    expect(formatDurationMinutes(120)).toBe('Moins de 2h');
    expect(formatDurationMinutes(130)).toBe('Moins de 2h 10min');
  });

  it('should format hours only if >= 24h', () => {
    expect(formatDurationMinutes(1440)).toBe('Plus de 24h');
    expect(formatDurationMinutes(1441)).toBe('Plus de 24h');
  });
});
