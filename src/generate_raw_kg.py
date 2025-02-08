#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Knowledge Graph Builder Script
============================

This script is responsible for building a knowledge graph by:
1. Loading raw data from MySQL database (db/mysql/)
2. Processing and transforming the data into graph structure
3. Saving the processed graph data into Neo4j database (db/neo4j/)

The process involves:
- Extracting entities and relationships from MySQL tables
- Cleaning and normalizing the data
- Creating graph nodes and relationships
- Loading the structured data into Neo4j

Usage:
    python generate_raw_kg.py

Dependencies:
    - mysql-connector-python
    - neo4j
"""

from neo4j import GraphDatabase
import pandas as pd
import json
from sqlalchemy import create_engine
from tqdm import tqdm

# MySQL connection parameters (based on docker-compose.yaml)
MYSQL_HOST = "localhost"
MYSQL_PORT = "3306"
MYSQL_DB = "mydatabase"
MYSQL_USER = "myuser"
MYSQL_PASSWORD = "mypassword"

# Create MySQL connection string
MYSQL_URL = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

class Neo4jDrugKnowledgeGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_category_hierarchy(self, categories_df):
        """Create drug category hierarchy"""
        print("\nCreating category hierarchy...")
        with self.driver.session() as session:
            for _, row in tqdm(categories_df.iterrows(), total=len(categories_df), desc="Processing categories"):
                # Preserve all original properties
                category_props = {
                    'id': row['id'],
                    'name': row['name'],
                    'sort': row['sort'],
                    'create_time': str(row['create_time']),
                    'is_leaf': row['is_leaf'],
                    'icon_base64': row['icon_base64']
                }

                # Create category node
                session.run("""
                    MERGE (c:Category {id: $id})
                    SET c += $properties
                """, id=row['id'], properties=category_props)

                # Create hierarchy relationship
                if row['parent_id'] != '0':
                    session.run("""
                        MATCH (child:Category {id: $child_id})
                        MATCH (parent:Category {id: $parent_id})
                        MERGE (child)-[:SUBCATEGORY_OF]->(parent)
                    """, child_id=row['id'], parent_id=row['parent_id'])

    def create_drug_nodes_and_relationships(self, drugs_df, drug_details_df):
        """Create drug nodes with all details"""
        print("\nCreating drug nodes and relationships...")
        total_drugs = len(drugs_df)
        batch_size = 1000
        total_details = len(drug_details_df)
        processed_details = 0
        
        print(f"Total drugs to process: {total_drugs}")
        print(f"Total details to process: {total_details}")
        
        with self.driver.session() as session:
            for idx, (_, drug) in enumerate(tqdm(drugs_df.iterrows(), total=total_drugs, desc="Processing drugs", unit="drugs")):
                # Preserve all original drug properties
                drug_properties = {
                    'id': drug['id'],
                    'name': drug['name'],
                    'create_time': str(drug['create_time']),
                    'spec': drug['spec'],
                    'manufacturer': drug['manufacturer']
                }

                # Create drug node
                session.run("""
                    MERGE (d:Drug {id: $id})
                    SET d += $properties
                """, id=drug['id'], properties=drug_properties)

                # Create manufacturer node and relationship
                session.run("""
                    MERGE (m:Manufacturer {name: $manufacturer})
                    WITH m
                    MATCH (d:Drug {id: $drug_id})
                    MERGE (d)-[:MANUFACTURED_BY]->(m)
                """, manufacturer=drug['manufacturer'], drug_id=drug['id'])

                # Link to category
                if drug['parent_id']:
                    session.run("""
                        MATCH (d:Drug {id: $drug_id})
                        MATCH (c:Category {id: $category_id})
                        MERGE (d)-[:BELONGS_TO]->(c)
                    """, drug_id=drug['id'], category_id=drug['parent_id'])

                # Process drug details
                details = drug_details_df[drug_details_df['id'] == drug['id']]
                details_count = len(details)
                processed_details += details_count
                self._create_drug_details(session, drug['id'], details, processed_details, total_details)
                
                # Log progress for drugs
                if (idx + 1) % batch_size == 0:
                    print(f"\nProcessed {idx + 1}/{total_drugs} drugs ({(idx + 1)/total_drugs*100:.1f}%)")
                    print(f"Processed {processed_details}/{total_details} details ({processed_details/total_details*100:.1f}%)")

    def _create_drug_details(self, session, drug_id, details, processed_details, total_details):
        """Create detailed information nodes and relationships"""
        details_count = len(details)
        
        # Only show progress bar for larger batches of details
        if details_count > 100:
            details_iter = tqdm(details.iterrows(), total=details_count, desc=f"Processing {details_count} details for drug {drug_id}", leave=False)
        else:
            details_iter = details.iterrows()
            
        for _, detail in details_iter:
            # Preserve all original detail properties
            detail_props = {
                'tag': detail['tag'],
                'create_time': str(detail['create_time']),
                'update_time': str(detail['update_time']) if detail['update_time'] else None,
                'del_flag': detail['del_flag'],
                'tenant_id': detail['tenant_id'],
                'display_type': detail['display_type'],
                'flag': detail['flag'],
                'content': detail['tcontent']
            }

            # Create appropriate nodes and relationships based on tag
            if detail['tag'] == '功能主治':
                self._create_indication_relationship(session, drug_id, detail['tcontent'], detail_props)
            elif detail['tag'] == '不良反应':
                self._create_adverse_reaction_relationship(session, drug_id, detail['tcontent'], detail_props)
            elif detail['tag'] == '禁忌':
                self._create_contraindication_relationship(session, drug_id, detail['tcontent'], detail_props)
            elif detail['tag'] == '药物相互作用':
                self._create_interaction_relationship(session, drug_id, detail['tcontent'], detail_props)
            
            # Store all details as DrugDetail nodes to preserve complete information
            session.run("""
                MATCH (d:Drug {id: $drug_id})
                MERGE (detail:DrugDetail {
                    drug_id: $drug_id,
                    tag: $props.tag
                })
                SET detail += $props
                MERGE (d)-[:HAS_DETAIL]->(detail)
            """, drug_id=drug_id, props=detail_props)

    def _create_indication_relationship(self, session, drug_id, content, props):
        session.run("""
            MATCH (d:Drug {id: $drug_id})
            MERGE (i:Indication {content: $content})
            MERGE (d)-[r:HAS_INDICATION]->(i)
            SET r += $props
        """, drug_id=drug_id, content=content, props=props)

    def _create_adverse_reaction_relationship(self, session, drug_id, content, props):
        session.run("""
            MATCH (d:Drug {id: $drug_id})
            MERGE (ar:AdverseReaction {content: $content})
            MERGE (d)-[r:MAY_CAUSE]->(ar)
            SET r += $props
        """, drug_id=drug_id, content=content, props=props)

    def _create_contraindication_relationship(self, session, drug_id, content, props):
        session.run("""
            MATCH (d:Drug {id: $drug_id})
            MERGE (c:Contraindication {content: $content})
            MERGE (d)-[r:CONTRAINDICATED_WITH]->(c)
            SET r += $props
        """, drug_id=drug_id, content=content, props=props)

    def _create_interaction_relationship(self, session, drug_id, content, props):
        session.run("""
            MATCH (d:Drug {id: $drug_id})
            MERGE (i:DrugInteraction {content: $content})
            MERGE (d)-[r:HAS_INTERACTION]->(i)
            SET r += $props
        """, drug_id=drug_id, content=content, props=props)

    def create_indexes(self):
        """Create indexes for better query performance"""
        with self.driver.session() as session:
            session.run("CREATE INDEX IF NOT EXISTS FOR (d:Drug) ON (d.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (c:Category) ON (c.id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (m:Manufacturer) ON (m.name)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (dd:DrugDetail) ON (dd.drug_id, dd.tag)")

def main():
    print("Starting ETL process...")
    
    # Initialize MySQL connection
    print("\nConnecting to MySQL database...")
    mysql_conn = create_engine(MYSQL_URL)
    
    # Initialize Neo4j connection
    print("Connecting to Neo4j database...")
    graph = Neo4jDrugKnowledgeGraph(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="test_neo4j"
    )

    try:
        # Create indexes
        print("\nCreating Neo4j indexes...")
        graph.create_indexes()

        # Read data from MySQL
        print("\nReading data from MySQL...")
        print("- Loading categories...")
        categories_df = pd.read_sql("SELECT * FROM categories_table", mysql_conn)
        print(f"  Loaded {len(categories_df)} categories")
        
        print("- Loading drugs...")
        drugs_df = pd.read_sql("SELECT * FROM drugs_table", mysql_conn)
        print(f"  Loaded {len(drugs_df)} drugs")
        
        print("- Loading drug details...")
        drug_details_df = pd.read_sql("SELECT * FROM drug_details_table", mysql_conn)
        print(f"  Loaded {len(drug_details_df)} drug details")

        # Process and import data
        graph.create_category_hierarchy(categories_df)
        graph.create_drug_nodes_and_relationships(drugs_df, drug_details_df)
        
        print("\nETL process completed successfully!")

    finally:
        graph.close()
        mysql_conn.dispose()  # Close MySQL connection

if __name__ == "__main__":
    main()