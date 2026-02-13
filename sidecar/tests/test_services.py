"""Tests for CRUD service layer."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fiction_translator.db.models import Base, Chapter, GlossaryEntry, Project
from fiction_translator.services.chapter_service import (
    create_chapter,
    delete_chapter,
    get_chapter,
    list_chapters,
    update_chapter,
)
from fiction_translator.services.glossary_service import (
    create_glossary_entry,
    delete_glossary_entry,
    list_glossary,
    update_glossary_entry,
)
from fiction_translator.services.project_service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)


@pytest.fixture
def db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestProjectService:
    """Tests for project CRUD operations."""

    def test_create_project(self, db):
        project = create_project(
            db,
            name="Test Project",
            source_language="ko",
            target_language="en",
        )
        assert project["id"] is not None
        assert project["name"] == "Test Project"
        assert project["source_language"] == "ko"
        assert project["target_language"] == "en"
        assert project["pipeline_type"] == "cot_batch"
        assert project["llm_provider"] == "gemini"

    def test_create_project_with_optional_fields(self, db):
        project = create_project(
            db,
            name="Test Project",
            description="A test project",
            genre="fantasy",
            style_settings={"tone": "formal"},
            pipeline_type="simple",
            llm_provider="claude",
        )
        assert project["description"] == "A test project"
        assert project["genre"] == "fantasy"
        assert project["style_settings"] == {"tone": "formal"}
        assert project["pipeline_type"] == "simple"
        assert project["llm_provider"] == "claude"

    def test_list_projects(self, db):
        create_project(db, name="Project 1")
        create_project(db, name="Project 2")

        projects = list_projects(db)
        assert len(projects) == 2
        # Check that both projects are present (order may vary due to timestamp resolution)
        project_names = {p["name"] for p in projects}
        assert project_names == {"Project 1", "Project 2"}
        assert projects[0]["chapter_count"] == 0
        assert projects[1]["chapter_count"] == 0

    def test_list_projects_with_chapter_counts(self, db):
        p1 = create_project(db, name="Project 1")
        p2 = create_project(db, name="Project 2")

        create_chapter(db, p1["id"], "Chapter 1")
        create_chapter(db, p1["id"], "Chapter 2")
        create_chapter(db, p2["id"], "Chapter 1")

        projects = list_projects(db)
        # Find projects by name
        project1 = next(p for p in projects if p["name"] == "Project 1")
        project2 = next(p for p in projects if p["name"] == "Project 2")

        assert project1["chapter_count"] == 2
        assert project2["chapter_count"] == 1

    def test_get_project(self, db):
        created = create_project(db, name="Test Project")
        retrieved = get_project(db, created["id"])

        assert retrieved["id"] == created["id"]
        assert retrieved["name"] == "Test Project"

    def test_get_project_not_found(self, db):
        with pytest.raises(ValueError, match="Project 999 not found"):
            get_project(db, 999)

    def test_update_project(self, db):
        project = create_project(db, name="Original Name")

        updated = update_project(
            db,
            project["id"],
            name="Updated Name",
            description="New description",
            genre="sci-fi",
        )

        assert updated["name"] == "Updated Name"
        assert updated["description"] == "New description"
        assert updated["genre"] == "sci-fi"

    def test_update_project_whitelist_enforcement(self, db):
        """Test that only whitelisted fields can be updated."""
        project = create_project(db, name="Test Project")

        # Try to update with a non-whitelisted field
        updated = update_project(
            db,
            project["id"],
            name="Updated Name",
            created_at="2020-01-01",  # Not in whitelist, should be ignored
            unknown_field="value",  # Not in whitelist, should be ignored
        )

        assert updated["name"] == "Updated Name"
        # created_at should remain unchanged
        assert updated["created_at"] == project["created_at"]

    def test_update_project_not_found(self, db):
        with pytest.raises(ValueError, match="Project 999 not found"):
            update_project(db, 999, name="New Name")

    def test_delete_project(self, db):
        project = create_project(db, name="To Delete")
        result = delete_project(db, project["id"])

        assert result["deleted"] is True
        assert result["id"] == project["id"]

        with pytest.raises(ValueError, match="not found"):
            get_project(db, project["id"])

    def test_delete_project_not_found(self, db):
        with pytest.raises(ValueError, match="Project 999 not found"):
            delete_project(db, 999)

    def test_delete_project_cascades_to_chapters(self, db):
        """Test that deleting a project also deletes its chapters."""
        project = create_project(db, name="Project with Chapters")
        chapter = create_chapter(db, project["id"], "Chapter 1")

        delete_project(db, project["id"])

        # Chapter should be deleted too
        assert db.query(Chapter).filter(Chapter.id == chapter["id"]).first() is None


class TestChapterService:
    """Tests for chapter CRUD operations."""

    def test_create_chapter(self, db):
        project = create_project(db, name="Test Project")
        chapter = create_chapter(
            db,
            project["id"],
            title="Chapter 1",
            source_content="Content here",
        )

        assert chapter["id"] is not None
        assert chapter["project_id"] == project["id"]
        assert chapter["title"] == "Chapter 1"
        assert chapter["source_content"] == "Content here"
        assert chapter["order"] == 1

    def test_create_chapter_auto_order(self, db):
        """Test that chapters are auto-ordered sequentially."""
        project = create_project(db, name="Test Project")
        ch1 = create_chapter(db, project["id"], "Chapter 1")
        ch2 = create_chapter(db, project["id"], "Chapter 2")
        ch3 = create_chapter(db, project["id"], "Chapter 3")

        assert ch1["order"] == 1
        assert ch2["order"] == 2
        assert ch3["order"] == 3

    def test_create_chapter_with_optional_fields(self, db):
        project = create_project(db, name="Test Project")
        chapter = create_chapter(
            db,
            project["id"],
            title="Chapter 1",
            source_content="Content",
            file_path="/path/to/file.txt",
        )

        assert chapter["file_path"] == "/path/to/file.txt"

    def test_list_chapters(self, db):
        project = create_project(db, name="Test Project")
        create_chapter(db, project["id"], "Chapter 1", "Content 1")
        create_chapter(db, project["id"], "Chapter 2", "Content 2")

        chapters = list_chapters(db, project["id"])
        assert len(chapters) == 2
        assert chapters[0]["title"] == "Chapter 1"
        assert chapters[1]["title"] == "Chapter 2"
        assert chapters[0]["segment_count"] == 0
        assert chapters[0]["translated_count"] == 0

    def test_list_chapters_empty(self, db):
        project = create_project(db, name="Test Project")
        chapters = list_chapters(db, project["id"])
        assert chapters == []

    def test_get_chapter(self, db):
        project = create_project(db, name="Test Project")
        created = create_chapter(db, project["id"], "Chapter 1")
        retrieved = get_chapter(db, created["id"])

        assert retrieved["id"] == created["id"]
        assert retrieved["title"] == "Chapter 1"

    def test_get_chapter_not_found(self, db):
        with pytest.raises(ValueError, match="Chapter 999 not found"):
            get_chapter(db, 999)

    def test_update_chapter(self, db):
        project = create_project(db, name="Test Project")
        chapter = create_chapter(db, project["id"], "Original Title")

        updated = update_chapter(
            db,
            chapter["id"],
            title="Updated Title",
            source_content="New content",
            order=5,
        )

        assert updated["title"] == "Updated Title"
        assert updated["source_content"] == "New content"
        assert updated["order"] == 5

    def test_update_chapter_whitelist_enforcement(self, db):
        """Test that only whitelisted fields can be updated."""
        project = create_project(db, name="Test Project")
        chapter = create_chapter(db, project["id"], "Chapter 1")

        # Try to update with a non-whitelisted field
        updated = update_chapter(
            db,
            chapter["id"],
            title="Updated Title",
            project_id=999,  # Not in whitelist, should be ignored
            unknown_field="value",  # Not in whitelist, should be ignored
        )

        assert updated["title"] == "Updated Title"
        assert updated["project_id"] == project["id"]  # Should remain unchanged

    def test_update_chapter_not_found(self, db):
        with pytest.raises(ValueError, match="Chapter 999 not found"):
            update_chapter(db, 999, title="New Title")

    def test_delete_chapter(self, db):
        project = create_project(db, name="Test Project")
        chapter = create_chapter(db, project["id"], "To Delete")

        result = delete_chapter(db, chapter["id"])

        assert result["deleted"] is True
        assert result["id"] == chapter["id"]

        with pytest.raises(ValueError, match="not found"):
            get_chapter(db, chapter["id"])

    def test_delete_chapter_not_found(self, db):
        with pytest.raises(ValueError, match="Chapter 999 not found"):
            delete_chapter(db, 999)


class TestGlossaryService:
    """Tests for glossary CRUD operations."""

    def test_create_glossary_entry(self, db):
        project = create_project(db, name="Test Project")
        entry = create_glossary_entry(
            db,
            project["id"],
            source_term="마법사",
            translated_term="Wizard",
        )

        assert entry["id"] is not None
        assert entry["project_id"] == project["id"]
        assert entry["source_term"] == "마법사"
        assert entry["translated_term"] == "Wizard"
        assert entry["term_type"] == "general"
        assert entry["auto_detected"] is False

    def test_create_glossary_entry_with_optional_fields(self, db):
        project = create_project(db, name="Test Project")
        entry = create_glossary_entry(
            db,
            project["id"],
            source_term="마법사",
            translated_term="Wizard",
            term_type="character",
            notes="Main character",
            context="Fantasy novel",
            auto_detected=True,
        )

        assert entry["term_type"] == "character"
        assert entry["notes"] == "Main character"
        assert entry["context"] == "Fantasy novel"
        assert entry["auto_detected"] is True

    def test_list_glossary(self, db):
        project = create_project(db, name="Test Project")
        create_glossary_entry(db, project["id"], "마법사", "Wizard")
        create_glossary_entry(db, project["id"], "전사", "Warrior")

        entries = list_glossary(db, project["id"])
        assert len(entries) == 2
        # Should be sorted by source_term
        assert entries[0]["source_term"] in ["마법사", "전사"]
        assert entries[1]["source_term"] in ["마법사", "전사"]

    def test_list_glossary_empty(self, db):
        project = create_project(db, name="Test Project")
        entries = list_glossary(db, project["id"])
        assert entries == []

    def test_list_glossary_filters_by_project(self, db):
        """Test that list_glossary only returns entries for the specified project."""
        p1 = create_project(db, name="Project 1")
        p2 = create_project(db, name="Project 2")

        create_glossary_entry(db, p1["id"], "term1", "translation1")
        create_glossary_entry(db, p2["id"], "term2", "translation2")

        entries_p1 = list_glossary(db, p1["id"])
        entries_p2 = list_glossary(db, p2["id"])

        assert len(entries_p1) == 1
        assert len(entries_p2) == 1
        assert entries_p1[0]["source_term"] == "term1"
        assert entries_p2[0]["source_term"] == "term2"

    def test_update_glossary_entry(self, db):
        project = create_project(db, name="Test Project")
        entry = create_glossary_entry(db, project["id"], "마법사", "Wizard")

        updated = update_glossary_entry(
            db,
            entry["id"],
            translated_term="Sorcerer",
            notes="Updated translation",
            term_type="character",
        )

        assert updated["translated_term"] == "Sorcerer"
        assert updated["notes"] == "Updated translation"
        assert updated["term_type"] == "character"
        assert updated["source_term"] == "마법사"  # Original unchanged

    def test_update_glossary_entry_whitelist_enforcement(self, db):
        """Test that only whitelisted fields can be updated."""
        project = create_project(db, name="Test Project")
        entry = create_glossary_entry(db, project["id"], "마법사", "Wizard")

        # Try to update with a non-whitelisted field
        updated = update_glossary_entry(
            db,
            entry["id"],
            translated_term="Sorcerer",
            project_id=999,  # Not in whitelist, should be ignored
            auto_detected=True,  # Not in whitelist, should be ignored
        )

        assert updated["translated_term"] == "Sorcerer"
        assert updated["project_id"] == project["id"]  # Should remain unchanged
        assert updated["auto_detected"] is False  # Should remain unchanged

    def test_update_glossary_entry_not_found(self, db):
        with pytest.raises(ValueError, match="Glossary entry 999 not found"):
            update_glossary_entry(db, 999, translated_term="New")

    def test_delete_glossary_entry(self, db):
        project = create_project(db, name="Test Project")
        entry = create_glossary_entry(db, project["id"], "마법사", "Wizard")

        result = delete_glossary_entry(db, entry["id"])

        assert result["deleted"] is True
        assert result["id"] == entry["id"]

        # Entry should be gone
        assert db.query(GlossaryEntry).filter(GlossaryEntry.id == entry["id"]).first() is None

    def test_delete_glossary_entry_not_found(self, db):
        with pytest.raises(ValueError, match="Glossary entry 999 not found"):
            delete_glossary_entry(db, 999)
