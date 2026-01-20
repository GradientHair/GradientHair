import os
import re
import uuid
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class Principle(BaseModel):
    id: str
    name: str
    filePath: str
    content: str


class PrincipleDetail(BaseModel):
    id: str
    name: str
    content: str


class PrincipleCreate(BaseModel):
    name: str
    content: str


class PrincipleUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None


class PrincipleCreateResponse(BaseModel):
    id: str
    name: str
    filePath: str


class PrinciplesService:
    def __init__(self, base_path: str | None = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Docker environment: /app/principles, local: project root/principles
            if os.path.exists("/app/principles"):
                self.base_path = Path("/app/principles")
            else:
                self.base_path = Path(__file__).parent.parent.parent / "principles"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _extract_name_from_content(self, content: str, fallback_id: str) -> str:
        """Extract principle name from markdown heading or return fallback."""
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        # Convert id to readable name as fallback
        return fallback_id.replace("-", " ").title()

    def _generate_id(self, name: str) -> str:
        """Generate a URL-safe ID from a name."""
        # Convert to lowercase and replace spaces with hyphens
        base_id = re.sub(r"[^a-z0-9\s-]", "", name.lower())
        base_id = re.sub(r"\s+", "-", base_id.strip())

        # If empty or too short, use uuid-based custom id
        if len(base_id) < 2:
            return f"custom-{uuid.uuid4().hex[:6]}"

        # Check if file already exists
        if (self.base_path / f"{base_id}.md").exists():
            # Append a unique suffix
            return f"{base_id}-{uuid.uuid4().hex[:4]}"

        return base_id

    def list_principles(self) -> list[Principle]:
        """List all principles from the principles directory."""
        principles = []

        if not self.base_path.exists():
            return principles

        for md_file in sorted(self.base_path.glob("*.md")):
            principle_id = md_file.stem
            try:
                content = md_file.read_text(encoding="utf-8")
                name = self._extract_name_from_content(content, principle_id)
                file_path = f"principles/{md_file.name}"

                principles.append(Principle(
                    id=principle_id,
                    name=name,
                    filePath=file_path,
                    content=content
                ))
            except Exception:
                # Skip files that can't be read
                continue

        return principles

    def get_principle(self, principle_id: str) -> Optional[PrincipleDetail]:
        """Get a single principle by ID."""
        file_path = self.base_path / f"{principle_id}.md"

        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            name = self._extract_name_from_content(content, principle_id)

            return PrincipleDetail(
                id=principle_id,
                name=name,
                content=content
            )
        except Exception:
            return None

    def update_principle(self, principle_id: str, update: PrincipleUpdate) -> Optional[PrincipleDetail]:
        """Update an existing principle."""
        file_path = self.base_path / f"{principle_id}.md"

        if not file_path.exists():
            return None

        try:
            # Read current content if we need to preserve it
            current_content = file_path.read_text(encoding="utf-8")

            # Determine new content
            new_content = update.content if update.content is not None else current_content

            # If name is provided, update the title in content
            if update.name is not None:
                # Check if content starts with a heading
                lines = new_content.split("\n")
                if lines and lines[0].strip().startswith("# "):
                    lines[0] = f"# {update.name}"
                    new_content = "\n".join(lines)
                else:
                    # Prepend the heading
                    new_content = f"# {update.name}\n\n{new_content}"

            # Write updated content
            file_path.write_text(new_content, encoding="utf-8")

            # Return updated principle
            name = self._extract_name_from_content(new_content, principle_id)
            return PrincipleDetail(
                id=principle_id,
                name=name,
                content=new_content
            )
        except Exception:
            return None

    def create_principle(self, create: PrincipleCreate) -> Optional[PrincipleCreateResponse]:
        """Create a new custom principle."""
        try:
            # Generate ID from name
            principle_id = self._generate_id(create.name)
            file_path = self.base_path / f"{principle_id}.md"

            # Ensure content has the name as heading
            content = create.content
            if not content.strip().startswith("# "):
                content = f"# {create.name}\n\n{content}"

            # Write the file
            file_path.write_text(content, encoding="utf-8")

            return PrincipleCreateResponse(
                id=principle_id,
                name=create.name,
                filePath=f"principles/{principle_id}.md"
            )
        except Exception:
            return None

    def delete_principle(self, principle_id: str) -> bool:
        """Delete a principle (optional - not in spec but useful)."""
        file_path = self.base_path / f"{principle_id}.md"

        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            return True
        except Exception:
            return False
