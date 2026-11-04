import { defang, formatNumber, percent, shortId } from './format';

describe('format helpers', () => {
  it('defangs URLs so they cannot be clicked by accident', () => {
    expect(defang('http://evil.example.com/a')).toBe('hxxp://evil[.]example[.]com/a');
  });

  it('computes percentages safely, including an empty total', () => {
    expect(percent(1, 4)).toBe('25%');
    expect(percent(0, 0)).toBe('0%');
  });

  it('shortens ids and formats numbers', () => {
    expect(shortId('0123456789abcdef')).toBe('01234567');
    expect(formatNumber(3)).toBe('3');
    expect(formatNumber(3.14159)).toBe('3.14');
  });
});
