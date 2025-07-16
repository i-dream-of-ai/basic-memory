"""Repository for managing entities in the knowledge graph."""

from pathlib import Path
from typing import List, Optional, Sequence, Union

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from basic_memory import db
from basic_memory.models.knowledge import Entity, Observation, Relation
from basic_memory.repository.repository import Repository


class EntityRepository(Repository[Entity]):
    """Repository for Entity model.

    Note: All file paths are stored as strings in the database. Convert Path objects
    to strings before passing to repository methods.
    """

    def __init__(self, session_maker: async_sessionmaker[AsyncSession], project_id: int):
        """Initialize with session maker and project_id filter.

        Args:
            session_maker: SQLAlchemy session maker
            project_id: Project ID to filter all operations by
        """
        super().__init__(session_maker, Entity, project_id=project_id)

    async def get_by_permalink(self, permalink: str) -> Optional[Entity]:
        """Get entity by permalink.

        Args:
            permalink: Unique identifier for the entity
        """
        query = self.select().where(Entity.permalink == permalink).options(*self.get_load_options())
        return await self.find_one(query)

    async def get_by_title(self, title: str) -> Sequence[Entity]:
        """Get entity by title.

        Args:
            title: Title of the entity to find
        """
        query = self.select().where(Entity.title == title).options(*self.get_load_options())
        result = await self.execute_query(query)
        return list(result.scalars().all())

    async def get_by_file_path(self, file_path: Union[Path, str]) -> Optional[Entity]:
        """Get entity by file_path.

        Args:
            file_path: Path to the entity file (will be converted to string internally)
        """
        query = (
            self.select()
            .where(Entity.file_path == str(file_path))
            .options(*self.get_load_options())
        )
        return await self.find_one(query)

    async def delete_by_file_path(self, file_path: Union[Path, str]) -> bool:
        """Delete entity with the provided file_path.

        Args:
            file_path: Path to the entity file (will be converted to string internally)
        """
        return await self.delete_by_fields(file_path=str(file_path))

    def get_load_options(self) -> List[LoaderOption]:
        """Get SQLAlchemy loader options for eager loading relationships."""
        return [
            selectinload(Entity.observations).selectinload(Observation.entity),
            # Load from_relations and both entities for each relation
            selectinload(Entity.outgoing_relations).selectinload(Relation.from_entity),
            selectinload(Entity.outgoing_relations).selectinload(Relation.to_entity),
            # Load to_relations and both entities for each relation
            selectinload(Entity.incoming_relations).selectinload(Relation.from_entity),
            selectinload(Entity.incoming_relations).selectinload(Relation.to_entity),
        ]

    async def find_by_permalinks(self, permalinks: List[str]) -> Sequence[Entity]:
        """Find multiple entities by their permalink.

        Args:
            permalinks: List of permalink strings to find
        """
        # Handle empty input explicitly
        if not permalinks:
            return []

        # Use existing select pattern
        query = (
            self.select().options(*self.get_load_options()).where(Entity.permalink.in_(permalinks))
        )

        result = await self.execute_query(query)
        return list(result.scalars().all())

    async def upsert_entity(self, entity: Entity) -> Entity:
        """Insert or update entity using a hybrid approach.

        This method provides a cleaner alternative to the try/catch approach
        for handling permalink and file_path conflicts. It first tries direct
        insertion, then handles conflicts intelligently.

        Args:
            entity: The entity to insert or update

        Returns:
            The inserted or updated entity
        """

        async with db.scoped_session(self.session_maker) as session:
            # Set project_id if applicable and not already set
            self._set_project_id_if_needed(entity)

            # Check for existing entity with same file_path first
            existing_by_path = await session.execute(
                select(Entity).where(
                    Entity.file_path == entity.file_path, Entity.project_id == entity.project_id
                )
            )
            existing_path_entity = existing_by_path.scalar_one_or_none()

            if existing_path_entity:
                # Update existing entity with same file path
                for key, value in {
                    "title": entity.title,
                    "entity_type": entity.entity_type,
                    "entity_metadata": entity.entity_metadata,
                    "content_type": entity.content_type,
                    "permalink": entity.permalink,
                    "checksum": entity.checksum,
                    "updated_at": entity.updated_at,
                }.items():
                    setattr(existing_path_entity, key, value)

                await session.flush()
                # Return with relationships loaded
                query = (
                    self.select()
                    .where(Entity.file_path == entity.file_path)
                    .options(*self.get_load_options())
                )
                result = await session.execute(query)
                found = result.scalar_one_or_none()
                if not found:  # pragma: no cover
                    raise RuntimeError(
                        f"Failed to retrieve entity after update: {entity.file_path}"
                    )
                return found

            # No existing entity with same file_path, try insert
            try:
                # Simple insert for new entity
                session.add(entity)
                await session.flush()

                # Return with relationships loaded
                query = (
                    self.select()
                    .where(Entity.file_path == entity.file_path)
                    .options(*self.get_load_options())
                )
                result = await session.execute(query)
                found = result.scalar_one_or_none()
                if not found:  # pragma: no cover
                    raise RuntimeError(
                        f"Failed to retrieve entity after insert: {entity.file_path}"
                    )
                return found

            except IntegrityError:
                # Could be either file_path or permalink conflict
                await session.rollback()

                # Check if it's a file_path conflict (race condition)
                existing_by_path_check = await session.execute(
                    select(Entity).where(
                        Entity.file_path == entity.file_path, Entity.project_id == entity.project_id
                    )
                )
                race_condition_entity = existing_by_path_check.scalar_one_or_none()

                if race_condition_entity:
                    # Race condition: file_path conflict detected after our initial check
                    # Update the existing entity instead
                    for key, value in {
                        "title": entity.title,
                        "entity_type": entity.entity_type,
                        "entity_metadata": entity.entity_metadata,
                        "content_type": entity.content_type,
                        "permalink": entity.permalink,
                        "checksum": entity.checksum,
                        "updated_at": entity.updated_at,
                    }.items():
                        setattr(race_condition_entity, key, value)

                    await session.flush()
                    # Return the updated entity with relationships loaded
                    query = (
                        self.select()
                        .where(Entity.file_path == entity.file_path)
                        .options(*self.get_load_options())
                    )
                    result = await session.execute(query)
                    found = result.scalar_one_or_none()
                    if not found:  # pragma: no cover
                        raise RuntimeError(
                            f"Failed to retrieve entity after race condition update: {entity.file_path}"
                        )
                    return found
                else:
                    # Must be permalink conflict - generate unique permalink
                    return await self._handle_permalink_conflict(entity, session)

    async def _handle_permalink_conflict(self, entity: Entity, session: AsyncSession) -> Entity:
        """Handle permalink conflicts by generating a unique permalink."""
        base_permalink = entity.permalink
        suffix = 1

        # Find a unique permalink
        while True:
            test_permalink = f"{base_permalink}-{suffix}"
            existing = await session.execute(
                select(Entity).where(
                    Entity.permalink == test_permalink, Entity.project_id == entity.project_id
                )
            )
            if existing.scalar_one_or_none() is None:
                # Found unique permalink
                entity.permalink = test_permalink
                break
            suffix += 1

        # Insert with unique permalink (no conflict possible now)
        session.add(entity)
        await session.flush()

        # Return the inserted entity with relationships loaded
        query = (
            self.select()
            .where(Entity.file_path == entity.file_path)
            .options(*self.get_load_options())
        )
        result = await session.execute(query)
        found = result.scalar_one_or_none()
        if not found:  # pragma: no cover
            raise RuntimeError(f"Failed to retrieve entity after insert: {entity.file_path}")
        return found

    async def upsert_entity_optimistic(
        self, entity_data: dict, conflict_columns: Optional[List[str]] = None
    ) -> Entity:
        """Insert or update entity using SQLite's ON CONFLICT clause for optimistic concurrency.

        This method uses SQLite's native ON CONFLICT semantics to handle race conditions
        efficiently without manual exception handling.

        Args:
            entity_data: Dictionary of entity data to insert/update
            conflict_columns: Columns to use for conflict detection (defaults to ['file_path'])

        Returns:
            The inserted or updated entity
        """
        if conflict_columns is None:
            conflict_columns = ["file_path"]

        async with db.scoped_session(self.session_maker) as session:
            # Ensure project_id is set
            if (
                self.project_id is not None
                and "project_id" not in entity_data
                and "project_id" in self.valid_columns
            ):
                entity_data["project_id"] = self.project_id

            # Create the upsert statement using SQLite's ON CONFLICT
            stmt = sqlite_insert(Entity).values(entity_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns,
                set_={
                    key: stmt.excluded[key]
                    for key in entity_data.keys()
                    if key not in conflict_columns and key != "id"
                },
            )

            await session.execute(stmt)
            await session.flush()

            # Retrieve the entity with relationships loaded
            file_path = entity_data.get("file_path")
            if not file_path:
                raise ValueError("file_path is required for upsert_entity_optimistic")

            query = (
                self.select()
                .where(Entity.file_path == file_path)
                .options(*self.get_load_options())
            )
            result = await session.execute(query)
            found = result.scalar_one_or_none()

            if not found:  # pragma: no cover
                raise RuntimeError(f"Failed to retrieve entity after optimistic upsert: {file_path}")

            return found

    async def update_entity_optimistic(
        self, file_path: str, updates: dict, conflict_columns: Optional[List[str]] = None
    ) -> Optional[Entity]:
        """Update an entity by file_path using SQLite's ON CONFLICT clause.

        This method is designed to replace direct update() calls in sync operations
        to eliminate race conditions.

        Args:
            file_path: The file_path of the entity to update
            updates: Dictionary of fields to update
            conflict_columns: Columns to use for conflict detection (defaults to ['file_path'])

        Returns:
            The updated entity or None if no entity exists with the given file_path
        """
        if conflict_columns is None:
            conflict_columns = ["file_path"]

        async with db.scoped_session(self.session_maker) as session:
            # First check if entity exists
            existing_entity = await session.execute(
                select(Entity).where(
                    Entity.file_path == file_path,
                    Entity.project_id == self.project_id
                )
            )
            entity = existing_entity.scalar_one_or_none()
            
            if not entity:
                # Entity doesn't exist, cannot update
                return None

            # Prepare the data for upsert (include the file_path and any other required fields)
            entity_data = {
                "file_path": file_path,
                "project_id": self.project_id,
                **updates
            }

            # For updates, we need to include the current values that shouldn't change
            # This ensures we don't lose data during the upsert
            for field in ["title", "entity_type", "content_type", "permalink", "checksum", "created_at", "updated_at"]:
                if field not in entity_data and hasattr(entity, field):
                    current_value = getattr(entity, field)
                    if current_value is not None:
                        entity_data[field] = current_value

            # Use the optimistic upsert method
            return await self.upsert_entity_optimistic(entity_data, conflict_columns)

    async def update_entity_by_id_optimistic(
        self, entity_id: int, updates: dict
    ) -> Optional[Entity]:
        """Update an entity by ID using current values + updates, then upsert optimistically.

        This method is useful when you have an entity ID and want to update specific fields
        while preserving all other current values.

        Args:
            entity_id: The ID of the entity to update
            updates: Dictionary of fields to update

        Returns:
            The updated entity or None if no entity exists with the given ID
        """
        async with db.scoped_session(self.session_maker) as session:
            # First get the current entity
            existing_entity = await session.execute(
                select(Entity).where(Entity.id == entity_id)
            )
            entity = existing_entity.scalar_one_or_none()
            
            if not entity:
                # Entity doesn't exist, cannot update
                return None

            # Prepare the data for upsert with current values + updates
            entity_data = {
                "file_path": entity.file_path,
                "project_id": entity.project_id,
                "title": entity.title,
                "entity_type": entity.entity_type,
                "content_type": entity.content_type,
                "permalink": entity.permalink,
                "checksum": entity.checksum,
                "created_at": entity.created_at,
                "updated_at": entity.updated_at,
                **updates  # Override with new values
            }

            # For moves, we need to handle the file_path conflict properly
            conflict_columns = ["file_path"]

            # Use the optimistic upsert method
            return await self.upsert_entity_optimistic(entity_data, conflict_columns)
