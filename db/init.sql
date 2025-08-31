-- Initialize database schema for roboflow scraper

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    project_url VARCHAR(500) UNIQUE NOT NULL,
    workspace_id VARCHAR(100) NOT NULL,
    project_id VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    author VARCHAR(255),
    image_count INTEGER,
    model_count INTEGER,
    classes TEXT[],
    downloaded BOOLEAN DEFAULT FALSE,
    download_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    search_term VARCHAR(255) NOT NULL,
    results_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_projects_url ON projects(project_url);
CREATE INDEX IF NOT EXISTS idx_projects_workspace_project ON projects(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_projects_downloaded ON projects(downloaded);
CREATE INDEX IF NOT EXISTS idx_search_history_term ON search_history(search_term);
