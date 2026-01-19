from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_minio(mocker: MockerFixture) -> Mock:
    bucket_name = "my_bucket"
    mock_minio = mocker.patch("mcr_capture_worker.services.s3_service.s3_client")
    mock_minio.put_object.return_value = SimpleNamespace(
        bucket_name=bucket_name,
        object_name="my/super/file",
    )

    return mock_minio
