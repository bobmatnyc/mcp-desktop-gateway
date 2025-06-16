"""Simple Adaptive Manager for py-mcp-bridge"""
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

class SimpleAdaptiveManager:
    def __init__(self, db_path: str = "prompt_performance.db"):
        self.db_path = db_path
    
    async def execute_adaptive_prompt(self, connector_name: str, prompt_name: str, 
                                    arguments: Dict[str, Any], user_context: Dict[str, Any],
                                    base_prompt_func):
        execution_id = str(uuid.uuid4())
        
        try:
            result = await base_prompt_func(prompt_name, arguments)
            
            # Record execution
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prompt_executions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id, connector_name, prompt_name, "v1.0",
                json.dumps(arguments), result.content, datetime.now().isoformat(),
                json.dumps(user_context), json.dumps({"success": True})
            ))
            conn.commit()
            conn.close()
            
            # Add feedback UI
            result.content += f"""

---
**📝 Rate this response:** (ID: {execution_id[-8:]})
👍 Good  |  👎 Poor  |  ⭐ Rate 1-5  |  💬 Comments
*Use: feedback {execution_id[-8:]} [thumbs_up|thumbs_down|rating X|text "comment"]*
"""
            result.metadata["execution_id"] = execution_id
            return result, execution_id
            
        except Exception as e:
            print(f"Adaptive prompt error: {e}")
            raise
    
    def record_feedback(self, execution_id: str, feedback_type: str, rating: Optional[int] = None, text: Optional[str] = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_feedback (feedback_id, execution_id, feedback_type, rating, text_feedback, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), execution_id, feedback_type, rating, text, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return f"✅ Feedback recorded for {execution_id[-8:]}"

# Global instance
adaptive_manager = SimpleAdaptiveManager()
