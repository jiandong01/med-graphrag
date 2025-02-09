# Medical Knowledge Graph with LLM Enhancement

A sophisticated medical knowledge graph system that leverages Large Language Models (LLM) and Elasticsearch for intelligent drug information processing and retrieval. The system combines modern AI capabilities with powerful search functionality to create a comprehensive medical knowledge base.

## 🌟 Features

- **Intelligent Drug Information Processing**
  - Standardized tag normalization for drug information
  - Comprehensive drug property extraction
  - Structured data organization
  - Advanced search capabilities

- **Elasticsearch Integration**
  - Full-text search across drug information
  - Complex query support
  - Faceted search capabilities
  - Fast and efficient retrieval

- **Advanced Data Processing**
  - Robust ETL pipeline
  - Batch processing capabilities
  - Comprehensive error handling and logging
  - Optimized search indices

## 🏗️ System Architecture

### Components

#### Tag Normalization (`tag_normalizer.py`)
- Standardizes drug information tags
- Maintains consistent terminology
- Provides Elasticsearch mapping properties
- Handles various Chinese medical terms

#### Drug Entity Extraction (`drug_entity_extractor.py`)
- LLM-based entity extraction
- Structured JSON output
- Batch processing capabilities
- Temporal tracking of extractions

#### Database Management (`database_manager.py`)
- Handles database operations
- Manages data persistence
- Supports multiple database types
- Robust error handling

#### Elasticsearch Integration (`elasticsearch_indexer.py`)
- Creates and manages Elasticsearch indices
- Processes drug information
- Provides search functionality
- Handles complex queries

#### Utility Functions (`utils.py`)
- Configuration management
- Logging setup
- Environment variable handling
- Common helper functions

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Elasticsearch 8.x
- PostgreSQL
- Hugging Face API key

### Installation
1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Configuration
1. Set up environment variables:
   ```
   HF_API_KEY=your_hugging_face_api_key
   ELASTIC_PASSWORD=your_elastic_password
   POSTGRES_DB=your_db_name
   POSTGRES_USER=your_db_user
   POSTGRES_PASSWORD=your_db_password
   ```

2. Configure Elasticsearch:
   - Default URL: http://localhost:9200
   - Default credentials: elastic/changeme

### Usage

1. Process and normalize drug information:
```bash
python src/tag_normalizer.py
```

2. Extract drug entities:
```bash
python src/drug_entity_extractor.py
```

3. Index data in Elasticsearch:
```bash
python src/elasticsearch_indexer.py
```

## 📊 Data Model

### Drug Information Structure
- **Basic Information**
  - Name
  - Specification
  - Manufacturer

- **Detailed Properties**
  - Components
  - Indications
  - Contraindications
  - Adverse Reactions
  - Usage Instructions

### Search Capabilities
- Full-text search
- Field-specific queries
- Complex boolean queries
- Aggregations and analytics

## 🔍 Query Examples

Coming soon...

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Contact

For any questions or suggestions, please open an issue in the repository.
