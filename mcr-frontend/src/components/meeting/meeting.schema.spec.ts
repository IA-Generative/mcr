import { describe, expect, test } from 'vitest';
import { comuPrivateUrlValidator, visioUrlValidator } from './meeting.schema';

type TestCase = {
  name: string;
  url: string;
  shouldMatch: boolean;
};

vi.mock('@/composables/use-feature-flag', () => {
  const mockedUseFeatureFlag = () => {
    return true;
  };

  return {
    useFeatureFlag: mockedUseFeatureFlag,
  };
});

const comuTestCases: TestCase[] = [
  // ✅ Valid
  {
    name: 'Valid URL (gouv) with secret and meeting ID',
    url: 'https://webconf.comu.gouv.fr/meeting/123456?secret=ABCdefGHIjkl_mnoPQRstu',
    shouldMatch: true,
  },
  {
    name: 'Valid URL (minint) with language code',
    url: 'https://webconf.comu.minint.fr/en-US/meeting/987654?secret=abcDEFghiJKL_mnoPQRstu',
    shouldMatch: true,
  },
  {
    name: 'Valid URL (interieur.rie.gouv) with language code',
    url: 'https://webconf.comu.interieur.rie.gouv.fr/fr-FR/meeting/111222?secret=1234567890abcdefABCDEF',
    shouldMatch: true,
  },
  {
    name: 'Valid URL with long meeting ID',
    url: 'https://webconf.comu.gouv.fr/pt-BR/meeting/9876543210?secret=A1b2C3d4E5F6g7H8I9J0kl',
    shouldMatch: true,
  },

  // ❌ Invalid
  {
    name: 'Invalid domain',
    url: 'https://webconf.comu.unknown.fr/meeting/123?secret=ABCdefGHIjkl_mnoPQRstu',
    shouldMatch: false,
  },
  {
    name: 'Missing webconf. subdomain',
    url: 'https://comu.gouv.fr/meeting/123?secret=ABCdefGHIjkl_mnoPQRstu',
    shouldMatch: false,
  },
  {
    name: 'Secret too short',
    url: 'https://webconf.comu.gouv.fr/meeting/123?secret=shortSecret',
    shouldMatch: false,
  },
  {
    name: 'Secret with invalid characters',
    url: 'https://webconf.comu.gouv.fr/meeting/123?secret=invalid!char$cter',
    shouldMatch: false,
  },
  {
    name: 'Non-numeric meeting ID',
    url: 'https://webconf.comu.gouv.fr/meeting/abc?secret=ABCdefGHIjkl_mnoPQRstu',
    shouldMatch: false,
  },
  {
    name: 'Missing meeting ID',
    url: 'https://webconf.comu.gouv.fr/meeting/?secret=ABCdefGHIjkl_mnoPQRstu',
    shouldMatch: false,
  },
  {
    name: 'Missing secret',
    url: 'https://webconf.comu.gouv.fr/meeting/123',
    shouldMatch: false,
  },
  {
    name: 'Secret too long',
    url: 'https://webconf.comu.gouv.fr/en-US/meeting/123456?secret=tooLongSecret_ABCDEFGHIJKL',
    shouldMatch: false,
  },
  {
    name: 'Invalid language code (missing region)',
    url: 'https://webconf.comu.gouv.fr/en/meeting/123456?secret=ABCdefGHIjkl_mnoPQRstu',
    shouldMatch: false,
  },
  {
    name: 'HTTP instead of HTTPS',
    url: 'http://webconf.comu.gouv.fr/en-US/meeting/123456?secret=ABCdefGHIjkl_mnoPQRstu',
    shouldMatch: false,
  },
  {
    name: 'Trailing slash after meeting ID',
    url: 'https://webconf.comu.gouv.fr/en-US/meeting/123456/?secret=ABCdefGHIjkl_mnoPQRstu',
    shouldMatch: false,
  },
  {
    name: 'Extra query params',
    url: 'https://webconf.comu.gouv.fr/meeting/123456?secret=ABCdefGHIjkl_mnoPQRstu&token=abc',
    shouldMatch: false,
  },
];

const visioTestCases: TestCase[] = [
  {
    name: 'Valid URL',
    url: 'https://visio.numerique.gouv.fr/aaa-bbbb-ccc',
    shouldMatch: true,
  },
  {
    name: 'Wrong domain',
    url: 'https://visio.numerique.gouv.eu/aaa-bbbb-ccc',
    shouldMatch: false,
  },
  {
    name: 'HTTP instead of HTTPS',
    url: 'http://visio.numerique.gouv.fr/aaa-bbbb-ccc',
    shouldMatch: false,
  },
  {
    name: 'Missing slug',
    url: 'https://visio.numerique.gouv.fr/',
    shouldMatch: false,
  },
  {
    name: 'Uppercase letters in slug',
    url: 'https://visio.numerique.gouv.fr/Aaa-bBbb-ccC',
    shouldMatch: false,
  },
  {
    name: 'Numbers in slug',
    url: 'https://visio.numerique.gouv.fr/rh1-bbbb-ccc',
    shouldMatch: false,
  },
  {
    name: 'Trailing slash',
    url: 'https://visio.numerique.gouv.fr/aaa-bbbb-ccc/',
    shouldMatch: false,
  },
  {
    name: 'Wrong group lengths',
    url: 'https://visio.numerique.gouv.fr/abcd-efgh-ijkl',
    shouldMatch: false,
  },
  {
    name: 'Missing group',
    url: 'https://visio.numerique.gouv.fr/aaa-bbbb',
    shouldMatch: false,
  },
];

describe('comuUrlRegex match tests', () => {
  test.each(comuTestCases)('$name', ({ url, shouldMatch }) => {
    expect(comuPrivateUrlValidator.test(url)).toBe(shouldMatch);
  });
});

describe('visioUrlRegex match tests', () => {
  test.each(visioTestCases)('$name', ({ url, shouldMatch }) => {
    expect(visioUrlValidator.test(url)).toBe(shouldMatch);
  });
});
