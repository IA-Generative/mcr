# Factory Boy Test Factories

This directory contains Factory Boy factories for generating test data. These factories create realistic database objects for use in integration tests, significantly reducing boilerplate code.

## Overview

Factory Boy factories provide:

- **Realistic test data** using Faker for names, emails, etc.
- **Proper database persistence** with automatic ID generation
- **Relationship management** through SubFactory
- **Reusable traits** for common variations
- **Session integration** with the test transaction system

## Available Factories

### UserFactory

Creates User instances with realistic data.

```python
from tests.factories import UserFactory

# Basic creation
user = UserFactory()

# With specific fields
user = UserFactory(email="test@example.com", first_name="John")

# Using traits
admin = UserFactory(admin=True)
member = UserFactory(xforce=True)
```

**Traits:**

- `admin=True` - Creates admin user with Role.ADMIN

### MeetingFactory

Creates Meeting instances with automatic owner user creation.

```python
from tests.factories import MeetingFactory

# Basic creation (auto-creates owner)
meeting = MeetingFactory()

# With specific owner
user = UserFactory()
meeting = MeetingFactory(owner=user)

# Using traits
import_meeting = MeetingFactory(import_meeting=True)
meeting_with_dates = MeetingFactory(with_dates=True)
```

**Traits:**

- `import_meeting=True` - MCR_IMPORT platform, no URL/platform_id
- `record_meeting=True` - MCR_RECORD platform, no URL/platform_id
- `with_dates=True` - Sets start_date and end_date
- `with_transcription=True` - Sets transcription_filename and TRANSCRIPTION_DONE status
- `with_report=True` - Sets report_filename and REPORT_DONE status

### TranscriptionFactory

Creates Transcription instances with auto-incrementing indices.

```python
from tests.factories import TranscriptionFactory

# Basic creation (auto-creates meeting)
transcription = TranscriptionFactory()

# For specific meeting
meeting = MeetingFactory()
transcription = TranscriptionFactory(meeting=meeting)

# Batch creation with sequential indices
transcriptions = TranscriptionFactory.create_batch(5, meeting=meeting)
```

**Traits:**

- `short_text=True` - Generates short transcription text
- `long_text=True` - Generates long transcription text

### MeetingTransitionRecordFactory

Creates MeetingTransitionRecord instances with automatic meeting creation.

```python
from tests.factories import MeetingTransitionRecordFactory

# Basic creation
record = MeetingTransitionRecordFactory()

# For specific meeting
meeting = MeetingFactory()
record = MeetingTransitionRecordFactory(meeting_id=meeting.id)

# Using traits
record = MeetingTransitionRecordFactory(with_prediction=True)
```

**Traits:**

- `with_prediction=True` - Sets predicted_date_of_next_transition
- `transcription_pending=True` - TRANSCRIPTION_PENDING status with prediction
- `transcription_in_progress=True` - TRANSCRIPTION_IN_PROGRESS status with prediction

## Usage in Tests

### Basic Usage

```python
def test_meeting_creation(db_session):
    """The db_session fixture is required for factories to work."""
    meeting = MeetingFactory()

    assert meeting.id is not None
    assert meeting.owner is not None
    assert meeting.name is not None
```

### Using Fixtures

Pre-configured fixtures are available in `tests/services/conftest.py`:

```python
def test_with_fixture(visio_meeting):
    """Use pre-configured meeting fixture."""
    assert visio_meeting.name_platform == MeetingPlatforms.COMU
    assert visio_meeting.status == MeetingStatus.NONE
```

Available fixtures:

- `orchestrator_user` - Basic user
- `visio_meeting` - COMU meeting with NONE status
- `import_meeting` - MCR_IMPORT meeting
- `record_meeting` - MCR_RECORD meeting

### Batch Creation

```python
def test_batch_users(db_session):
    users = UserFactory.create_batch(10)
    assert len(users) == 10
    assert all(u.id is not None for u in users)

def test_batch_transcriptions(db_session):
    meeting = MeetingFactory()
    transcriptions = TranscriptionFactory.create_batch(5, meeting=meeting)

    assert len(transcriptions) == 5
    assert all(t.meeting_id == meeting.id for t in transcriptions)
```

### Combining Traits and Overrides

```python
def test_complex_meeting(db_session):
    meeting = MeetingFactory(
        import_meeting=True,  # Trait
        with_dates=True,      # Trait
        name="Custom Name",   # Override
    )

    assert meeting.name_platform == MeetingPlatforms.MCR_IMPORT
    assert meeting.start_date is not None
    assert meeting.name == "Custom Name"
```

## How It Works

### Session Management

Factories integrate with the test session management system:

1. The `db_session` fixture (in `tests/conftest.py`) creates a test transaction
2. It sets the session in a context variable using `db_session_ctx.set(session)`
3. Factories use `BaseFactory._create()` which calls `get_db_session_ctx()`
4. This ensures factories use the same session as repositories
5. Objects are flushed (not committed) to get IDs
6. At test end, the transaction rolls back, cleaning up all data

### BaseFactory

All factories inherit from `BaseFactory` which:

- Uses `get_db_session_ctx()` to access the test session
- Flushes instead of commits to stay in the transaction
- Provides consistent behavior across all factories

```python
class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        session = get_db_session_ctx()
        obj = model_class(*args, **kwargs)
        session.add(obj)
        session.flush()
        return obj
```

## File Structure

```
tests/factories/
├── __init__.py                             # Factory exports
├── base.py                                 # BaseFactory with session management
├── user_factory.py                         # UserFactory
├── meeting_factory.py                      # MeetingFactory
├── transcription_factory.py                # TranscriptionFactory
├── meeting_transition_record_factory.py    # MeetingTransitionRecordFactory
├── test_factories.py                       # Factory tests
├── README.md                               # This file
└── MIGRATION_EXAMPLE.md                    # Migration guide
```

## Best Practices

### 1. Use Factories for Integration Tests

Factories are ideal for integration tests where you need real database objects:

```python
def test_meeting_service_integration(db_session):
    meeting = MeetingFactory(status=MeetingStatus.NONE)
    service.transition_to_capture_pending(meeting.id)

    updated = meeting_repository.get_by_id(meeting.id)
    assert updated.status == MeetingStatus.CAPTURE_PENDING
```

### 2. Keep Factory Definitions Simple

Let Faker generate realistic data; only override when necessary:

```python
# Good
meeting = MeetingFactory()

# Also good - specific requirement
meeting = MeetingFactory(status=MeetingStatus.CAPTURE_DONE)

# Avoid - unnecessary overrides
meeting = MeetingFactory(
    name="Test Meeting 1",
    creation_date=datetime.now(),
    # ... lots of manual fields
)
```

### 3. Use Traits for Common Variations

Define traits for variations you use frequently:

```python
# Good - using trait
meeting = MeetingFactory(import_meeting=True)

# Avoid - manual setup every time
meeting = MeetingFactory(
    name_platform=MeetingPlatforms.MCR_IMPORT,
    url=None,
    meeting_platform_id=None,
)
```

### 4. Use Fixtures for Common Test Objects

Create fixtures in `conftest.py` for objects used across multiple tests:

```python
# tests/services/conftest.py
@pytest.fixture
def transcription_meeting(db_session):
    return MeetingFactory(
        with_dates=True,
        status=MeetingStatus.TRANSCRIPTION_PENDING,
    )

# In tests
def test_transcription(transcription_meeting):
    # Use the fixture
    pass
```

### 5. Batch Creation for Performance

When you need multiple similar objects, use batch creation:

```python
# Good - batch creation
meetings = MeetingFactory.create_batch(10, status=MeetingStatus.NONE)

# Avoid - loop
meetings = [MeetingFactory(status=MeetingStatus.NONE) for _ in range(10)]
```

## Adding New Factories

To add a factory for a new model:

1. Create a new file: `tests/factories/new_model_factory.py`
2. Import and extend `BaseFactory`
3. Define the model and fields
4. Add traits as needed
5. Export from `__init__.py`
6. Add tests in `test_factories.py`

Example:

```python
# tests/factories/new_model_factory.py
from factory import Faker, LazyAttribute
from .base import BaseFactory
from mcr_meeting.app.models import NewModel

class NewModelFactory(BaseFactory):
    class Meta:
        model = NewModel

    name = Faker("name")
    value = 42

    class Params:
        special = factory.Trait(
            value=100,
        )
```

## Testing Factories

All factories have tests in `test_factories.py`. When adding/modifying factories, ensure:

1. Basic creation works
2. Traits work correctly
3. Relationships create proper foreign keys
4. Batch creation works
5. Overrides work

Run factory tests:

```bash
uv run pytest tests/factories/test_factories.py -v
```

## Troubleshooting

### "No DB session found in context"

Make sure your test function has `db_session` as a parameter:

```python
# Wrong
def test_something():
    meeting = MeetingFactory()  # Error!

# Correct
def test_something(db_session):
    meeting = MeetingFactory()  # Works!
```

### Objects Don't Persist Between Test Functions

This is by design - each test gets a fresh transaction that rolls back. To share data, use fixtures:

```python
@pytest.fixture
def shared_user(db_session):
    return UserFactory()

def test_one(shared_user):
    # Use shared_user

def test_two(shared_user):
    # Gets fresh shared_user (from new transaction)
```

### Circular Import Errors

If you get circular imports, use TYPE_CHECKING:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .meeting_factory import MeetingFactory
```

## Resources

- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)
- [SQLAlchemy Factory Boy Integration](https://factoryboy.readthedocs.io/en/stable/orms.html#sqlalchemy)
- [Faker Documentation](https://faker.readthedocs.io/)
