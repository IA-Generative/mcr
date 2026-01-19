import { describe, it, expect } from 'vitest';
import { formatDurationMinutes } from './timeFormatting';

describe('formatDurationMinutes tests', () => {
  it('should handle undefined argument', () => {
    expect(formatDurationMinutes(undefined)).toBeDefined();
  });

  it('should not diplay minutes if <= 60min', () => {
    expect(formatDurationMinutes(45)).toBe("Moins d'une heure");
  });

  it('should format hours and minutes if > 60min & < 24h', () => {
    expect(formatDurationMinutes(120)).toBe('2h00');
    expect(formatDurationMinutes(130)).toBe('2h10');
  });

  it('should format hours only if >= 24h', () => {
    expect(formatDurationMinutes(1440)).toBe('24 heures');
    expect(formatDurationMinutes(1441)).toBe('24 heures');
  });
});
