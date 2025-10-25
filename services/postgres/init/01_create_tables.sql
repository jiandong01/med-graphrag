-- PostgreSQL table creation scripts
-- Converted from MySQL structure

-- Table: categories_table (zhushou)
CREATE TABLE categories_table (
  ids SERIAL PRIMARY KEY,
  name VARCHAR(255) DEFAULT NULL,
  sort INT NOT NULL DEFAULT 0,
  create_time TIMESTAMP NOT NULL,
  parent_id CHAR(32) DEFAULT NULL,
  id CHAR(32) NOT NULL UNIQUE,
  category VARCHAR(255) DEFAULT NULL,
  type VARCHAR(255) DEFAULT NULL,
  is_leaf VARCHAR(5) DEFAULT NULL,
  icon_base64 TEXT DEFAULT NULL
);

-- Create indexes for categories_table
CREATE INDEX idx_categories_parent_id ON categories_table(parent_id);
CREATE INDEX idx_categories_name ON categories_table(name);

-- Add comments for categories_table
COMMENT ON TABLE categories_table IS 'Table for storing hierarchical data with optional icons and metadata';
COMMENT ON COLUMN categories_table.ids IS 'Primary key, auto-incremented';
COMMENT ON COLUMN categories_table.name IS 'Name of the category or item';
COMMENT ON COLUMN categories_table.sort IS 'Sorting index for display purposes';
COMMENT ON COLUMN categories_table.create_time IS 'Creation timestamp';
COMMENT ON COLUMN categories_table.parent_id IS 'Parent ID for hierarchical relationships';
COMMENT ON COLUMN categories_table.id IS 'Unique identifier for the record';
COMMENT ON COLUMN categories_table.category IS 'Category of the item';
COMMENT ON COLUMN categories_table.type IS 'Type of the item (if applicable)';
COMMENT ON COLUMN categories_table.is_leaf IS 'Indicates whether it is a leaf node (true/false)';
COMMENT ON COLUMN categories_table.icon_base64 IS 'Base64-encoded icon data (image)';

-- Table: drugs_table (zhushouc)
CREATE TABLE drugs_table (
  ids SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  create_time TIMESTAMP NOT NULL,
  id CHAR(32) NOT NULL,
  spec TEXT NOT NULL,
  manufacturer VARCHAR(255) NOT NULL,
  parent_id CHAR(32) DEFAULT NULL
);

-- Create indexes for drugs_table
CREATE INDEX idx_drugs_parent_id ON drugs_table(parent_id);
CREATE INDEX idx_drugs_name ON drugs_table(name);

-- Add comments for drugs_table
COMMENT ON TABLE drugs_table IS 'Table for storing drug details and relationships';
COMMENT ON COLUMN drugs_table.ids IS 'Primary key, auto-incremented';
COMMENT ON COLUMN drugs_table.name IS 'Drug name';
COMMENT ON COLUMN drugs_table.create_time IS 'Creation timestamp';
COMMENT ON COLUMN drugs_table.id IS 'Unique identifier for the drug';
COMMENT ON COLUMN drugs_table.spec IS 'Specification or description of the drug';
COMMENT ON COLUMN drugs_table.manufacturer IS 'Name of the drug manufacturer';
COMMENT ON COLUMN drugs_table.parent_id IS 'Parent ID for hierarchical relationships';

-- Table: drug_details_table (zhushour)
CREATE TABLE drug_details_table (
  ids SERIAL PRIMARY KEY,
  tag VARCHAR(255) NOT NULL,
  create_time TIMESTAMP NOT NULL,
  update_time TIMESTAMP DEFAULT NULL,
  del_flag SMALLINT NOT NULL DEFAULT 0,
  tenant_id VARCHAR(255) DEFAULT NULL,
  id CHAR(32) NOT NULL,
  display_type SMALLINT NOT NULL DEFAULT 0,
  flag SMALLINT NOT NULL DEFAULT 0,
  tcontent TEXT NOT NULL,
  suoyin SMALLINT NOT NULL DEFAULT 0,
  type SMALLINT NOT NULL DEFAULT 1
);

-- Create indexes for drug_details_table
CREATE INDEX idx_drug_details_id ON drug_details_table(id);
CREATE INDEX idx_drug_details_tag ON drug_details_table(tag);

-- Add comments for drug_details_table
COMMENT ON TABLE drug_details_table IS 'Table for storing drug information';
COMMENT ON COLUMN drug_details_table.ids IS 'Primary key, auto-incremented';
COMMENT ON COLUMN drug_details_table.tag IS 'Tag or category of the entry';
COMMENT ON COLUMN drug_details_table.create_time IS 'Creation timestamp';
COMMENT ON COLUMN drug_details_table.update_time IS 'Last update timestamp, nullable';
COMMENT ON COLUMN drug_details_table.del_flag IS 'Delete flag (0 for active, 1 for deleted)';
COMMENT ON COLUMN drug_details_table.tenant_id IS 'Tenant identifier, nullable';
COMMENT ON COLUMN drug_details_table.id IS 'Unique identifier for the drug';
COMMENT ON COLUMN drug_details_table.display_type IS 'Display type (e.g., 0, 4)';
COMMENT ON COLUMN drug_details_table.flag IS 'Flag value for special indicators';
COMMENT ON COLUMN drug_details_table.tcontent IS 'Content of the entry, typically JSON or text';
COMMENT ON COLUMN drug_details_table.suoyin IS 'Index flag (0 by default)';
COMMENT ON COLUMN drug_details_table.type IS 'Type of entry, usually 1';
