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

## 🏗️ Project Structure

```
src/
├── core/            # Core functionality and shared components
├── indexers/        # Elasticsearch indexing related modules
│   └── drug_indexer.py         # Drug information indexing
├── extractors/      # Entity extraction modules
│   └── indication_extractor.py # Indication entity extraction
├── normalizers/     # Data normalization modules
│   ├── indication_normalizer.py # Indication text normalization
│   └── tag_normalizer.py       # Drug tag normalization
├── analysis/        # Analysis and statistics scripts
│   └── indication_stats.py     # Indication statistics analysis
└── utils/           # Utility functions and helpers
    └── common.py              # Common utility functions
```

## 🔧 Components

### Indexers
#### Drug Indexer (`indexers/drug_indexer.py`)
- Creates and manages Elasticsearch indices for drug information
- Processes and indexes drug data
- Provides search functionality
- Handles complex queries

### Extractors
#### Indication Extractor (`extractors/indication_extractor.py`)
- LLM-based indication entity extraction
- Structured JSON output
- Batch processing capabilities
- Temporal tracking of extractions

### Normalizers
#### Indication Normalizer (`normalizers/indication_normalizer.py`)
- Standardizes indication text
- Categorizes diseases
- Maintains consistent terminology
- Handles Chinese medical terms

#### Tag Normalizer (`normalizers/tag_normalizer.py`)
- Standardizes drug information tags
- Provides Elasticsearch mapping properties
- Ensures data consistency
- Supports multiple tag types

### Analysis
#### Indication Statistics (`analysis/indication_stats.py`)
- Analyzes indication frequency
- Generates statistical reports
- Exports data to CSV
- Provides insights into disease categories

### Utils
#### Common Utilities (`utils/common.py`)
- Shared utility functions
- Helper methods
- Common data structures
- Reusable components

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Elasticsearch 7.x
- HuggingFace API key
- MySQL database

### Environment Variables
Create a `.env` file with:
```
ELASTIC_PASSWORD=your_elastic_password
HF_API_KEY=your_huggingface_api_key
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=your_database_name
```

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables
4. Run the indexer: `python src/indexers/drug_indexer.py`

## 📊 Usage Examples

### Index Drug Data
```bash
python src/indexers/drug_indexer.py --clear
```

### Extract Indications
```bash
python src/extractors/indication_extractor.py --batch-size 100
```

### Generate Statistics
```bash
python src/analysis/indication_stats.py --stats --export stats.csv
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
