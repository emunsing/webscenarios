"""Multi-tenant ReBAC system with FastAPI + Panel integration."""
import panel as pn
from fastapi import FastAPI, HTTPException, status
from panel.io.fastapi import add_application
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, UniqueConstraint
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
import enum

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


# Enums
class UserRole(str, enum.Enum):
    SUPERUSER = "superuser"
    MANAGER = "manager"
    EMPLOYEE = "employee"


# Database Models
class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="organization")
    projects = relationship("Project", back_populates="organization")


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    created_product_configs = relationship("ProductConfiguration", back_populates="creator", foreign_keys="ProductConfiguration.created_by")
    created_projects = relationship("Project", back_populates="creator", foreign_keys="Project.created_by")
    shared_projects = relationship("ProjectShare", back_populates="user", cascade="all, delete-orphan")
    shared_product_configs = relationship("ProductConfigurationShare", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent = relationship("Project", remote_side=[id], backref="children")
    organization = relationship("Organization", back_populates="projects")
    creator = relationship("User", back_populates="created_projects", foreign_keys=[created_by])
    product_configs = relationship("ProductConfiguration", back_populates="project", cascade="all, delete-orphan")
    shared_with = relationship("ProjectShare", back_populates="project", cascade="all, delete-orphan")


class ProductConfiguration(Base):
    __tablename__ = "product_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    product_name = Column(String(255), nullable=False)
    product_text = Column(Text, nullable=False, default="")
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_editing = Column(Boolean, default=False)
    edited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="product_configs")
    creator = relationship("User", back_populates="created_product_configs", foreign_keys=[created_by])
    editor = relationship("User", foreign_keys=[edited_by])
    shared_with = relationship("ProductConfigurationShare", back_populates="product_config", cascade="all, delete-orphan")


class ProjectShare(Base):
    __tablename__ = "project_shares"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="shared_with")
    user = relationship("User", back_populates="shared_projects")
    
    # Unique constraint to prevent duplicate shares
    __table_args__ = (
        UniqueConstraint('project_id', 'user_id', name='uq_project_user_share'),
    )


class ProductConfigurationShare(Base):
    __tablename__ = "product_configuration_shares"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_configuration_id = Column(UUID(as_uuid=True), ForeignKey("product_configurations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product_config = relationship("ProductConfiguration", back_populates="shared_with")
    user = relationship("User", back_populates="shared_product_configs")
    
    # Unique constraint to prevent duplicate shares
    __table_args__ = (
        UniqueConstraint('product_configuration_id', 'user_id', name='uq_product_config_user_share'),
    )


# Pydantic Schemas
class OrganizationRead(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserRead(BaseModel):
    id: uuid.UUID
    username: str
    email: Optional[str]
    role: UserRole
    organization_id: Optional[uuid.UUID]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    role: UserRole = UserRole.EMPLOYEE
    organization_id: Optional[uuid.UUID] = None


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: Optional[uuid.UUID]
    organization_id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str
    parent_id: Optional[uuid.UUID] = None
    organization_id: uuid.UUID
    created_by: str  # username


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None


class ProductConfigurationRead(BaseModel):
    id: uuid.UUID
    name: str
    product_name: str
    product_text: str
    project_id: uuid.UUID
    created_by: uuid.UUID
    is_editing: bool
    edited_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductConfigurationCreate(BaseModel):
    name: str
    product_name: str
    product_text: str
    project_id: uuid.UUID
    created_by: str  # username


class ProductConfigurationUpdate(BaseModel):
    name: Optional[str] = None
    product_name: Optional[str] = None
    product_text: Optional[str] = None
    project_id: Optional[uuid.UUID] = None


class ShareRequest(BaseModel):
    username: str


# Helper functions
async def get_or_create_user(username: str, db_session: AsyncSession) -> User:
    """Get user by username or create if doesn't exist."""
    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user:
        # Create default organization if needed
        org_result = await db_session.execute(select(Organization).where(Organization.name == "default"))
        org = org_result.scalar_one_or_none()
        if not org:
            org = Organization(name="default")
            db_session.add(org)
            await db_session.flush()
        
        # Create user
        user = User(username=username, role=UserRole.EMPLOYEE, organization_id=org.id)
        db_session.add(user)
        await db_session.flush()
    
    return user


async def has_access_to_product_config(user_id: uuid.UUID, product_config_id: uuid.UUID, db_session: AsyncSession) -> bool:
    """Check if user has access to a product configuration."""
    from sqlalchemy import select, or_
    
    # Get product configuration
    product_config = await db_session.get(ProductConfiguration, product_config_id)
    if not product_config:
        return False
    
    # Creator always has access
    if product_config.created_by == user_id:
        return True
    
    # Check direct share
    direct_share = await db_session.execute(
        select(ProductConfigurationShare).where(
            ProductConfigurationShare.product_configuration_id == product_config_id,
            ProductConfigurationShare.user_id == user_id
        )
    )
    if direct_share.scalar_one_or_none():
        return True
    
    # Check project share (recursive through parent projects)
    project_id = product_config.project_id
    while project_id:
        project_share = await db_session.execute(
            select(ProjectShare).where(
                ProjectShare.project_id == project_id,
                ProjectShare.user_id == user_id
            )
        )
        if project_share.scalar_one_or_none():
            return True
        
        # Check parent project
        project = await db_session.get(Project, project_id)
        if project and project.parent_id:
            project_id = project.parent_id
        else:
            break
    
    return False


async def grant_access_to_project_shares(project_id: uuid.UUID, product_config_id: uuid.UUID, db_session: AsyncSession):
    """Grant access to all users who have access to the project."""
    from sqlalchemy import select
    
    # Get all users with access to this project (recursive)
    project_shares = await db_session.execute(
        select(ProjectShare).where(ProjectShare.project_id == project_id)
    )
    shared_users = project_shares.scalars().all()
    
    # Also check parent projects
    project = await db_session.get(Project, project_id)
    parent_id = project.parent_id if project else None
    while parent_id:
        parent_shares = await db_session.execute(
            select(ProjectShare).where(ProjectShare.project_id == parent_id)
        )
        shared_users.extend(parent_shares.scalars().all())
        parent_project = await db_session.get(Project, parent_id)
        parent_id = parent_project.parent_id if parent_project else None
    
    # Create shares for each user
    for share in shared_users:
        existing = await db_session.execute(
            select(ProductConfigurationShare).where(
                ProductConfigurationShare.product_configuration_id == product_config_id,
                ProductConfigurationShare.user_id == share.user_id
            )
        )
        if not existing.scalar_one_or_none():
            new_share = ProductConfigurationShare(
                product_configuration_id=product_config_id,
                user_id=share.user_id
            )
            db_session.add(new_share)


async def revoke_access_from_project_shares(project_id: uuid.UUID, product_config_id: uuid.UUID, db_session: AsyncSession):
    """Revoke access from users who only had access through this project."""
    from sqlalchemy import select
    
    # Get product config
    product_config = await db_session.get(ProductConfiguration, product_config_id)
    if not product_config:
        return
    
    # Get all users with access to this project
    project_shares = await db_session.execute(
        select(ProjectShare).where(ProjectShare.project_id == project_id)
    )
    project_user_ids = {share.user_id for share in project_shares.scalars().all()}
    
    # Check each direct share
    direct_shares = await db_session.execute(
        select(ProductConfigurationShare).where(
            ProductConfigurationShare.product_configuration_id == product_config_id
        )
    )
    
    for share in direct_shares.scalars().all():
        # If user only had access through this project and not creator, remove share
        if share.user_id in project_user_ids and share.user_id != product_config.created_by:
            # Check if user has access through another project
            has_other_access = False
            
            # Check all other projects that contain this product config
            other_project_shares = await db_session.execute(
                select(ProjectShare).where(
                    ProjectShare.user_id == share.user_id,
                    ProjectShare.project_id != project_id
                )
            )
            for other_share in other_project_shares.scalars().all():
                # Check if this product config is in that project (recursively)
                other_project = await db_session.get(Project, other_share.project_id)
                if other_project and _is_product_in_project_tree(product_config.project_id, other_share.project_id, db_session):
                    has_other_access = True
                    break
            
            if not has_other_access:
                await db_session.delete(share)


async def _is_product_in_project_tree(product_project_id: uuid.UUID, target_project_id: uuid.UUID, db_session: AsyncSession) -> bool:
    """Check if a product's project is within a project tree."""
    current_id = product_project_id
    while current_id:
        if current_id == target_project_id:
            return True
        project = await db_session.get(Project, current_id)
        if project and project.parent_id:
            current_id = project.parent_id
        else:
            break
    return False


# Create FastAPI app
app = FastAPI(title="Multi-tenant ReBAC System")


# REST API Endpoints
@app.get("/api/users", response_model=List[UserRead])
async def list_users():
    """List all users."""
    async with async_session_maker() as db_session:
        from sqlalchemy import select
        result = await db_session.execute(select(User))
        users = result.scalars().all()
        return users


@app.get("/api/users/{username}", response_model=UserRead)
async def get_user_by_username(username: str):
    """Get user by username."""
    async with async_session_maker() as db_session:
        from sqlalchemy import select
        result = await db_session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user


@app.post("/api/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, current_user: str = "admin"):
    """Create a new user."""
    async with async_session_maker() as db_session:
        from sqlalchemy import select
        
        # Check if user already exists
        existing = await db_session.execute(select(User).where(User.username == user_data.username))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Handle organization - use provided or default
        org_id = user_data.organization_id
        if not org_id:
            org_result = await db_session.execute(select(Organization).where(Organization.name == "default"))
            org = org_result.scalar_one_or_none()
            if not org:
                org = Organization(name="default")
                db_session.add(org)
                await db_session.flush()
            org_id = org.id
        
        # Create user
        user = User(
            username=user_data.username,
            email=user_data.email,
            role=user_data.role,
            organization_id=org_id,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user


@app.get("/api/projects", response_model=List[ProjectRead])
async def list_projects(current_user: str = "admin"):
    """List all projects accessible to the current user."""
    async with async_session_maker() as db_session:
        user = await get_or_create_user(current_user, db_session)
        from sqlalchemy import select, or_
        
        # Get projects user created or has access to
        if user.role == UserRole.SUPERUSER:
            result = await db_session.execute(select(Project))
        else:
            # Projects user created or has share access to
            result = await db_session.execute(
                select(Project).where(
                    or_(
                        Project.created_by == user.id,
                        Project.id.in_(
                            select(ProjectShare.project_id).where(ProjectShare.user_id == user.id)
                        )
                    )
                )
            )
        projects = result.scalars().all()
        return projects


@app.get("/api/organizations/default")
async def get_or_create_default_org():
    """Get or create default organization."""
    async with async_session_maker() as db_session:
        from sqlalchemy import select
        org_result = await db_session.execute(select(Organization).where(Organization.name == "default"))
        org = org_result.scalar_one_or_none()
        if not org:
            org = Organization(name="default")
            db_session.add(org)
            await db_session.flush()
            await db_session.commit()
            await db_session.refresh(org)
        return {"id": str(org.id), "name": org.name}


@app.post("/api/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(project_data: ProjectCreate, current_user: str = "admin"):
    """Create a new project."""
    async with async_session_maker() as db_session:
        user = await get_or_create_user(project_data.created_by, db_session)
        
        # Use provided organization_id or get user's organization or default
        if project_data.organization_id:
            org_id = project_data.organization_id
        elif user.organization_id:
            org_id = user.organization_id
        else:
            # Get default organization
            from sqlalchemy import select
            org_result = await db_session.execute(select(Organization).where(Organization.name == "default"))
            org = org_result.scalar_one_or_none()
            if not org:
                org = Organization(name="default")
                db_session.add(org)
                await db_session.flush()
            org_id = org.id
            # Update user's organization
            user.organization_id = org_id
        
        project = Project(
            name=project_data.name,
            parent_id=project_data.parent_id,
            organization_id=org_id,
            created_by=user.id
        )
        db_session.add(project)
        await db_session.flush()
        
        # Auto-share with creator
        share = ProjectShare(project_id=project.id, user_id=user.id)
        db_session.add(share)
        
        await db_session.commit()
        await db_session.refresh(project)
        return project


@app.post("/api/projects/{project_id}/share", status_code=status.HTTP_200_OK)
async def share_project(project_id: uuid.UUID, share_request: ShareRequest, current_user: str = "admin"):
    """Share a project with a user."""
    async with async_session_maker() as db_session:
        project = await db_session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        target_user = await get_or_create_user(share_request.username, db_session)
        
        # Check if share already exists
        from sqlalchemy import select
        existing = await db_session.execute(
            select(ProjectShare).where(
                ProjectShare.project_id == project_id,
                ProjectShare.user_id == target_user.id
            )
        )
        if existing.scalar_one_or_none():
            return {"message": "Project already shared with this user"}
        
        # Create share
        share = ProjectShare(project_id=project_id, user_id=target_user.id)
        db_session.add(share)
        
        # Grant access to all product configs in this project
        for product_config in project.product_configs:
            await grant_access_to_project_shares(project_id, product_config.id, db_session)
        
        await db_session.commit()
        return {"message": f"Project shared with {share_request.username}"}


@app.delete("/api/projects/{project_id}/share/{username}", status_code=status.HTTP_200_OK)
async def unshare_project(project_id: uuid.UUID, username: str, current_user: str = "admin"):
    """Remove user from project share."""
    async with async_session_maker() as db_session:
        from sqlalchemy import select
        
        user_result = await db_session.execute(select(User).where(User.username == username))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        share_result = await db_session.execute(
            select(ProjectShare).where(
                ProjectShare.project_id == project_id,
                ProjectShare.user_id == user.id
            )
        )
        share = share_result.scalar_one_or_none()
        if not share:
            raise HTTPException(status_code=404, detail="Share not found")
        
        # Revoke access from product configs
        project = await db_session.get(Project, project_id)
        if project:
            for product_config in project.product_configs:
                await revoke_access_from_project_shares(project_id, product_config.id, db_session)
        
        await db_session.delete(share)
        await db_session.commit()
        return {"message": f"Project unshared with {username}"}


@app.put("/api/projects/{project_id}/parent", response_model=ProjectRead)
async def update_project_parent(project_id: uuid.UUID, parent_id: Optional[uuid.UUID], current_user: str = "admin"):
    """Update project parent."""
    async with async_session_maker() as db_session:
        project = await db_session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if parent_id is not None:
            parent = await db_session.get(Project, parent_id)
            if not parent:
                raise HTTPException(status_code=404, detail="Parent project not found")
        
        project.parent_id = parent_id
        await db_session.commit()
        await db_session.refresh(project)
        return project


@app.get("/api/product-configurations", response_model=List[ProductConfigurationRead])
async def list_product_configurations(current_user: str = "admin"):
    """List product configurations accessible to current user."""
    async with async_session_maker() as db_session:
        user = await get_or_create_user(current_user, db_session)
        from sqlalchemy import select
        
        if user.role == UserRole.SUPERUSER:
            result = await db_session.execute(select(ProductConfiguration))
        else:
            # Get accessible product configs
            accessible_ids = []
            all_configs = await db_session.execute(select(ProductConfiguration))
            for config in all_configs.scalars().all():
                if await has_access_to_product_config(user.id, config.id, db_session):
                    accessible_ids.append(config.id)
            
            if accessible_ids:
                result = await db_session.execute(
                    select(ProductConfiguration).where(ProductConfiguration.id.in_(accessible_ids))
                )
            else:
                return []
        
        configs = result.scalars().all()
        return configs


@app.post("/api/product-configurations", response_model=ProductConfigurationRead, status_code=status.HTTP_201_CREATED)
async def create_product_configuration(product_data: ProductConfigurationCreate, current_user: str = "admin"):
    """Create a new product configuration."""
    async with async_session_maker() as db_session:
        user = await get_or_create_user(product_data.created_by, db_session)
        
        product_config = ProductConfiguration(
            name=product_data.name,
            product_name=product_data.product_name,
            product_text=product_data.product_text,
            project_id=product_data.project_id,
            created_by=user.id
        )
        db_session.add(product_config)
        await db_session.flush()
        
        # Auto-share with creator
        creator_share = ProductConfigurationShare(
            product_configuration_id=product_config.id,
            user_id=user.id
        )
        db_session.add(creator_share)
        
        # Grant access through project shares
        await grant_access_to_project_shares(product_data.project_id, product_config.id, db_session)
        
        await db_session.commit()
        await db_session.refresh(product_config)
        return product_config


@app.put("/api/product-configurations/{config_id}", response_model=ProductConfigurationRead)
async def update_product_configuration(
    config_id: uuid.UUID,
    product_data: ProductConfigurationUpdate,
    current_user: str = "admin"
):
    """Update a product configuration."""
    async with async_session_maker() as db_session:
        user = await get_or_create_user(current_user, db_session)
        product_config = await db_session.get(ProductConfiguration, config_id)
        
        if not product_config:
            raise HTTPException(status_code=404, detail="Product configuration not found")
        
        # Check access
        if not await has_access_to_product_config(user.id, config_id, db_session):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if being edited by someone else
        if product_config.is_editing and product_config.edited_by != user.id:
            raise HTTPException(status_code=409, detail="Product configuration is being edited by another user")
        
        # Set editing status
        if not product_config.is_editing:
            product_config.is_editing = True
            product_config.edited_by = user.id
        
        # Update fields
        if product_data.name is not None:
            product_config.name = product_data.name
        if product_data.product_name is not None:
            product_config.product_name = product_data.product_name
        if product_data.product_text is not None:
            product_config.product_text = product_data.product_text
        
        # Handle project change
        old_project_id = product_config.project_id
        if product_data.project_id is not None and product_data.project_id != old_project_id:
            product_config.project_id = product_data.project_id
            
            # Revoke access from old project shares
            await revoke_access_from_project_shares(old_project_id, config_id, db_session)
            
            # Grant access through new project shares
            await grant_access_to_project_shares(product_data.project_id, config_id, db_session)
        
        await db_session.commit()
        await db_session.refresh(product_config)
        return product_config


@app.post("/api/product-configurations/{config_id}/release-edit", status_code=status.HTTP_200_OK)
async def release_edit_lock(config_id: uuid.UUID, current_user: str = "admin"):
    """Release edit lock on a product configuration."""
    async with async_session_maker() as db_session:
        user = await get_or_create_user(current_user, db_session)
        product_config = await db_session.get(ProductConfiguration, config_id)
        
        if not product_config:
            raise HTTPException(status_code=404, detail="Product configuration not found")
        
        if product_config.edited_by == user.id:
            product_config.is_editing = False
            product_config.edited_by = None
            await db_session.commit()
        
        return {"message": "Edit lock released"}


@app.post("/api/product-configurations/{config_id}/share", status_code=status.HTTP_200_OK)
async def share_product_configuration(
    config_id: uuid.UUID,
    share_request: ShareRequest,
    current_user: str = "admin"
):
    """Share a product configuration with a user."""
    async with async_session_maker() as db_session:
        user = await get_or_create_user(current_user, db_session)
        
        if not await has_access_to_product_config(user.id, config_id, db_session):
            raise HTTPException(status_code=403, detail="Access denied")
        
        target_user = await get_or_create_user(share_request.username, db_session)
        
        from sqlalchemy import select
        existing = await db_session.execute(
            select(ProductConfigurationShare).where(
                ProductConfigurationShare.product_configuration_id == config_id,
                ProductConfigurationShare.user_id == target_user.id
            )
        )
        if existing.scalar_one_or_none():
            return {"message": "Product configuration already shared with this user"}
        
        share = ProductConfigurationShare(
            product_configuration_id=config_id,
            user_id=target_user.id
        )
        db_session.add(share)
        await db_session.commit()
        return {"message": f"Product configuration shared with {share_request.username}"}


@app.delete("/api/product-configurations/{config_id}/share/{username}", status_code=status.HTTP_200_OK)
async def unshare_product_configuration(
    config_id: uuid.UUID,
    username: str,
    current_user: str = "admin"
):
    """Remove user from product configuration share."""
    async with async_session_maker() as db_session:
        user = await get_or_create_user(current_user, db_session)
        
        if not await has_access_to_product_config(user.id, config_id, db_session):
            raise HTTPException(status_code=403, detail="Access denied")
        
        from sqlalchemy import select
        
        user_result = await db_session.execute(select(User).where(User.username == username))
        target_user = user_result.scalar_one_or_none()
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Don't allow removing creator's access
        product_config = await db_session.get(ProductConfiguration, config_id)
        if product_config and product_config.created_by == target_user.id:
            raise HTTPException(status_code=400, detail="Cannot remove creator's access")
        
        share_result = await db_session.execute(
            select(ProductConfigurationShare).where(
                ProductConfigurationShare.product_configuration_id == config_id,
                ProductConfigurationShare.user_id == target_user.id
            )
        )
        share = share_result.scalar_one_or_none()
        if not share:
            raise HTTPException(status_code=404, detail="Share not found")
        
        await db_session.delete(share)
        await db_session.commit()
        return {"message": f"Product configuration unshared with {username}"}


@app.delete("/api/product-configurations/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_configuration(config_id: uuid.UUID, current_user: str = "admin"):
    """Delete a product configuration."""
    async with async_session_maker() as db_session:
        user = await get_or_create_user(current_user, db_session)
        product_config = await db_session.get(ProductConfiguration, config_id)
        
        if not product_config:
            raise HTTPException(status_code=404, detail="Product configuration not found")
        
        # Only creator or superuser can delete
        if product_config.created_by != user.id and user.role != UserRole.SUPERUSER:
            raise HTTPException(status_code=403, detail="Access denied")
        
        await db_session.delete(product_config)
        await db_session.commit()
        return None


# Panel App with async callbacks
@add_application("/panel", app=app, title="Multi-tenant ReBAC Manager")
def create_panel_app():
    """Create Panel app with ReBAC controls and product CRUD."""
    
    # Current user selection (left column)
    current_user_select = pn.widgets.Select(
        name="Logged in as",
        options=["admin"],
        value="admin",
        width=300
    )
    
    # User creation controls
    new_username_input = pn.widgets.TextInput(name="New Username", value="", width=300)
    create_user_button = pn.widgets.Button(name="Create User", button_type="primary", width=150)
    user_status = pn.pane.Markdown("", width=300)
    
    # Load users on init
    async def load_users():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/api/users")
                if response.status_code == 200:
                    users = response.json()
                    usernames = [u["username"] for u in users]
                    if usernames:
                        current_user_select.options = usernames
                        if current_user_select.value not in usernames:
                            current_user_select.value = usernames[0]
        except Exception as e:
            logger.error(f"Error loading users: {e}")
    
    # User creation handler
    async def create_user_handler(event):
        username = new_username_input.value.strip()
        current_user = get_current_user()
        
        if not username:
            user_status.object = "❌ Username is required"
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:8000/api/users?current_user={current_user}",
                    json={
                        "username": username,
                        "email": None,
                        "role": "employee",
                        "organization_id": None
                    }
                )
                if response.status_code == 201:
                    user_status.object = f"✅ User '{username}' created successfully!"
                    new_username_input.value = ""
                    # Refresh user list
                    await load_users()
                elif response.status_code == 400:
                    user_status.object = f"❌ User '{username}' already exists"
                else:
                    user_status.object = f"❌ Error: {response.text}"
        except Exception as e:
            user_status.object = f"❌ Error: {str(e)}"
    
    # Project management (left column)
    project_name_input = pn.widgets.TextInput(name="Project Name", value="", width=300)
    create_project_button = pn.widgets.Button(name="Create Project", button_type="primary", width=150)
    project_status = pn.pane.Markdown("", width=300)
    
    # Sharing controls (left column)
    share_username_input = pn.widgets.TextInput(name="Username to share with", value="", width=300)
    share_project_select = pn.widgets.Select(name="Project to share", options=[], value=None, width=300)
    share_project_button = pn.widgets.Button(name="Share Project", button_type="default", width=150)
    
    share_product_select = pn.widgets.Select(name="Product Config to share", options=[], value=None, width=300)
    share_product_button = pn.widgets.Button(name="Share Product", button_type="default", width=150)
    
    unshare_project_select = pn.widgets.Select(name="Project to unshare", options=[], value=None, width=300)
    unshare_username_select = pn.widgets.Select(name="User to remove", options=[], value=None, width=300)
    unshare_project_button = pn.widgets.Button(name="Remove User from Project", button_type="default", width=200)
    
    unshare_product_select = pn.widgets.Select(name="Product Config to unshare", options=[], value=None, width=300)
    unshare_product_username_select = pn.widgets.Select(name="User to remove", options=[], value=None, width=300)
    unshare_product_button = pn.widgets.Button(name="Remove User from Product", button_type="default", width=200)
    
    # Parent change controls (left column)
    change_parent_project_select = pn.widgets.Select(name="Project to move", options=[], value=None, width=300)
    new_parent_select = pn.widgets.Select(name="New parent project", options=["None"], value="None", width=300)
    change_parent_button = pn.widgets.Button(name="Change Parent", button_type="default", width=150)
    
    change_product_parent_select = pn.widgets.Select(name="Product to move", options=[], value=None, width=300)
    new_product_parent_select = pn.widgets.Select(name="New parent project", options=[], value=None, width=300)
    change_product_parent_button = pn.widgets.Button(name="Change Product Parent", button_type="default", width=200)
    
    # Product CRUD (right column) - existing interface
    product_name_input = pn.widgets.TextInput(name="Product Name", value="", width=400)
    product_config_name_input = pn.widgets.TextInput(name="Product Config Name", value="", width=400)
    product_config_text_input = pn.widgets.TextAreaInput(name="Product Text", value="", height=150, width=400)
    product_project_select = pn.widgets.Select(name="Project", options=[], value=None, width=400)
    
    save_button = pn.widgets.Button(name="Save", button_type="primary", width=100)
    load_button = pn.widgets.Button(name="Browse Products", button_type="default", width=150)
    
    status_text = pn.pane.Markdown("", width=400)
    products_list = pn.pane.Markdown("_No products loaded yet. Click 'Browse Products' to load._", width=600)
    
    # Helper function to get current user
    def get_current_user():
        return current_user_select.value if current_user_select.value else "admin"
    
    # Store full data for lookups
    projects_data = {}
    products_data = {}
    
    # Load functions
    async def refresh_project_lists():
        """Refresh project and product dropdowns."""
        current_user = get_current_user()
        try:
            async with httpx.AsyncClient() as client:
                # Load projects
                response = await client.get(
                    f"http://localhost:8000/api/projects?current_user={current_user}"
                )
                if response.status_code == 200:
                    projects = response.json()
                    # Store full project data indexed by ID
                    projects_data.clear()
                    for p in projects:
                        projects_data[str(p['id'])] = p
                    
                    project_options = [f"{p['name']} ({str(p['id'])[:8]})" for p in projects]
                    share_project_select.options = project_options if project_options else []
                    change_parent_project_select.options = project_options if project_options else []
                    new_parent_select.options = ["None"] + project_options
                    new_product_parent_select.options = project_options if project_options else []
                    product_project_select.options = project_options if project_options else []
                
                # Load products
                response = await client.get(
                    f"http://localhost:8000/api/product-configurations?current_user={current_user}"
                )
                if response.status_code == 200:
                    products = response.json()
                    # Store full product data indexed by ID
                    products_data.clear()
                    for p in products:
                        products_data[str(p['id'])] = p
                    
                    product_options = [f"{p['name']} ({str(p['id'])[:8]})" for p in products]
                    share_product_select.options = product_options if product_options else []
                    unshare_product_select.options = product_options if product_options else []
                    change_product_parent_select.options = product_options if product_options else []
        except Exception as e:
            logger.error(f"Error refreshing lists: {e}")
    
    # Helper to extract full UUID from option string
    def extract_uuid_from_option(option_str, data_dict):
        """Extract full UUID from option string like 'Name (12345678)'."""
        if not option_str or option_str == "None":
            return None
        try:
            # Extract the 8-char prefix from option string
            prefix = option_str.split("(")[1].split(")")[0]
            # Find matching UUID in data dict
            for full_id in data_dict.keys():
                if str(full_id).startswith(prefix):
                    return full_id
            # If not found, try to parse as UUID directly
            return option_str
        except Exception:
            return None
    
    # Project creation
    async def create_project_handler(event):
        name = project_name_input.value
        current_user = get_current_user()
        
        if not name:
            project_status.object = "❌ Project name is required"
            return
        
        try:
            async with httpx.AsyncClient() as client:
                # Get default organization
                org_response = await client.get("http://localhost:8000/api/organizations/default")
                if org_response.status_code != 200:
                    project_status.object = "❌ Error: Could not get organization"
                    return
                
                org_id = org_response.json()["id"]
                
                response = await client.post(
                    f"http://localhost:8000/api/projects?current_user={current_user}",
                    json={
                        "name": name,
                        "parent_id": None,
                        "organization_id": org_id,
                        "created_by": current_user
                    }
                )
                
                if response.status_code == 201:
                    project_status.object = f"✅ Project '{name}' created successfully!"
                    project_name_input.value = ""
                    await refresh_project_lists()
                else:
                    project_status.object = f"❌ Error: {response.text}"
        except Exception as e:
            project_status.object = f"❌ Error: {str(e)}"
    
    # Sharing handlers
    async def share_project_handler(event):
        current_user = get_current_user()
        username = share_username_input.value
        project_option = share_project_select.value
        
        if not username or not project_option:
            project_status.object = "❌ Please select a project and enter a username"
            return
        
        project_id = extract_uuid_from_option(project_option, projects_data)
        if not project_id:
            project_status.object = "❌ Invalid project selection"
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:8000/api/projects/{project_id}/share?current_user={current_user}",
                    json={"username": username}
                )
                if response.status_code == 200:
                    project_status.object = f"✅ Project shared with {username}!"
                    share_username_input.value = ""
                    await refresh_project_lists()
                else:
                    project_status.object = f"❌ Error: {response.text}"
        except Exception as e:
            project_status.object = f"❌ Error: {str(e)}"
    
    async def share_product_handler(event):
        current_user = get_current_user()
        username = share_username_input.value
        product_option = share_product_select.value
        
        if not username or not product_option:
            status_text.object = "❌ Please select a product and enter a username"
            return
        
        product_id = extract_uuid_from_option(product_option, products_data)
        if not product_id:
            status_text.object = "❌ Invalid product selection"
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:8000/api/product-configurations/{product_id}/share?current_user={current_user}",
                    json={"username": username}
                )
                if response.status_code == 200:
                    status_text.object = f"✅ Product shared with {username}!"
                    share_username_input.value = ""
                    await refresh_project_lists()
                else:
                    status_text.object = f"❌ Error: {response.text}"
        except Exception as e:
            status_text.object = f"❌ Error: {str(e)}"
    
    async def unshare_project_handler(event):
        current_user = get_current_user()
        project_option = unshare_project_select.value
        username = unshare_username_select.value
        
        if not project_option or not username:
            project_status.object = "❌ Please select a project and user"
            return
        
        project_id = extract_uuid_from_option(project_option, projects_data)
        if not project_id:
            project_status.object = "❌ Invalid project selection"
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"http://localhost:8000/api/projects/{project_id}/share/{username}?current_user={current_user}"
                )
                if response.status_code == 200:
                    project_status.object = f"✅ User {username} removed from project!"
                    await refresh_project_lists()
                else:
                    project_status.object = f"❌ Error: {response.text}"
        except Exception as e:
            project_status.object = f"❌ Error: {str(e)}"
    
    async def unshare_product_handler(event):
        current_user = get_current_user()
        product_option = unshare_product_select.value
        username = unshare_product_username_select.value
        
        if not product_option or not username:
            status_text.object = "❌ Please select a product and user"
            return
        
        product_id = extract_uuid_from_option(product_option, products_data)
        if not product_id:
            status_text.object = "❌ Invalid product selection"
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"http://localhost:8000/api/product-configurations/{product_id}/share/{username}?current_user={current_user}"
                )
                if response.status_code == 200:
                    status_text.object = f"✅ User {username} removed from product!"
                    await refresh_project_lists()
                else:
                    status_text.object = f"❌ Error: {response.text}"
        except Exception as e:
            status_text.object = f"❌ Error: {str(e)}"
    
    # Parent change handlers
    async def change_project_parent_handler(event):
        current_user = get_current_user()
        project_option = change_parent_project_select.value
        parent_option = new_parent_select.value
        
        if not project_option:
            project_status.object = "❌ Please select a project"
            return
        
        project_id = extract_uuid_from_option(project_option, projects_data)
        if not project_id:
            project_status.object = "❌ Invalid project selection"
            return
        
        parent_id = extract_uuid_from_option(parent_option, projects_data)
        
        try:
            async with httpx.AsyncClient() as client:
                params = {"current_user": current_user}
                if parent_id is not None:
                    params["parent_id"] = parent_id
                response = await client.put(
                    f"http://localhost:8000/api/projects/{project_id}/parent",
                    params=params
                )
                if response.status_code == 200:
                    project_status.object = f"✅ Project parent updated!"
                    await refresh_project_lists()
                else:
                    project_status.object = f"❌ Error: {response.text}"
        except Exception as e:
            project_status.object = f"❌ Error: {str(e)}"
    
    async def change_product_parent_handler(event):
        current_user = get_current_user()
        product_option = change_product_parent_select.value
        parent_option = new_product_parent_select.value
        
        if not product_option or not parent_option:
            status_text.object = "❌ Please select a product and parent project"
            return
        
        product_id = extract_uuid_from_option(product_option, products_data)
        if not product_id:
            status_text.object = "❌ Invalid product selection"
            return
        
        parent_id = extract_uuid_from_option(parent_option, projects_data)
        if not parent_id:
            status_text.object = "❌ Invalid parent project selection"
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"http://localhost:8000/api/product-configurations/{product_id}?current_user={current_user}",
                    json={"project_id": parent_id}
                )
                if response.status_code == 200:
                    status_text.object = f"✅ Product parent project updated!"
                    await refresh_project_lists()
                else:
                    status_text.object = f"❌ Error: {response.text}"
        except Exception as e:
            status_text.object = f"❌ Error: {str(e)}"
    
    # Product CRUD handlers (existing)
    async def save_product(event):
        name = product_config_name_input.value
        product_name = product_name_input.value
        product_text = product_config_text_input.value
        project_option = product_project_select.value
        current_user = get_current_user()
        
        if not name:
            status_text.object = "❌ Product config name is required"
            return
        if not product_name:
            status_text.object = "❌ Product name is required"
            return
        if not project_option:
            status_text.object = "❌ Project is required"
            return
        
        project_id = extract_uuid_from_option(project_option, projects_data)
        if not project_id:
            status_text.object = "❌ Invalid project selection"
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:8000/api/product-configurations?current_user={current_user}",
                    json={
                        "name": name,
                        "product_name": product_name,
                        "product_text": product_text,
                        "project_id": project_id,
                        "created_by": current_user
                    }
                )
                if response.status_code == 201:
                    status_text.object = f"✅ Product '{name}' saved successfully!"
                    product_config_name_input.value = ""
                    product_name_input.value = ""
                    product_config_text_input.value = ""
                    await refresh_project_lists()
                else:
                    status_text.object = f"❌ Error: {response.text}"
        except Exception as e:
            status_text.object = f"❌ Error: {str(e)}"
    
    async def browse_products(event):
        current_user = get_current_user()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:8000/api/product-configurations?current_user={current_user}"
                )
                if response.status_code == 200:
                    products = response.json()
                    if products:
                        table_rows = [
                            "| ID | Name | Product Name | Project | Created |",
                            "|-----|------|--------------|---------|---------|"
                        ]
                        for p in products:
                            product_id = str(p["id"])[:8] + "..."
                            name = p["name"]
                            product_name = p.get("product_name", "N/A")
                            project_id = str(p.get("project_id", ""))[:8] + "..." if p.get("project_id") else "N/A"
                            created = p["created_at"][:10] if p.get("created_at") else "N/A"
                            table_rows.append(f"| {product_id} | {name} | {product_name} | {project_id} | {created} |")
                        
                        table_md = "\n".join(table_rows)
                        products_list.object = table_md
                        status_text.object = f"✅ Loaded {len(products)} product(s)"
                    else:
                        products_list.object = "_No products found._"
                        status_text.object = "ℹ️ No products found"
                else:
                    status_text.object = f"❌ Error: {response.text}"
        except Exception as e:
            status_text.object = f"❌ Error: {str(e)}"
    
    # Attach callbacks
    create_user_button.on_click(create_user_handler)
    create_project_button.on_click(create_project_handler)
    share_project_button.on_click(share_project_handler)
    share_product_button.on_click(share_product_handler)
    unshare_project_button.on_click(unshare_project_handler)
    unshare_product_button.on_click(unshare_product_handler)
    change_parent_button.on_click(change_project_parent_handler)
    change_product_parent_button.on_click(change_product_parent_handler)
    save_button.on_click(save_product)
    load_button.on_click(browse_products)
    
    # Initialize data function - runs on user change
    async def initialize_data():
        """Load users and refresh project lists."""
        await load_users()
        await refresh_project_lists()
    
    # Watch for user changes to refresh lists
    # Panel's parameter watch callbacks can schedule async work via on_click pattern
    # We'll use a button-based approach for async initialization
    async def on_user_change_async(event=None):
        """Async handler for user changes - loads users and refreshes lists."""
        await initialize_data()
    
    # Create a hidden button that triggers initial load
    # This allows us to use Panel's async callback support
    init_load_trigger = pn.widgets.Button(name="Refresh", button_type="default", width=0, height=0, visible=False)
    init_load_trigger.on_click(on_user_change_async)
    
    # Watch for user changes - trigger async load when user changes
    def on_user_change(event):
        # Trigger via the button's async handler
        init_load_trigger.clicks += 1
    
    current_user_select.param.watch(on_user_change, 'value')
    
    # Trigger initial load once by simulating a click on the hidden button
    # This happens after the layout is created but uses Panel's async support
    def trigger_initial_load():
        """Trigger initial data load."""
        try:
            init_load_trigger.clicks = 1
        except Exception:
            # If trigger fails, data will load when user changes selection
            pass
    
    # Schedule initial load - will run after widget creation
    # We use a small delay to ensure widgets are fully initialized
    try:
        import threading
        timer = threading.Timer(0.1, trigger_initial_load)
        timer.start()
    except Exception as e:
        logger.warning(f"Could not schedule initial load: {e}. Data will load when user selection changes.")
    
    # Left column - Auth and sharing controls
    left_column = pn.Column(
        pn.pane.Markdown("## User & Access Control", styles={"font-size": "20px", "font-weight": "bold"}),
        current_user_select,
        pn.pane.Markdown("### Create User"),
        new_username_input,
        create_user_button,
        user_status,
        pn.pane.Markdown("### Project Management"),
        project_name_input,
        create_project_button,
        project_status,
        pn.pane.Markdown("### Share Project"),
        share_project_select,
        share_username_input,
        share_project_button,
        pn.pane.Markdown("### Share Product Configuration"),
        share_product_select,
        share_product_button,
        pn.pane.Markdown("### Unshare Project"),
        unshare_project_select,
        unshare_username_select,
        unshare_project_button,
        pn.pane.Markdown("### Unshare Product"),
        unshare_product_select,
        unshare_product_username_select,
        unshare_product_button,
        pn.pane.Markdown("### Change Project Parent"),
        change_parent_project_select,
        new_parent_select,
        change_parent_button,
        pn.pane.Markdown("### Change Product Parent"),
        change_product_parent_select,
        new_product_parent_select,
        change_product_parent_button,
        width=400,
        margin=10
    )
    
    # Right column - Product CRUD
    right_column = pn.Column(
        pn.pane.Markdown("# Product Configuration Manager", styles={"font-size": "24px", "font-weight": "bold"}),
        product_config_name_input,
        product_name_input,
        product_config_text_input,
        product_project_select,
        pn.Row(save_button, pn.Spacer(width=20), load_button),
        pn.Row(status_text),
        pn.pane.Markdown("### Products List"),
        products_list,
        width=700,
        margin=10
    )
    
    # Main layout - two columns
    return pn.Row(left_column, right_column, width=1200)


@app.on_event("startup")
async def on_startup():
    """Create database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Multi-tenant ReBAC System",
        "panel_app": "/panel",
        "docs": "/docs",
        "api": "/api"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
