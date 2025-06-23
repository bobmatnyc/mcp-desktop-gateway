"""
Prompt versioning and management system
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import shutil
import logging

from .models import PromptVersion, PromptType

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages prompt versions and deployments"""
    
    def __init__(self, storage_path: str = "prompt_training"):
        self.storage_path = Path(storage_path)
        self.system_prompts_path = self.storage_path / "system"
        self.user_prompts_path = self.storage_path / "user"
        self.versions_path = self.storage_path / "versions"
        
        # Create directories
        for path in [self.system_prompts_path, self.user_prompts_path, self.versions_path]:
            path.mkdir(parents=True, exist_ok=True)
            
        # Cache for active prompts
        self._active_prompts: Dict[str, PromptVersion] = {}
        self._load_active_prompts()
        
    def create_prompt(
        self,
        prompt_id: str,
        prompt_type: PromptType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PromptVersion:
        """Create a new prompt with initial version"""
        version = PromptVersion(
            prompt_id=prompt_id,
            version=1,
            content=content,
            metadata=metadata or {},
            is_active=True,
            is_experimental=False
        )
        
        self._save_version(version)
        self._set_active_version(prompt_id, version)
        
        logger.info(f"Created new prompt {prompt_id} v{version.version}")
        return version
        
    def create_new_version(
        self,
        prompt_id: str,
        content: str,
        parent_version_id: str,
        training_data_ids: Optional[List[str]] = None,
        training_params: Optional[Dict[str, Any]] = None,
        is_experimental: bool = True
    ) -> PromptVersion:
        """Create a new version of an existing prompt"""
        # Get the latest version number
        existing_versions = self.get_all_versions(prompt_id)
        latest_version = max([v.version for v in existing_versions]) if existing_versions else 0
        
        version = PromptVersion(
            prompt_id=prompt_id,
            version=latest_version + 1,
            content=content,
            parent_version_id=parent_version_id,
            training_data_ids=training_data_ids or [],
            training_params=training_params or {},
            is_experimental=is_experimental,
            is_active=False  # Not active by default
        )
        
        self._save_version(version)
        logger.info(f"Created new version {prompt_id} v{version.version} (experimental={is_experimental})")
        
        return version
        
    def get_active_prompt(self, prompt_id: str) -> Optional[PromptVersion]:
        """Get the currently active version of a prompt"""
        return self._active_prompts.get(prompt_id)
        
    def get_version(self, prompt_id: str, version_number: int) -> Optional[PromptVersion]:
        """Get a specific version of a prompt"""
        version_file = self.versions_path / prompt_id / f"v{version_number}.json"
        if not version_file.exists():
            return None
            
        return self._load_version_from_file(version_file)
        
    def get_all_versions(self, prompt_id: str) -> List[PromptVersion]:
        """Get all versions of a prompt"""
        prompt_dir = self.versions_path / prompt_id
        if not prompt_dir.exists():
            return []
            
        versions = []
        for version_file in prompt_dir.glob("v*.json"):
            version = self._load_version_from_file(version_file)
            if version:
                versions.append(version)
                
        return sorted(versions, key=lambda v: v.version)
        
    def deploy_version(self, prompt_id: str, version_number: int) -> bool:
        """Deploy a specific version as the active prompt"""
        version = self.get_version(prompt_id, version_number)
        if not version:
            logger.error(f"Version {prompt_id} v{version_number} not found")
            return False
            
        # Mark previous active version as inactive
        if prompt_id in self._active_prompts:
            old_version = self._active_prompts[prompt_id]
            old_version.is_active = False
            old_version.retired_at = datetime.now()
            self._save_version(old_version)
            
        # Mark new version as active
        version.is_active = True
        version.is_experimental = False
        version.deployed_at = datetime.now()
        self._save_version(version)
        
        # Update active prompts
        self._set_active_version(prompt_id, version)
        
        logger.info(f"Deployed {prompt_id} v{version_number} as active version")
        return True
        
    def rollback_prompt(self, prompt_id: str) -> bool:
        """Rollback to the previous version of a prompt"""
        versions = self.get_all_versions(prompt_id)
        if len(versions) < 2:
            logger.error(f"Cannot rollback {prompt_id}: insufficient versions")
            return False
            
        # Find current active and previous version
        active_version = None
        previous_version = None
        
        for i, version in enumerate(reversed(versions)):
            if version.is_active:
                active_version = version
                if i + 1 < len(versions):
                    previous_version = versions[-(i + 2)]
                break
                
        if not active_version or not previous_version:
            logger.error(f"Cannot rollback {prompt_id}: no previous version found")
            return False
            
        # Deploy the previous version
        return self.deploy_version(prompt_id, previous_version.version)
        
    def update_version_metrics(
        self,
        prompt_id: str,
        version_number: int,
        metrics: Dict[str, float]
    ):
        """Update performance metrics for a version"""
        version = self.get_version(prompt_id, version_number)
        if not version:
            return
            
        # Update metrics
        if "rating" in metrics:
            version.avg_rating = metrics["rating"]
        if "success_rate" in metrics:
            version.success_rate = metrics["success_rate"]
        if "error_rate" in metrics:
            version.error_rate = metrics["error_rate"]
        if "usage_count" in metrics:
            version.usage_count = int(metrics["usage_count"])
            
        self._save_version(version)
        
    def export_prompts(self, output_dir: str, prompt_type: Optional[PromptType] = None):
        """Export prompts to external directory for use"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Export active prompts
        for prompt_id, version in self._active_prompts.items():
            if prompt_type and not prompt_id.startswith(prompt_type.value):
                continue
                
            # Determine output file path
            if prompt_id.startswith(PromptType.SYSTEM.value):
                file_name = f"{prompt_id.replace('system_', '')}.txt"
                file_path = output_path / "system" / file_name
            else:
                file_name = f"{prompt_id}.txt"
                file_path = output_path / "user" / file_name
                
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write prompt content
            with open(file_path, 'w') as f:
                f.write(version.content)
                
            # Write metadata
            meta_path = file_path.with_suffix('.json')
            with open(meta_path, 'w') as f:
                json.dump({
                    "prompt_id": prompt_id,
                    "version": version.version,
                    "exported_at": datetime.now().isoformat(),
                    "metrics": {
                        "avg_rating": version.avg_rating,
                        "success_rate": version.success_rate,
                        "error_rate": version.error_rate,
                        "usage_count": version.usage_count
                    }
                }, f, indent=2)
                
        logger.info(f"Exported {len(self._active_prompts)} prompts to {output_dir}")
        
    def import_prompt(self, prompt_id: str, prompt_type: PromptType, file_path: str):
        """Import a prompt from an external file"""
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Check if prompt exists
        existing = self.get_active_prompt(prompt_id)
        if existing and existing.content == content:
            logger.info(f"Prompt {prompt_id} unchanged, skipping import")
            return existing
            
        if existing:
            # Create new version
            return self.create_new_version(
                prompt_id=prompt_id,
                content=content,
                parent_version_id=existing.id,
                is_experimental=False
            )
        else:
            # Create new prompt
            return self.create_prompt(
                prompt_id=prompt_id,
                prompt_type=prompt_type,
                content=content
            )
            
    def _save_version(self, version: PromptVersion):
        """Save a prompt version to disk"""
        version_dir = self.versions_path / version.prompt_id
        version_dir.mkdir(parents=True, exist_ok=True)
        
        version_file = version_dir / f"v{version.version}.json"
        with open(version_file, 'w') as f:
            json.dump(self._version_to_dict(version), f, indent=2)
            
    def _load_version_from_file(self, file_path: Path) -> Optional[PromptVersion]:
        """Load a version from a JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return self._dict_to_version(data)
        except Exception as e:
            logger.error(f"Error loading version from {file_path}: {e}")
            return None
            
    def _set_active_version(self, prompt_id: str, version: PromptVersion):
        """Set a version as the active prompt"""
        self._active_prompts[prompt_id] = version
        
        # Save to active prompts file
        prompt_type = PromptType.SYSTEM if prompt_id.startswith("system_") else PromptType.USER
        active_dir = self.system_prompts_path if prompt_type == PromptType.SYSTEM else self.user_prompts_path
        
        active_file = active_dir / f"{prompt_id}.json"
        with open(active_file, 'w') as f:
            json.dump({
                "prompt_id": prompt_id,
                "version": version.version,
                "content": version.content,
                "updated_at": datetime.now().isoformat()
            }, f, indent=2)
            
    def _load_active_prompts(self):
        """Load all active prompts into cache"""
        # Load system prompts
        for prompt_file in self.system_prompts_path.glob("*.json"):
            self._load_active_prompt(prompt_file)
            
        # Load user prompts
        for prompt_file in self.user_prompts_path.glob("*.json"):
            self._load_active_prompt(prompt_file)
            
    def _load_active_prompt(self, file_path: Path):
        """Load an active prompt from file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            prompt_id = data["prompt_id"]
            version_number = data["version"]
            
            version = self.get_version(prompt_id, version_number)
            if version:
                self._active_prompts[prompt_id] = version
        except Exception as e:
            logger.error(f"Error loading active prompt from {file_path}: {e}")
            
    def _version_to_dict(self, version: PromptVersion) -> Dict[str, Any]:
        """Convert PromptVersion to dictionary"""
        return {
            "id": version.id,
            "prompt_id": version.prompt_id,
            "version": version.version,
            "content": version.content,
            "metadata": version.metadata,
            "avg_rating": version.avg_rating,
            "success_rate": version.success_rate,
            "error_rate": version.error_rate,
            "usage_count": version.usage_count,
            "parent_version_id": version.parent_version_id,
            "training_data_ids": version.training_data_ids,
            "training_params": version.training_params,
            "created_at": version.created_at.isoformat(),
            "deployed_at": version.deployed_at.isoformat() if version.deployed_at else None,
            "retired_at": version.retired_at.isoformat() if version.retired_at else None,
            "is_active": version.is_active,
            "is_experimental": version.is_experimental
        }
        
    def _dict_to_version(self, data: Dict[str, Any]) -> PromptVersion:
        """Convert dictionary to PromptVersion"""
        return PromptVersion(
            id=data["id"],
            prompt_id=data["prompt_id"],
            version=data["version"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            avg_rating=data.get("avg_rating", 0.0),
            success_rate=data.get("success_rate", 0.0),
            error_rate=data.get("error_rate", 0.0),
            usage_count=data.get("usage_count", 0),
            parent_version_id=data.get("parent_version_id"),
            training_data_ids=data.get("training_data_ids", []),
            training_params=data.get("training_params", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            deployed_at=datetime.fromisoformat(data["deployed_at"]) if data.get("deployed_at") else None,
            retired_at=datetime.fromisoformat(data["retired_at"]) if data.get("retired_at") else None,
            is_active=data.get("is_active", False),
            is_experimental=data.get("is_experimental", True)
        )