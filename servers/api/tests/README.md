# API Integration Tests

## Running Tests

```bash
cd servers/api
.venv/bin/pytest tests/ -v
```

## Test Coverage

All 22 integration tests cover:

### Basic CRUD Operations
- ✅ Health check endpoint
- ✅ Create task
- ✅ Get task by ID
- ✅ Get nonexistent task (404 error)
- ✅ List all tasks
- ✅ Update task
- ✅ Delete task

### Pagination & Filtering
- ✅ List tasks with pagination (page, page_size)
- ✅ Filter tasks by status
- ✅ List root tasks (no parent)
- ✅ List subtasks of a parent

### Task Hierarchy
- ✅ Create subtasks with parent_task_id
- ✅ Multi-level task hierarchy (grandparent → parent → child)
- ✅ Subtask creation and retrieval
- ✅ Prevent circular references
- ✅ Validation for nonexistent parent

### Deletion Strategies
- ✅ Delete task (orphans children by default)
- ✅ Delete with cascade (recursively deletes all children)

### Advanced Features
- ✅ Update task completion status
- ✅ Update priority and due date
- ✅ Create task with metadata (tags, extra_data, assignees)
- ✅ Recurring task configuration
- ✅ Complete workflow (create → update → complete → delete)

## Test Database

Tests use an in-memory SQLite database that is:
- Created fresh for each test
- Isolated (no test interference)
- Fast (no disk I/O)
- Automatically cleaned up

## Key Test Patterns

### Fixtures
- `reset_db_state` - Resets database singleton before each test
- `client` - FastAPI TestClient with test database

### Environment
Tests set `DATABASE_URL=sqlite:///:memory:` to use in-memory database.
