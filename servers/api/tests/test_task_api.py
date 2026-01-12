import pytest
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_task(client: TestClient):
    """Test creating a task."""
    payload = {
        "title": "Test Task",
        "description": "This is a test task",
        "status": "todo",
        "priority": "medium"
    }

    response = client.post("/api/v1/tasks/", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Test Task"
    assert data["description"] == "This is a test task"
    assert data["status"] == "todo"
    assert data["priority"] == "medium"
    assert "id" in data
    assert data["owner_user_id"] == "hardcoded-user-123"

def test_get_task(client: TestClient):
    """Test retrieving a task by ID."""
    # Create a task first
    create_response = client.post("/api/v1/tasks/", json={
        "title": "Get Test Task",
        "description": "Task to retrieve"
    })
    task_id = create_response.json()["id"]

    # Get the task
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == "Get Test Task"

def test_get_nonexistent_task(client: TestClient):
    """Test getting a task that doesn't exist."""
    response = client.get("/api/v1/tasks/nonexistent-id")
    assert response.status_code == 404

def test_list_tasks(client: TestClient):
    """Test listing tasks."""
    # Create multiple tasks
    for i in range(3):
        client.post("/api/v1/tasks/", json={
            "title": f"Task {i}",
            "description": f"Description {i}"
        })

    # List all tasks
    response = client.get("/api/v1/tasks/")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3
    assert len(data["tasks"]) == 3
    assert data["page"] == 1
    assert data["page_size"] == 50

def test_list_tasks_with_pagination(client: TestClient):
    """Test listing tasks with pagination."""
    # Create 5 tasks
    for i in range(5):
        client.post("/api/v1/tasks/", json={"title": f"Task {i}"})

    # Get page 1 with page_size=2
    response = client.get("/api/v1/tasks/?page=1&page_size=2")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 5
    assert len(data["tasks"]) == 2
    assert data["page"] == 1

    # Get page 2
    response = client.get("/api/v1/tasks/?page=2&page_size=2")
    data = response.json()
    assert len(data["tasks"]) == 2
    assert data["page"] == 2

def test_list_root_tasks(client: TestClient):
    """Test listing only root tasks (no parent)."""
    # Create parent task
    parent_response = client.post("/api/v1/tasks/", json={"title": "Parent Task"})
    parent_id = parent_response.json()["id"]

    # Create child task
    client.post("/api/v1/tasks/", json={
        "title": "Child Task",
        "parent_task_id": parent_id
    })

    # Create another root task
    client.post("/api/v1/tasks/", json={"title": "Another Root"})

    # List only root tasks
    response = client.get("/api/v1/tasks/?parent_id=root")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2  # Only parent and "Another Root"
    assert all(task["parent_task_id"] is None for task in data["tasks"])

def test_list_subtasks(client: TestClient):
    """Test listing subtasks of a parent."""
    # Create parent
    parent_response = client.post("/api/v1/tasks/", json={"title": "Parent"})
    parent_id = parent_response.json()["id"]

    # Create children
    for i in range(3):
        client.post("/api/v1/tasks/", json={
            "title": f"Subtask {i}",
            "parent_task_id": parent_id
        })

    # List subtasks
    response = client.get(f"/api/v1/tasks/?parent_id={parent_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3
    assert all(task["parent_task_id"] == parent_id for task in data["tasks"])

def test_filter_by_status(client: TestClient):
    """Test filtering tasks by status."""
    # Create tasks with different statuses
    client.post("/api/v1/tasks/", json={"title": "Task 1", "status": "todo"})
    client.post("/api/v1/tasks/", json={"title": "Task 2", "status": "in_progress"})
    client.post("/api/v1/tasks/", json={"title": "Task 3", "status": "completed"})

    # Filter by todo status
    response = client.get("/api/v1/tasks/?status=todo")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["tasks"][0]["title"] == "Task 1"

def test_update_task(client: TestClient):
    """Test updating a task."""
    # Create task
    create_response = client.post("/api/v1/tasks/", json={
        "title": "Original Title",
        "description": "Original description"
    })
    task_id = create_response.json()["id"]

    # Update task
    update_payload = {
        "title": "Updated Title",
        "status": "in_progress",
        "priority": "high"
    }
    response = client.patch(f"/api/v1/tasks/{task_id}", json=update_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"
    assert data["description"] == "Original description"  # Unchanged

def test_update_task_completion(client: TestClient):
    """Test marking a task as completed."""
    # Create task
    create_response = client.post("/api/v1/tasks/", json={"title": "Task to complete"})
    task_id = create_response.json()["id"]

    # Mark as completed
    response = client.patch(f"/api/v1/tasks/{task_id}", json={
        "status": "completed",
        "completed_at": "2026-01-13T10:00:00"
    })
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None

def test_delete_task(client: TestClient):
    """Test deleting a task."""
    # Create task
    create_response = client.post("/api/v1/tasks/", json={"title": "Task to delete"})
    task_id = create_response.json()["id"]

    # Delete task
    response = client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify it's gone
    get_response = client.get(f"/api/v1/tasks/{task_id}")
    assert get_response.status_code == 404

def test_delete_task_orphan_subtasks(client: TestClient):
    """Test deleting a parent task orphans subtasks by default."""
    # Create parent
    parent_response = client.post("/api/v1/tasks/", json={"title": "Parent"})
    parent_id = parent_response.json()["id"]

    # Create child
    child_response = client.post("/api/v1/tasks/", json={
        "title": "Child",
        "parent_task_id": parent_id
    })
    child_id = child_response.json()["id"]

    # Delete parent (without cascade)
    response = client.delete(f"/api/v1/tasks/{parent_id}")
    assert response.status_code == 200

    # Child should still exist but orphaned
    child_get = client.get(f"/api/v1/tasks/{child_id}")
    assert child_get.status_code == 200
    assert child_get.json()["parent_task_id"] is None

def test_delete_task_cascade(client: TestClient):
    """Test deleting a parent task with cascade deletes subtasks."""
    # Create parent
    parent_response = client.post("/api/v1/tasks/", json={"title": "Parent"})
    parent_id = parent_response.json()["id"]

    # Create child
    child_response = client.post("/api/v1/tasks/", json={
        "title": "Child",
        "parent_task_id": parent_id
    })
    child_id = child_response.json()["id"]

    # Delete parent with cascade
    response = client.delete(f"/api/v1/tasks/{parent_id}?cascade=true")
    assert response.status_code == 200

    # Child should also be deleted
    child_get = client.get(f"/api/v1/tasks/{child_id}")
    assert child_get.status_code == 404

def test_prevent_circular_reference(client: TestClient):
    """Test that circular references are prevented."""
    # Create parent
    parent_response = client.post("/api/v1/tasks/", json={"title": "Parent"})
    parent_id = parent_response.json()["id"]

    # Create child
    child_response = client.post("/api/v1/tasks/", json={
        "title": "Child",
        "parent_task_id": parent_id
    })
    child_id = child_response.json()["id"]

    # Try to make parent a child of child (should fail)
    response = client.patch(f"/api/v1/tasks/{parent_id}", json={
        "parent_task_id": child_id
    })
    assert response.status_code == 400
    assert "circular" in response.json()["detail"].lower()

def test_create_task_with_nonexistent_parent(client: TestClient):
    """Test creating a task with non-existent parent fails."""
    response = client.post("/api/v1/tasks/", json={
        "title": "Orphan Task",
        "parent_task_id": "nonexistent-parent-id"
    })
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()

def test_task_hierarchy(client: TestClient):
    """Test multi-level task hierarchy."""
    # Create grandparent
    grandparent_response = client.post("/api/v1/tasks/", json={"title": "Grandparent"})
    grandparent_id = grandparent_response.json()["id"]

    # Create parent
    parent_response = client.post("/api/v1/tasks/", json={
        "title": "Parent",
        "parent_task_id": grandparent_id
    })
    parent_id = parent_response.json()["id"]

    # Create child
    child_response = client.post("/api/v1/tasks/", json={
        "title": "Child",
        "parent_task_id": parent_id
    })

    # Get grandparent - should have subtask_ids
    grandparent_get = client.get(f"/api/v1/tasks/{grandparent_id}")
    assert parent_id in grandparent_get.json()["subtask_ids"]

    # Get parent - should have subtask_ids
    parent_get = client.get(f"/api/v1/tasks/{parent_id}")
    assert len(parent_get.json()["subtask_ids"]) == 1

def test_update_task_priority_and_due_date(client: TestClient):
    """Test updating task priority and due date."""
    # Create task
    create_response = client.post("/api/v1/tasks/", json={"title": "Task"})
    task_id = create_response.json()["id"]

    # Update
    response = client.patch(f"/api/v1/tasks/{task_id}", json={
        "priority": "urgent",
        "due_date": "2026-01-20T15:00:00"
    })
    assert response.status_code == 200

    data = response.json()
    assert data["priority"] == "urgent"
    assert data["due_date"] == "2026-01-20T15:00:00"

def test_create_task_with_metadata(client: TestClient):
    """Test creating a task with extra_data and tags."""
    payload = {
        "title": "Task with metadata",
        "tags": ["urgent", "school", "homework"],
        "extra_data": {
            "calendar_event_id": "evt_123",
            "source": "calendar"
        },
        "assignees": ["user:parent-1", "user:parent-2"]
    }

    response = client.post("/api/v1/tasks/", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["tags"] == ["urgent", "school", "homework"]
    assert data["extra_data"]["calendar_event_id"] == "evt_123"
    assert len(data["assignees"]) == 2

def test_complete_workflow(client: TestClient):
    """Test a complete task lifecycle."""
    # 1. Create task
    create_response = client.post("/api/v1/tasks/", json={
        "title": "Complete Homework",
        "description": "Math homework for tomorrow",
        "priority": "high",
        "tags": ["school", "math"]
    })
    assert create_response.status_code == 200
    task_id = create_response.json()["id"]

    # 2. Start working on it
    update_response = client.patch(f"/api/v1/tasks/{task_id}", json={
        "status": "in_progress"
    })
    assert update_response.json()["status"] == "in_progress"

    # 3. Complete it
    complete_response = client.patch(f"/api/v1/tasks/{task_id}", json={
        "status": "completed",
        "completed_at": "2026-01-13T16:00:00"
    })
    assert complete_response.json()["status"] == "completed"

    # 4. Verify completion
    get_response = client.get(f"/api/v1/tasks/{task_id}")
    task_data = get_response.json()
    assert task_data["status"] == "completed"
    assert task_data["completed_at"] is not None

    # 5. Delete it
    delete_response = client.delete(f"/api/v1/tasks/{task_id}")
    assert delete_response.json()["success"] is True

def test_subtask_creation_and_retrieval(client: TestClient):
    """Test creating and retrieving subtasks."""
    # Create main task
    parent_response = client.post("/api/v1/tasks/", json={
        "title": "Plan Birthday Party",
        "description": "Organize kids birthday party"
    })
    parent_id = parent_response.json()["id"]

    # Create subtasks
    subtask_titles = ["Book venue", "Order cake", "Send invitations"]
    subtask_ids = []

    for title in subtask_titles:
        response = client.post("/api/v1/tasks/", json={
            "title": title,
            "parent_task_id": parent_id
        })
        subtask_ids.append(response.json()["id"])

    # Get parent - should include subtask_ids
    parent_get = client.get(f"/api/v1/tasks/{parent_id}")
    parent_data = parent_get.json()
    assert len(parent_data["subtask_ids"]) == 3
    assert set(parent_data["subtask_ids"]) == set(subtask_ids)

    # List subtasks
    subtasks_response = client.get(f"/api/v1/tasks/?parent_id={parent_id}")
    subtasks_data = subtasks_response.json()
    assert subtasks_data["total"] == 3

def test_recurrence_config(client: TestClient):
    """Test creating a recurring task."""
    payload = {
        "title": "Weekly Soccer Practice",
        "recurrence_config": {
            "frequency": "weekly",
            "interval": 1,
            "by_weekday": [2, 4],  # Tuesday and Thursday
        }
    }

    response = client.post("/api/v1/tasks/", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["recurrence_config"]["frequency"] == "weekly"
    assert data["recurrence_config"]["by_weekday"] == [2, 4]
