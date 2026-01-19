import pytest

from mcr_meeting.app.schemas.S3_types import S3Object
from mcr_meeting.app.services.s3_service import get_extension_from_object_list


class TestGetExtensionFromObjectList:
    """Tests pour la fonction get_extension_from_object_list."""

    def test_should_raise_value_error_when_empty_iterator(self):
        """Test que la fonction lève ValueError pour un itérateur vide."""
        empty_iterator = iter([])

        with pytest.raises(
            ValueError, match="No audio files found for the specified meeting"
        ):
            get_extension_from_object_list(empty_iterator)

    def test_should_return_correct_extension_when_single_object(self):
        """Test que la fonction retourne la bonne extension pour un objet unique."""
        s3_object = S3Object(
            bucket_name="test-bucket",
            object_name="123/audio_chunk.weba",
            last_modified="2023-01-01T00:00:00Z",
        )
        reconstructed_iterator, file_extension = get_extension_from_object_list(
            iter([s3_object])
        )

        assert file_extension == "weba"
        reconstructed_objects = list(reconstructed_iterator)
        assert len(reconstructed_objects) == 1
        assert reconstructed_objects[0].object_name == "123/audio_chunk.weba"

    def test_should_return_correct_extension_when_multiple_objects(self):
        """Test que la fonction retourne l'extension du premier objet avec plusieurs objets."""
        s3_objects = [
            S3Object(
                bucket_name="test-bucket",
                object_name="123/audio_chunk_1.weba",
                last_modified="2023-01-01T00:00:00Z",
            ),
            S3Object(
                bucket_name="test-bucket",
                object_name="123/audio_chunk_2.weba",
                last_modified="2023-01-01T00:01:00Z",
            ),
            S3Object(
                bucket_name="test-bucket",
                object_name="123/audio_chunk_3.mp3",
                last_modified="2023-01-01T00:02:00Z",
            ),
        ]

        reconstructed_iterator, file_extension = get_extension_from_object_list(
            iter(s3_objects)
        )

        assert file_extension == "weba"
        reconstructed_objects = list(reconstructed_iterator)
        assert len(reconstructed_objects) == 3
        assert reconstructed_objects[0].object_name == "123/audio_chunk_1.weba"
        assert reconstructed_objects[1].object_name == "123/audio_chunk_2.weba"
        assert reconstructed_objects[2].object_name == "123/audio_chunk_3.mp3"

    def test_should_handle_file_without_extension(self):
        """Test la gestion des fichiers sans extension."""
        s3_object = S3Object(
            bucket_name="test-bucket",
            object_name="123/audio_chunk_no_ext",
            last_modified="2023-01-01T00:00:00Z",
        )

        reconstructed_iterator, file_extension = get_extension_from_object_list(
            iter([s3_object])
        )

        assert file_extension == "123/audio_chunk_no_ext"

    def test_should_handle_file_with_multiple_dots(self):
        """Test la gestion des fichiers avec plusieurs points dans le nom."""
        s3_object = S3Object(
            bucket_name="test-bucket",
            object_name="123/audio.chunk.test.weba",
            last_modified="2023-01-01T00:00:00Z",
        )

        reconstructed_iterator, file_extension = get_extension_from_object_list(
            iter([s3_object])
        )

        assert file_extension == "weba"

    def test_should_handle_file_ending_with_dot(self):
        """Test la gestion des fichiers se terminant par un point."""
        s3_object = S3Object(
            bucket_name="test-bucket",
            object_name="123/audio_chunk.",
            last_modified="2023-01-01T00:00:00Z",
        )

        reconstructed_iterator, file_extension = get_extension_from_object_list(
            iter([s3_object])
        )

        assert file_extension == ""

    def test_should_preserve_iterator_order(self):
        """Test que l'ordre des objets est préservé dans l'itérateur reconstruit."""
        s3_objects = [
            S3Object(
                bucket_name="test",
                object_name="123/chunk_1.weba",
                last_modified="2023-01-01T00:00:00Z",
            ),
            S3Object(
                bucket_name="test",
                object_name="123/chunk_2.weba",
                last_modified="2023-01-01T00:01:00Z",
            ),
            S3Object(
                bucket_name="test",
                object_name="123/chunk_3.weba",
                last_modified="2023-01-01T00:02:00Z",
            ),
        ]

        reconstructed_iterator, file_extension = get_extension_from_object_list(
            iter(s3_objects)
        )
        reconstructed_objects = list(reconstructed_iterator)

        assert len(reconstructed_objects) == 3
        assert reconstructed_objects[0].object_name == "123/chunk_1.weba"
        assert reconstructed_objects[1].object_name == "123/chunk_2.weba"
        assert reconstructed_objects[2].object_name == "123/chunk_3.weba"

    def test_should_handle_different_extensions_correctly(self):
        """Test la gestion de différentes extensions communes."""
        test_cases = [
            ("123/audio.mp3", "mp3"),
            ("123/audio.wav", "wav"),
            ("123/audio.weba", "weba"),
            ("123/audio.m4a", "m4a"),
            ("123/audio.ogg", "ogg"),
            ("123/audio.flac", "flac"),
        ]

        for object_name, expected_extension in test_cases:
            s3_object = S3Object(
                bucket_name="test-bucket",
                object_name=object_name,
                last_modified="2023-01-01T00:00:00Z",
            )

            reconstructed_iterator, file_extension = get_extension_from_object_list(
                iter([s3_object])
            )

            assert file_extension == expected_extension, f"Failed for {object_name}"
