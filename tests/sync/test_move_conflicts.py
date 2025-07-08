"""Test file move conflict handling in sync service."""

import pytest
from pathlib import Path
from unittest.mock import patch
from sqlalchemy.exc import IntegrityError

from basic_memory.config import ProjectConfig
from basic_memory.sync.sync_service import SyncService
from basic_memory.services import EntityService


async def create_test_file(path: Path, content: str = "test content") -> None:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.mark.asyncio
async def test_handle_move_file_path_conflict(
    sync_service: SyncService, project_config: ProjectConfig, entity_service: EntityService
):
    """Test that handle_move handles file path conflicts gracefully."""
    project_dir = project_config.home
    
    # Create two files that will be swapped
    file_a_content = """
---
type: knowledge
---
# File A
Content of file A
"""
    file_b_content = """
---
type: knowledge
---
# File B
Content of file B
"""
    
    await create_test_file(project_dir / "file_a.md", file_a_content)
    await create_test_file(project_dir / "file_b.md", file_b_content)
    
    # Initial sync
    await sync_service.sync(project_config.home)
    
    # Verify entities exist
    entity_a = await entity_service.get_by_file_path("file_a.md")
    entity_b = await entity_service.get_by_file_path("file_b.md")
    assert entity_a is not None
    assert entity_b is not None
    
    # Now simulate a file swap - this should cause the conflict
    # Mock the repository update to raise IntegrityError on first call
    original_update = sync_service.entity_repository.update
    call_count = 0
    
    async def mock_update(entity_id, updates):
        nonlocal call_count
        call_count += 1
        
        # Simulate the constraint violation on first call
        if call_count == 1 and updates.get("file_path") == "file_b.md":
            raise IntegrityError("UNIQUE constraint failed: entity.file_path, entity.project_id", None, None)
        else:
            return await original_update(entity_id, updates)
    
    with patch.object(sync_service.entity_repository, "update", side_effect=mock_update):
        # This should handle the conflict gracefully using temporary path
        await sync_service.handle_move("file_a.md", "file_b.md")
    
    # Verify the entity was updated successfully
    updated_entity = await entity_service.get_by_file_path("file_b.md")
    assert updated_entity is not None
    assert updated_entity.id == entity_a.id  # Same entity, just moved


@pytest.mark.asyncio 
async def test_handle_move_other_integrity_error_reraise(
    sync_service: SyncService, project_config: ProjectConfig, entity_service: EntityService
):
    """Test that handle_move re-raises non-file-path IntegrityErrors."""
    project_dir = project_config.home
    
    # Create a file
    file_content = """
---
type: knowledge
---
# Test File
Content
"""
    await create_test_file(project_dir / "test.md", file_content)
    
    # Initial sync
    await sync_service.sync(project_config.home)
    
    # Mock the repository update to raise a different IntegrityError
    async def mock_update(entity_id, updates):
        raise IntegrityError("UNIQUE constraint failed: entity.some_other_field", None, None)
    
    with patch.object(sync_service.entity_repository, "update", side_effect=mock_update):
        # Should re-raise the IntegrityError since it's not a file_path constraint
        with pytest.raises(IntegrityError, match="UNIQUE constraint failed: entity.some_other_field"):
            await sync_service.handle_move("test.md", "moved_test.md")


@pytest.mark.asyncio
async def test_handle_move_file_swap_simulation(
    sync_service: SyncService, project_config: ProjectConfig, entity_service: EntityService
):
    """Test handling of file swap scenario that triggers the original bug."""
    project_dir = project_config.home
    
    # Create two files similar to the original error scenario
    file_a_content = """
---
type: knowledge
---
# Finance Document
Financial analysis content
"""
    file_b_content = """
---
type: knowledge
---
# Other Document
Other content
"""
    
    await create_test_file(project_dir / "Finance/document.md", file_a_content)
    await create_test_file(project_dir / "Other/document.md", file_b_content)
    
    # Initial sync
    await sync_service.sync(project_config.home)
    
    # Get original entities
    entity_a = await entity_service.get_by_file_path("Finance/document.md")
    entity_b = await entity_service.get_by_file_path("Other/document.md")
    
    # Simulate the exact scenario from the bug report
    # First move should work, second should trigger conflict
    await sync_service.handle_move("Finance/document.md", "temp_location.md")
    await sync_service.handle_move("Other/document.md", "Finance/document.md")
    
    # This should now work with the temporary path resolution
    await sync_service.handle_move("temp_location.md", "Other/document.md")
    
    # Verify entities were swapped correctly
    swapped_a = await entity_service.get_by_file_path("Other/document.md")
    swapped_b = await entity_service.get_by_file_path("Finance/document.md")
    
    assert swapped_a.id == entity_a.id  # Original A is now in Other location
    assert swapped_b.id == entity_b.id  # Original B is now in Finance location