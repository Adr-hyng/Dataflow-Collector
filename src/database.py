import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Boolean, TIMESTAMP, ARRAY, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from typing import Optional, List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    project_url = Column(String(500), unique=True, nullable=False)
    workspace_id = Column(String(100), nullable=False)
    project_id = Column(String(100), nullable=False)
    title = Column(String(255))
    author = Column(String(255))
    image_count = Column(Integer)
    model_count = Column(Integer)
    classes = Column(ARRAY(Text))
    downloaded = Column(Boolean, default=False)
    download_path = Column(String(500))
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

class SearchHistory(Base):
    __tablename__ = 'search_history'
    
    id = Column(Integer, primary_key=True)
    search_term = Column(String(255), nullable=False)
    results_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=func.now())

class DatabaseManager:
    def __init__(self, database_url: str = None):
        if database_url is None:
            database_url = os.getenv('DATABASE_URL', 'postgresql://scraper:password@localhost:5432/roboflow_scraper')
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database connection established")
    
    def get_session(self):
        return self.SessionLocal()
    
    def project_exists(self, project_url: str) -> bool:
        """Check if a project URL already exists in the database"""
        with self.get_session() as session:
            project = session.query(Project).filter(Project.project_url == project_url).first()
            return project is not None
    
    def add_project(self, project_data: dict) -> Optional[Project]:
        """Add a new project to the database"""
        try:
            with self.get_session() as session:
                project = Project(**project_data)
                session.add(project)
                session.commit()
                session.refresh(project)
                logger.info(f"Added project: {project.title} ({project.project_url})")
                return project
        except Exception as e:
            logger.error(f"Error adding project: {e}")
            return None
    
    def update_project_download_status(self, project_url: str, download_path: str) -> bool:
        """Update project download status"""
        try:
            with self.get_session() as session:
                project = session.query(Project).filter(Project.project_url == project_url).first()
                if project:
                    project.downloaded = True
                    project.download_path = download_path
                    project.updated_at = func.now()
                    session.commit()
                    logger.info(f"Updated download status for project: {project.title}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error updating project download status: {e}")
            return False
    
    def get_undownloaded_projects(self) -> List[Project]:
        """Get all projects that haven't been downloaded yet"""
        with self.get_session() as session:
            return session.query(Project).filter(Project.downloaded == False).all()
    
    def add_search_history(self, search_term: str, results_count: int):
        """Add search history entry"""
        try:
            with self.get_session() as session:
                search_entry = SearchHistory(search_term=search_term, results_count=results_count)
                session.add(search_entry)
                session.commit()
                logger.info(f"Added search history: {search_term} ({results_count} results)")
        except Exception as e:
            logger.error(f"Error adding search history: {e}")
    
    def get_project_by_url(self, project_url: str) -> Optional[Project]:
        """Get project by URL"""
        with self.get_session() as session:
            return session.query(Project).filter(Project.project_url == project_url).first()
