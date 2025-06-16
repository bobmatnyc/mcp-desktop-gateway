"""
Entity-Memory Integration Module
Provides automatic entity extraction and cross-referencing between memories and entities
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

import structlog
from pydantic import BaseModel, Field

# Entity extraction
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    
from ..connectors.entities.models import (
    BaseEntity, Person, Project, Organization,
    EntityType, PersonType, EntityRelationship, RelationshipType
)

logger = structlog.get_logger()


class EntityReference(BaseModel):
    """Reference to an entity from a memory"""
    entity_id: str
    entity_type: EntityType
    entity_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    context: Optional[str] = None  # Surrounding text where entity was found


class EntityExtractionResult(BaseModel):
    """Result of entity extraction from text"""
    entities: List[EntityReference]
    new_entities: List[Dict[str, Any]]  # Entities to be created
    relationships: List[Tuple[str, str, RelationshipType]]  # (from_id, to_id, type)


class EntitiesMemoryIntegration:
    """Handles integration between entities and memory systems"""
    
    def __init__(self, entities_connector=None):
        self.entities_connector = entities_connector
        self.nlp = None
        self._initialize_nlp()
        
    def _initialize_nlp(self):
        """Initialize NLP model for entity extraction"""
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("SpaCy NLP model loaded for entity extraction")
            except Exception as e:
                logger.warning(f"Failed to load SpaCy model: {e}")
                self.nlp = None
        else:
            logger.info("SpaCy not available, using pattern-based extraction")
    
    async def extract_entities_from_text(self, text: str) -> EntityExtractionResult:
        """Extract entities from text content"""
        entities = []
        new_entities = []
        relationships = []
        
        if self.nlp:
            # Use SpaCy for NER
            doc = self.nlp(text)
            
            for ent in doc.ents:
                entity_type = self._map_spacy_to_entity_type(ent.label_)
                if entity_type:
                    # Check if entity exists
                    existing = await self._find_existing_entity(ent.text, entity_type)
                    
                    if existing:
                        entities.append(EntityReference(
                            entity_id=existing['id'],
                            entity_type=entity_type,
                            entity_name=ent.text,
                            confidence=0.8,
                            context=self._get_entity_context(text, ent.start_char, ent.end_char)
                        ))
                    else:
                        # Prepare new entity
                        new_entity = self._prepare_new_entity(ent.text, entity_type, text)
                        new_entities.append(new_entity)
                        
            # Extract relationships from dependency parsing
            relationships.extend(self._extract_relationships_spacy(doc))
        else:
            # Fallback to pattern-based extraction
            entities, new_entities = await self._pattern_based_extraction(text)
            relationships = self._extract_relationships_pattern(text)
            
        return EntityExtractionResult(
            entities=entities,
            new_entities=new_entities,
            relationships=relationships
        )
    
    def _map_spacy_to_entity_type(self, spacy_label: str) -> Optional[EntityType]:
        """Map SpaCy entity labels to our entity types"""
        mapping = {
            'PERSON': EntityType.PERSON,
            'ORG': EntityType.ORGANIZATION,
            'COMPANY': EntityType.ORGANIZATION,
            'PRODUCT': EntityType.PROJECT,  # Approximate mapping
            'WORK_OF_ART': EntityType.PROJECT,  # Approximate mapping
        }
        return mapping.get(spacy_label)
    
    def _get_entity_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Get surrounding context for an entity mention"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
    
    async def _find_existing_entity(self, name: str, entity_type: EntityType) -> Optional[Dict[str, Any]]:
        """Find existing entity by name and type"""
        if not self.entities_connector:
            return None
            
        try:
            # Search for entity
            search_result = await self.entities_connector.search_entities({
                'name': name,
                'entity_type': entity_type.value,
                'limit': 1
            })
            
            if search_result and len(search_result) > 0:
                return search_result[0]
        except Exception as e:
            logger.error(f"Error searching for entity: {e}")
            
        return None
    
    def _prepare_new_entity(self, name: str, entity_type: EntityType, context: str) -> Dict[str, Any]:
        """Prepare a new entity for creation"""
        base_entity = {
            'name': name,
            'entity_type': entity_type.value,
            'description': f"Extracted from memory: {context[:200]}...",
            'tags': ['auto-extracted'],
            'metadata': {
                'extraction_confidence': 0.8,
                'extraction_date': datetime.utcnow().isoformat()
            }
        }
        
        if entity_type == EntityType.PERSON:
            # Try to split first/last name
            parts = name.split(' ', 1)
            base_entity.update({
                'first_name': parts[0],
                'last_name': parts[1] if len(parts) > 1 else '',
                'person_type': PersonType.CONTACT.value  # Default type
            })
        elif entity_type == EntityType.PROJECT:
            base_entity.update({
                'project_info': {
                    'status': 'active'  # Default status
                }
            })
        elif entity_type == EntityType.ORGANIZATION:
            base_entity.update({
                'org_info': {}
            })
            
        return base_entity
    
    async def _pattern_based_extraction(self, text: str) -> Tuple[List[EntityReference], List[Dict[str, Any]]]:
        """Fallback pattern-based entity extraction"""
        entities = []
        new_entities = []
        
        # Common patterns for entity detection
        patterns = {
            EntityType.PERSON: [
                r'\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+said|\s+wrote|\s+mentioned)',
                r'(?:contact|meet|email|call)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            ],
            EntityType.ORGANIZATION: [
                r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:Inc\.|LLC|Corp\.|Corporation|Company)',
                r'(?:at|from|with)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:company|organization)',
            ],
            EntityType.PROJECT: [
                r'(?:project|Project)\s+([A-Z][a-zA-Z0-9\-\_]+)',
                r'(?:working on|developing|building)\s+([A-Z][a-zA-Z0-9\-\_\s]+)',
            ]
        }
        
        for entity_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, text)
                for match in matches:
                    entity_name = match.group(1).strip()
                    
                    # Check if exists
                    existing = await self._find_existing_entity(entity_name, entity_type)
                    
                    if existing:
                        entities.append(EntityReference(
                            entity_id=existing['id'],
                            entity_type=entity_type,
                            entity_name=entity_name,
                            confidence=0.6,  # Lower confidence for pattern matching
                            context=self._get_entity_context(text, match.start(), match.end())
                        ))
                    else:
                        new_entity = self._prepare_new_entity(entity_name, entity_type, text)
                        new_entities.append(new_entity)
                        
        return entities, new_entities
    
    def _extract_relationships_spacy(self, doc) -> List[Tuple[str, str, RelationshipType]]:
        """Extract relationships using SpaCy dependency parsing"""
        relationships = []
        
        # Look for patterns like "X works for Y", "X leads Y", etc.
        for token in doc:
            if token.dep_ == "ROOT" and token.pos_ == "VERB":
                # Check for subject and object
                subject = None
                obj = None
                
                for child in token.children:
                    if child.dep_ in ["nsubj", "nsubjpass"]:
                        subject = child
                    elif child.dep_ in ["dobj", "pobj"]:
                        obj = child
                        
                if subject and obj:
                    # Map verb to relationship type
                    rel_type = self._map_verb_to_relationship(token.text)
                    if rel_type:
                        relationships.append((subject.text, obj.text, rel_type))
                        
        return relationships
    
    def _extract_relationships_pattern(self, text: str) -> List[Tuple[str, str, RelationshipType]]:
        """Extract relationships using patterns"""
        relationships = []
        
        # Relationship patterns
        patterns = [
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+works\s+(?:for|at)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', RelationshipType.WORKS_FOR),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+leads?\s+([A-Z][a-zA-Z0-9\-\_\s]+)', RelationshipType.LEADS_PROJECT),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+reports\s+to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', RelationshipType.REPORTS_TO),
        ]
        
        for pattern, rel_type in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                from_entity = match.group(1).strip()
                to_entity = match.group(2).strip()
                relationships.append((from_entity, to_entity, rel_type))
                
        return relationships
    
    def _map_verb_to_relationship(self, verb: str) -> Optional[RelationshipType]:
        """Map verbs to relationship types"""
        mapping = {
            'works': RelationshipType.WORKS_FOR,
            'leads': RelationshipType.LEADS_PROJECT,
            'manages': RelationshipType.LEADS_PROJECT,
            'reports': RelationshipType.REPORTS_TO,
            'collaborates': RelationshipType.COLLABORATES_ON,
        }
        return mapping.get(verb.lower())
    
    async def create_entities_from_extraction(self, extraction_result: EntityExtractionResult) -> List[str]:
        """Create new entities from extraction result"""
        created_ids = []
        
        if not self.entities_connector:
            return created_ids
            
        for entity_data in extraction_result.new_entities:
            try:
                result = await self.entities_connector.create_entity(entity_data)
                if result and 'id' in result:
                    created_ids.append(result['id'])
                    logger.info(f"Created new entity: {entity_data['name']} ({entity_data['entity_type']})")
            except Exception as e:
                logger.error(f"Failed to create entity {entity_data['name']}: {e}")
                
        return created_ids
    
    async def create_relationships_from_extraction(self, extraction_result: EntityExtractionResult, entity_map: Dict[str, str]):
        """Create relationships between entities"""
        if not self.entities_connector:
            return
            
        for from_name, to_name, rel_type in extraction_result.relationships:
            # Look up entity IDs
            from_id = entity_map.get(from_name)
            to_id = entity_map.get(to_name)
            
            if from_id and to_id:
                try:
                    await self.entities_connector.create_relationship({
                        'from_entity_id': from_id,
                        'to_entity_id': to_id,
                        'relationship_type': rel_type.value,
                        'metadata': {
                            'auto_extracted': True,
                            'extraction_date': datetime.utcnow().isoformat()
                        }
                    })
                    logger.info(f"Created relationship: {from_name} {rel_type.value} {to_name}")
                except Exception as e:
                    logger.error(f"Failed to create relationship: {e}")
    
    async def enrich_memory_with_entities(self, memory_content: str, memory_id: str) -> Dict[str, Any]:
        """Extract entities from memory and create cross-references"""
        # Extract entities
        extraction_result = await self.extract_entities_from_text(memory_content)
        
        # Create new entities
        created_ids = await self.create_entities_from_extraction(extraction_result)
        
        # Build entity map for relationship creation
        entity_map = {}
        for ref in extraction_result.entities:
            entity_map[ref.entity_name] = ref.entity_id
            
        # Add newly created entities to map
        for i, entity_data in enumerate(extraction_result.new_entities):
            if i < len(created_ids):
                entity_map[entity_data['name']] = created_ids[i]
                
        # Create relationships
        await self.create_relationships_from_extraction(extraction_result, entity_map)
        
        # Return enrichment data
        return {
            'memory_id': memory_id,
            'extracted_entities': [
                {
                    'id': ref.entity_id,
                    'name': ref.entity_name,
                    'type': ref.entity_type.value,
                    'confidence': ref.confidence
                }
                for ref in extraction_result.entities
            ],
            'created_entities': created_ids,
            'relationships': len(extraction_result.relationships)
        }
    
    async def get_related_memories_for_entity(self, entity_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get memories that reference a specific entity"""
        # This would query the memory system for memories that contain references to this entity
        # For now, return empty list - will be implemented when we add entity references to memories
        return []
    
    async def index_entity_for_vector_search(self, entity: BaseEntity) -> bool:
        """Generate and store vector embeddings for an entity"""
        # This will be implemented to generate embeddings for entity attributes
        # and store them in Qdrant for semantic search
        return True