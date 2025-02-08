# Medical Knowledge Graph with LLM Enhancement

A sophisticated medical knowledge graph system that leverages Large Language Models (LLM) for intelligent entity extraction and relationship building from medical texts. The system combines traditional database systems with modern AI capabilities and graph database technology to create a comprehensive medical knowledge base.

## 🌟 Features

- **Intelligent Entity Extraction**
  - Utilizes DeepSeek-R1-Distill-Qwen-32B model for processing medical texts
  - Extracts diseases, symptoms, and medical relationships
  - Provides confidence scores and evidence levels
  - Standardizes medical terminology

- **Comprehensive Knowledge Graph**
  - Hierarchical drug categorization
  - Detailed drug information and properties
  - Rich relationship types (indications, contraindications, interactions)
  - Manufacturer and production information

- **Advanced Data Processing**
  - ETL pipeline from MySQL to Neo4j
  - Batch processing capabilities
  - Robust error handling and logging
  - Optimized graph queries with indexes

## 🏗️ System Architecture

### Data Flow
1. Raw medical data stored in MySQL
2. LLM processes and extracts structured entities
3. Data transformation into graph structure
4. Storage in Neo4j graph database

### Components

#### Entity Generation (`generate_drug_entity.py`)
- LLM-based entity extraction
- Structured JSON output format
- Batch processing capabilities
- Temporal tracking of extractions

#### Knowledge Graph Construction (`generate_raw_kg.py`)
- Comprehensive node types:
  - Drugs
  - Categories
  - Manufacturers
  - Medical conditions
  - Adverse reactions
  - Contraindications
- Rich relationship types:
  - BELONGS_TO
  - MANUFACTURED_BY
  - HAS_INDICATION
  - MAY_CAUSE
  - CONTRAINDICATED_WITH
  - HAS_INTERACTION

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- MySQL
- Neo4j
- Hugging Face API key

### Installation
1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Configuration
1. Set up MySQL database with required tables:
   - categories_table
   - drugs_table
   - drug_details_table

2. Configure Neo4j connection:
   - Default port: 7687
   - Default credentials: neo4j/test_neo4j

3. Set up your Hugging Face API key for LLM access

### Usage

1. Generate entities from medical texts:
```python
python src/generate_drug_entity.py
```

2. Build the knowledge graph:
```python
python src/generate_raw_kg.py
```

## 📊 Data Model

### Node Types
- **Drug**: Pharmaceutical products with properties
- **Category**: Hierarchical classification system
- **Manufacturer**: Production companies
- **Indication**: Medical conditions and uses
- **AdverseReaction**: Side effects
- **Contraindication**: Usage warnings
- **DrugInteraction**: Inter-drug effects

### Relationship Types
- **BELONGS_TO**: Drug category hierarchy
- **MANUFACTURED_BY**: Production information
- **HAS_INDICATION**: Drug uses and applications
- **MAY_CAUSE**: Potential side effects
- **CONTRAINDICATED_WITH**: Usage restrictions
- **HAS_INTERACTION**: Drug interactions

## 🔍 Query Examples

Coming soon...

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Contact

For any questions or suggestions, please open an issue in the repository.
