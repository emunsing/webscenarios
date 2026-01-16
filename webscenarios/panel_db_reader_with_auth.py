"""Minimal test of FastAPI + Panel integration."""
import panel as pn
from fastapi import FastAPI, HTTPException, status
from panel.io.fastapi import add_application
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import logging
import httpx
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# Initialize Panel
pn.extension()

# Database setup
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/webauth_demo"
)

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# Database Model
class Project(Base):
    __tablename__ = "projects_with_auth"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=False)
    product_name = Column(String(255), nullable=False)
    product_text = Column(Text, nullable=False, default="")
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Schemas
class ProjectCreate(BaseModel):
    name: str
    organization: str
    product_name: str
    product_text: str
    created_by: str


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    organization: Optional[str] = None
    product_name: Optional[str] = None
    product_text: Optional[str] = None
    created_by: Optional[str] = None


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    organization: str
    product_name: str
    product_text: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


async def get_async_session():
    """Dependency to get async database session."""
    async with async_session_maker() as session:
        yield session


# Create FastAPI app
app = FastAPI(title="Panel + FastAPI Test")


# REST API Endpoints
@app.get("/api/projects", response_model=List[ProjectRead])
async def list_projects():
    """List all projects."""
    async with async_session_maker() as db_session:
        from sqlalchemy import select
        result = await db_session.execute(select(Project))
        projects = result.scalars().all()
        return projects


@app.post("/api/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(project_data: ProjectCreate):
    """Create a new project."""
    async with async_session_maker() as db_session:
        project = Project(
            name=project_data.name,
            organization=project_data.organization,
            product_name=project_data.product_name,
            product_text=project_data.product_text,
            created_by=project_data.created_by
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        return project


@app.get("/api/projects/{project_id}", response_model=ProjectRead)
async def get_project(project_id: uuid.UUID):
    """Get a specific project."""
    async with async_session_maker() as db_session:
        project = await db_session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project


@app.put("/api/projects/{project_id}", response_model=ProjectRead)
async def update_project(project_id: uuid.UUID, project_data: ProjectUpdate):
    """Update a project."""
    async with async_session_maker() as db_session:
        project = await db_session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project_data.name is not None:
            project.name = project_data.name
        if project_data.organization is not None:
            project.organization = project_data.organization
        if project_data.product_name is not None:
            project.product_name = project_data.product_name
        if project_data.product_text is not None:
            project.product_text = project_data.product_text
        if project_data.created_by is not None:
            project.created_by = project_data.created_by

        await db_session.commit()
        await db_session.refresh(project)
        return project


@app.delete("/api/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: uuid.UUID):
    """Delete a project."""
    async with async_session_maker() as db_session:
        project = await db_session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        await db_session.delete(project)
        await db_session.commit()
        return None


# Panel App with async callbacks
@add_application("/panel", app=app, title="Project Manager")
def create_panel_app():
    """Create Panel app with async callbacks for database operations."""
    # Input fields
    project_name_input = pn.widgets.TextInput(name="Project Name", value="", width=400)
    organization_input = pn.widgets.TextInput(name="Organization", value="", width=400)
    product_name_input = pn.widgets.TextInput(name="Product Name", value="", width=400)
    config_text_input = pn.widgets.TextAreaInput(name="Product Text", value="", height=150, width=400)
    created_by_input = pn.widgets.TextInput(name="Creator username", value="", width=400)

    # Buttons
    save_button = pn.widgets.Button(name="Save", button_type="primary", width=100)
    load_button = pn.widgets.Button(name="Browse Projects", button_type="default", width=150)

    # Status display
    status_text = pn.pane.Markdown("", width=400)

    # Projects list display (using Markdown table)
    projects_list = pn.pane.Markdown("_No projects loaded yet. Click 'Browse Projects' to load._", width=600)

    # Async callback for saving
    async def save_project(event):
        name = project_name_input.value
        organization = organization_input.value
        config_name = product_name_input.value
        config = config_text_input.value
        creator = created_by_input.value

        if not name:
            status_text.object = "❌ Project name is required"
            return
        if not organization:
            status_text.object = "❌ Organization is required"
            return
        if not config_name:
            status_text.object = "❌ Product name is required"
            return
        if not creator:
            status_text.object = "❌ Creator username is required"
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/projects",
                    json={
                        "name": name,
                        "organization": organization,
                        "product_name": config_name,
                        "product_text": config,
                        "created_by": creator
                    }
                )
                if response.status_code == 201:
                    status_text.object = f"✅ Project '{name}' saved successfully!"
                    project_name_input.value = ""
                    organization_input.value = ""
                    product_name_input.value = ""
                    config_text_input.value = ""
                    created_by_input.value = ""
                else:
                    status_text.object = f"❌ Error: {response.text}"
        except Exception as e:
            status_text.object = f"❌ Error: {str(e)}"

    # Async callback for loading/browsing
    async def browse_projects(event):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/api/projects")
                if response.status_code == 200:
                    projects = response.json()
                    if projects:
                        # Create Markdown table
                        table_rows = [
                            "| ID | Name | Organization | Product Name | Created |",
                            "|-----|------|--------------|-------------------|---------|"
                        ]
                        for p in projects:
                            project_id = str(p["id"])[:8] + "..."
                            name = p["name"]
                            organization = p.get("organization", "N/A")
                            config_name = p.get("product_name", "N/A")
                            created = p["created_at"][:10] if p.get("created_at") else "N/A"
                            table_rows.append(f"| {project_id} | {name} | {organization} | {config_name} | {created} |")

                        table_md = "\n".join(table_rows)
                        projects_list.object = table_md
                        status_text.object = f"✅ Loaded {len(projects)} project(s)"
                    else:
                        projects_list.object = "_No projects found._"
                        status_text.object = "ℹ️ No projects found"
                else:
                    status_text.object = f"❌ Error: {response.text}"
        except Exception as e:
            status_text.object = f"❌ Error: {str(e)}"

    # Attach async callbacks
    save_button.on_click(save_project)
    load_button.on_click(browse_projects)

    # Layout
    return pn.Column(
        pn.pane.Markdown("# Project Manager", styles={"font-size": "24px", "font-weight": "bold"}),
        pn.Row(project_name_input, pn.Spacer(width=20), save_button),
        organization_input,
        product_name_input,
        config_text_input,
        created_by_input,
        pn.Row(load_button, pn.Spacer(width=20), status_text),
        pn.pane.Markdown("### Projects List"),
        projects_list,
        width=700,
        margin=20
    )


@app.on_event("startup")
async def on_startup():
    """Create database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "FastAPI + Panel Test",
        "panel_app": "/panel",
        "docs": "/docs",
        "api": "/api/projects"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
