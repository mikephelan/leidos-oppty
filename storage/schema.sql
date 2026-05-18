-- Database schema for CFR and FAA Orders
-- SQLite database for storing CFR regulations and FAA Orders with their mappings

-- CFR Titles
CREATE TABLE IF NOT EXISTS cfr_titles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_number INTEGER NOT NULL UNIQUE,
    title_name TEXT NOT NULL,
    effective_date DATE,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CFR Chapters
CREATE TABLE IF NOT EXISTS cfr_chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_number TEXT NOT NULL,
    chapter_name TEXT NOT NULL,
    title_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (title_id) REFERENCES cfr_titles(id) ON DELETE CASCADE,
    UNIQUE(title_id, chapter_number)
);

-- CFR Subchapters
CREATE TABLE IF NOT EXISTS cfr_subchapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subchapter_letter TEXT NOT NULL,
    subchapter_name TEXT NOT NULL,
    chapter_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chapter_id) REFERENCES cfr_chapters(id) ON DELETE CASCADE,
    UNIQUE(chapter_id, subchapter_letter)
);

-- CFR Parts
CREATE TABLE IF NOT EXISTS cfr_parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number INTEGER NOT NULL,
    part_name TEXT NOT NULL,
    title_number INTEGER NOT NULL,
    chapter_id INTEGER,
    subchapter_id INTEGER,
    authority TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chapter_id) REFERENCES cfr_chapters(id) ON DELETE SET NULL,
    FOREIGN KEY (subchapter_id) REFERENCES cfr_subchapters(id) ON DELETE SET NULL,
    UNIQUE(title_number, part_number)
);

-- CFR Subparts
CREATE TABLE IF NOT EXISTS cfr_subparts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subpart_letter TEXT NOT NULL,
    subpart_name TEXT NOT NULL,
    part_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES cfr_parts(id) ON DELETE CASCADE,
    UNIQUE(part_id, subpart_letter)
);

-- CFR Sections
CREATE TABLE IF NOT EXISTS cfr_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_number TEXT NOT NULL,
    section_title TEXT NOT NULL,
    content TEXT,
    part_id INTEGER NOT NULL,
    subpart_id INTEGER,
    effective_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES cfr_parts(id) ON DELETE CASCADE,
    FOREIGN KEY (subpart_id) REFERENCES cfr_subparts(id) ON DELETE SET NULL,
    UNIQUE(part_id, section_number)
);

-- CFR Paragraphs
CREATE TABLE IF NOT EXISTS cfr_paragraphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paragraph_id TEXT NOT NULL,
    content TEXT NOT NULL,
    section_id INTEGER NOT NULL,
    parent_paragraph_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (section_id) REFERENCES cfr_sections(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_paragraph_id) REFERENCES cfr_paragraphs(id) ON DELETE CASCADE
);

-- CFR Cross References
CREATE TABLE IF NOT EXISTS cfr_cross_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_section_id INTEGER NOT NULL,
    target_section_id INTEGER NOT NULL,
    reference_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_section_id) REFERENCES cfr_sections(id) ON DELETE CASCADE,
    FOREIGN KEY (target_section_id) REFERENCES cfr_sections(id) ON DELETE CASCADE,
    UNIQUE(source_section_id, target_section_id)
);

-- FAA Orders
CREATE TABLE IF NOT EXISTS faa_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    order_title TEXT NOT NULL,
    effective_date DATE,
    file_path TEXT NOT NULL,
    extracted_text TEXT,
    metadata TEXT,  -- JSON string for additional metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CFR References in Orders
CREATE TABLE IF NOT EXISTS order_cfr_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    cfr_section TEXT NOT NULL,
    part_number INTEGER NOT NULL,
    section_number TEXT NOT NULL,
    context TEXT,
    page_number INTEGER,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES faa_orders(id) ON DELETE CASCADE
);

-- CFR-Order Mappings
CREATE TABLE IF NOT EXISTS cfr_order_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cfr_section_id INTEGER NOT NULL,
    faa_order_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL,  -- 'implements', 'references', 'clarifies', etc.
    confidence_score REAL NOT NULL CHECK(confidence_score >= 0 AND confidence_score <= 1),
    extraction_method TEXT NOT NULL,  -- 'explicit_citation', 'semantic_match', etc.
    context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cfr_section_id) REFERENCES cfr_sections(id) ON DELETE CASCADE,
    FOREIGN KEY (faa_order_id) REFERENCES faa_orders(id) ON DELETE CASCADE,
    UNIQUE(cfr_section_id, faa_order_id, relationship_type)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cfr_parts_title ON cfr_parts(title_number);
CREATE INDEX IF NOT EXISTS idx_cfr_sections_part ON cfr_sections(part_id);
CREATE INDEX IF NOT EXISTS idx_cfr_sections_number ON cfr_sections(section_number);
CREATE INDEX IF NOT EXISTS idx_order_references_order ON order_cfr_references(order_id);
CREATE INDEX IF NOT EXISTS idx_order_references_section ON order_cfr_references(cfr_section);
CREATE INDEX IF NOT EXISTS idx_mappings_section ON cfr_order_mappings(cfr_section_id);
CREATE INDEX IF NOT EXISTS idx_mappings_order ON cfr_order_mappings(faa_order_id);
CREATE INDEX IF NOT EXISTS idx_mappings_confidence ON cfr_order_mappings(confidence_score);

-- Full-text search for CFR content
CREATE VIRTUAL TABLE IF NOT EXISTS cfr_sections_fts USING fts5(
    section_number,
    section_title,
    content,
    content=cfr_sections,
    content_rowid=id
);

-- Triggers to keep FTS index updated
CREATE TRIGGER IF NOT EXISTS cfr_sections_ai AFTER INSERT ON cfr_sections BEGIN
    INSERT INTO cfr_sections_fts(rowid, section_number, section_title, content)
    VALUES (new.id, new.section_number, new.section_title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS cfr_sections_ad AFTER DELETE ON cfr_sections BEGIN
    DELETE FROM cfr_sections_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS cfr_sections_au AFTER UPDATE ON cfr_sections BEGIN
    DELETE FROM cfr_sections_fts WHERE rowid = old.id;
    INSERT INTO cfr_sections_fts(rowid, section_number, section_title, content)
    VALUES (new.id, new.section_number, new.section_title, new.content);
END;

-- Full-text search for FAA Orders
CREATE VIRTUAL TABLE IF NOT EXISTS faa_orders_fts USING fts5(
    order_number,
    order_title,
    extracted_text,
    content=faa_orders,
    content_rowid=id
);

-- Triggers for FAA Orders FTS
CREATE TRIGGER IF NOT EXISTS faa_orders_ai AFTER INSERT ON faa_orders BEGIN
    INSERT INTO faa_orders_fts(rowid, order_number, order_title, extracted_text)
    VALUES (new.id, new.order_number, new.order_title, new.extracted_text);
END;

CREATE TRIGGER IF NOT EXISTS faa_orders_ad AFTER DELETE ON faa_orders BEGIN
    DELETE FROM faa_orders_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS faa_orders_au AFTER UPDATE ON faa_orders BEGIN
    DELETE FROM faa_orders_fts WHERE rowid = old.id;
    INSERT INTO faa_orders_fts(rowid, order_number, order_title, extracted_text)
    VALUES (new.id, new.order_number, new.order_title, new.extracted_text);
END;

-- Made with Bob
