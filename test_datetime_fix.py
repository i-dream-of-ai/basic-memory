#!/usr/bin/env python3
"""Test script to verify datetime serialization fix."""

import json
from datetime import datetime, timezone
from basic_memory.schemas.memory import EntitySummary, RelationSummary, ObservationSummary, MemoryMetadata

def test_datetime_serialization():
    """Test that datetime fields are serialized with timezone information."""
    
    # Test EntitySummary
    entity = EntitySummary(
        permalink="/test",
        title="Test Entity",
        file_path="/test.md",
        created_at=datetime.now(timezone.utc)
    )
    
    entity_json = entity.model_dump_json()
    entity_dict = json.loads(entity_json)
    
    print("EntitySummary created_at:", entity_dict["created_at"])
    assert entity_dict["created_at"].endswith("+00:00") or entity_dict["created_at"].endswith("Z"), \
        f"EntitySummary created_at should have timezone: {entity_dict['created_at']}"
    
    # Test RelationSummary
    relation = RelationSummary(
        title="Test Relation",
        file_path="/test.md",
        permalink="/test-rel",
        relation_type="relates_to",
        created_at=datetime.now(timezone.utc)
    )
    
    relation_json = relation.model_dump_json()
    relation_dict = json.loads(relation_json)
    
    print("RelationSummary created_at:", relation_dict["created_at"])
    assert relation_dict["created_at"].endswith("+00:00") or relation_dict["created_at"].endswith("Z"), \
        f"RelationSummary created_at should have timezone: {relation_dict['created_at']}"
    
    # Test ObservationSummary
    observation = ObservationSummary(
        title="Test Observation",
        file_path="/test.md",
        permalink="/test-obs",
        category="test",
        content="Test content",
        created_at=datetime.now(timezone.utc)
    )
    
    observation_json = observation.model_dump_json()
    observation_dict = json.loads(observation_json)
    
    print("ObservationSummary created_at:", observation_dict["created_at"])
    assert observation_dict["created_at"].endswith("+00:00") or observation_dict["created_at"].endswith("Z"), \
        f"ObservationSummary created_at should have timezone: {observation_dict['created_at']}"
    
    # Test MemoryMetadata
    metadata = MemoryMetadata(
        depth=1,
        generated_at=datetime.now(timezone.utc)
    )
    
    metadata_json = metadata.model_dump_json()
    metadata_dict = json.loads(metadata_json)
    
    print("MemoryMetadata generated_at:", metadata_dict["generated_at"])
    assert metadata_dict["generated_at"].endswith("+00:00") or metadata_dict["generated_at"].endswith("Z"), \
        f"MemoryMetadata generated_at should have timezone: {metadata_dict['generated_at']}"
    
    print("✅ All datetime serialization tests passed!")
    
    # Test with naive datetime to ensure it gets converted to UTC
    naive_dt = datetime(2025, 8, 22, 15, 30, 45, 123456)
    entity_naive = EntitySummary(
        permalink="/test-naive",
        title="Test Naive Entity",
        file_path="/test-naive.md",
        created_at=naive_dt
    )
    
    entity_naive_json = entity_naive.model_dump_json()
    entity_naive_dict = json.loads(entity_naive_json)
    
    print("Naive datetime converted to:", entity_naive_dict["created_at"])
    assert entity_naive_dict["created_at"].endswith("+00:00") or entity_naive_dict["created_at"].endswith("Z"), \
        f"Naive datetime should be converted to UTC: {entity_naive_dict['created_at']}"
    
    print("✅ Naive datetime conversion test passed!")

if __name__ == "__main__":
    test_datetime_serialization()