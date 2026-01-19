import pytest

from mcr_meeting.app.schemas.meeting_schema import (
    ComuUrlValidator,
    WebConfUrlValidator,
    WebinaireUrlValidator,
)

comu_test_cases = [
    # ✅ Valid
    (
        "Valid URL .gouv.fr",
        "https://webconf.comu.gouv.fr/meeting/123456?secret=ABCdefGHIjkl_mnoPQRstu",
        True,
    ),
    (
        "Valid URL .minint.fr",
        "https://webconf.comu.minint.fr/en-US/meeting/987654?secret=abcDEFghiJKL_mnoPQRstu",
        True,
    ),
    (
        "Valid URL .interieur.rie.gouv with language code",
        "https://webconf.comu.interieur.rie.gouv.fr/fr-FR/meeting/111222?secret=1234567890abcdefABCDEF",
        True,
    ),
    # ❌ Invalid
    (
        "Invalid domain",
        "https://webconf.comu.unknown.fr/meeting/123?secret=ABCdefGHIjkl_mnoPQRstu",
        False,
    ),
    (
        "Secret too short",
        "https://webconf.comu.gouv.fr/meeting/123?secret=shortSecret",
        False,
    ),
    (
        "Secret too long",
        "https://webconf.comu.gouv.fr/en-US/meeting/123456?secret=tooLongSecret_ABCDEFGHIJKL",
        False,
    ),
    (
        "Secret with invalid characters",
        "https://webconf.comu.gouv.fr/meeting/123?secret=invalid!char$cter",
        False,
    ),
    (
        "Non-numeric meeting Id",
        "https://webconf.comu.gouv.fr/meeting/abc?secret=ABCdefGHIjkl_mnoPQRstu",
        False,
    ),
    (
        "Missing meeting Id",
        "https://webconf.comu.gouv.fr/meeting/?secret=ABCdefGHIjkl_mnoPQRstu",
        False,
    ),
    ("Missing secret", "https://webconf.comu.gouv.fr/meeting/123", False),
    (
        "Invalid language code (missing region)",
        "https://webconf.comu.gouv.fr/en/meeting/123456?secret=ABCdefGHIjkl_mnoPQRstu",
        False,
    ),
    (
        "HTTP instead of HTTPS",
        "http://webconf.comu.gouv.fr/en-US/meeting/123456?secret=ABCdefGHIjkl_mnoPQRstu",
        False,
    ),
    (
        "Trailing slash after meeting ID",
        "https://webconf.comu.gouv.fr/en-US/meeting/123456/?secret=ABCdefGHIjkl_mnoPQRstu",
        False,
    ),
    (
        "Extra query params",
        "https://webconf.comu.gouv.fr/meeting/123456?secret=ABCdefGHIjkl_mnoPQRstu&token=abc",
        False,
    ),
]


@pytest.mark.parametrize("name,url,should_match", comu_test_cases)
def test_comu_url_validator(name: str, url: str, should_match: bool) -> None:
    validator = ComuUrlValidator()
    result = validator.validate_url(url)
    assert result == should_match, f"{name} failed"


webinaire_test_cases = [
    # ✅ Valid URLs
    (
        "Valid URL",
        "https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/creator/456/hash/abcdef0123456789abcdef0123456789abcdef01",
        True,
    ),
    # ❌ Invalid domain
    (
        "Invalid domain",
        "https://webinaire.numerique.gouv.eu/meeting/signin/moderateur/123/creator/456/hash/abcdef0123456789abcdef0123456789abcdef01",
        False,
    ),
    (
        "Missing https",
        "http://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/creator/456/hash/abcdef0123456789abcdef0123456789abcdef01",
        False,
    ),
    (
        "Non-numeric user_id",
        "https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/abc/creator/456/hash/abcdef0123456789abcdef0123456789abcdef01",
        False,
    ),
    (
        "Non-numeric creator_id",
        "https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/creator/xyz/hash/abcdef0123456789abcdef0123456789abcdef01",
        False,
    ),
    (
        "Hash too short",
        "https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/creator/456/hash/abc123",
        False,
    ),
    (
        "Hash too long",
        "https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/creator/456/hash/abcdef0123456789abcdef0123456789abcdef012345",
        False,
    ),
    (
        "Hash with invalid characters",
        "https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/creator/456/hash/abcdef0123456789abcdef0123456789abcdef0G",
        False,
    ),
    (
        "Missing /creator segment",
        "https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/hash/abcdef0123456789abcdef0123456789abcdef01",
        False,
    ),
    (
        "Extra trailing slash",
        "https://webinaire.numerique.gouv.fr/meeting/signin/moderateur/123/creator/456/hash/abcdef0123456789abcdef0123456789abcdef01/",
        False,
    ),
]


@pytest.mark.parametrize("name,url,should_match", webinaire_test_cases)
def test_webinaire_url_validator(name: str, url: str, should_match: bool) -> None:
    validator = WebinaireUrlValidator()
    assert validator.validate_url(url) == should_match, f"{name} failed"


webconf_test_cases = [
    # ✅ Valid URLs
    (
        "Valid URL",
        "https://webconf.numerique.gouv.fr/1234567890",
        True,
    ),
    (
        "Valid URL",
        "https://webconf.numerique.gouv.fr/TestMI1234",
        True,
    ),
    (
        "Valid URL",
        "https://webconf.numerique.gouv.fr/Test123456",
        True,
    ),
    # ❌ Invalid domain
    (
        "Invalid domain",
        "https://webconf.numerique.gouv.eu/Test123456",
        False,
    ),
    (
        "Missing https",
        "http://webconf.numerique.gouv.fr/Test123456",
        False,
    ),
    (
        "Non-alphanumeric meeting Id",
        "https://webconf.numerique.gouv.fr/!@#$%^&*()",
        False,
    ),
    (
        "Missing meeting name",
        "https://webconf.numerique.gouv.fr/",
        False,
    ),
    (
        "Less than 3 digits",
        "https://webconf.numerique.gouv.fr/TestTest23",
        False,
    ),
    (
        "Less than 10 characters",
        "https://webconf.numerique.gouv.fr/TestTest2",
        False,
    ),
]


@pytest.mark.parametrize("name,url,should_match", webconf_test_cases)
def test_webconf_url_validator(name: str, url: str, should_match: bool) -> None:
    validator = WebConfUrlValidator()
    assert validator.validate_url(url) == should_match, f"{name} failed"
