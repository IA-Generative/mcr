import { describe, expect, test } from 'vitest';
import {
  comuPrivateUrlValidator,
  visioUrlValidator,
  webinaireModeratorUrlValidator,
} from './meeting.schema';

// test

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

const HASH = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678'; // 40 lowercase hex chars

const webinaireModeratorTestCases: TestCase[] = [
  // ✅ Valid
  {
    name: 'Valid URL with creator segment',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/creator/456/hash/${HASH}`,
    shouldMatch: true,
  },
  {
    name: 'Valid URL without creator segment (creator is optional)',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/hash/${HASH}`,
    shouldMatch: true,
  },
  {
    name: 'Valid URL with long numeric ids',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/9876543210/creator/1234567890/hash/${HASH}`,
    shouldMatch: true,
  },

  // ❌ Invalid
  {
    name: 'Attendee role instead of moderator',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/invite/123/hash/${HASH}`,
    shouldMatch: false,
  },
  {
    name: 'Missing role segment',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/123/hash/${HASH}`,
    shouldMatch: false,
  },
  {
    name: 'Missing hash',
    url: 'https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/creator/456',
    shouldMatch: false,
  },
  {
    name: 'Hash too short (39 chars)',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/hash/${HASH.slice(0, 39)}`,
    shouldMatch: false,
  },
  {
    name: 'Hash too long (41 chars)',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/hash/${HASH}9`,
    shouldMatch: false,
  },
  {
    name: 'Uppercase hex in hash',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/hash/${HASH.toUpperCase()}`,
    shouldMatch: false,
  },
  {
    name: 'Non-numeric meeting ID',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/abc/hash/${HASH}`,
    shouldMatch: false,
  },
  {
    name: 'Non-numeric creator ID',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/creator/abc/hash/${HASH}`,
    shouldMatch: false,
  },
  {
    name: 'Creator keyword without id',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/creator/hash/${HASH}`,
    shouldMatch: false,
  },
  {
    name: 'HTTP instead of HTTPS',
    url: `http://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/hash/${HASH}`,
    shouldMatch: false,
  },
  {
    name: 'Wrong domain',
    url: `https://webinaire.numerique.gouv.eu/meeting/signin/moderateur/123/hash/${HASH}`,
    shouldMatch: false,
  },
  {
    name: 'Trailing slash',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/hash/${HASH}/`,
    shouldMatch: false,
  },
  {
    name: 'Extra query params',
    url: `https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/hash/${HASH}?foo=bar`,
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

describe('webinaireModeratorUrlRegex match tests', () => {
  test.each(webinaireModeratorTestCases)('$name', ({ url, shouldMatch }) => {
    expect(webinaireModeratorUrlValidator.test(url)).toBe(shouldMatch);
  });
});
