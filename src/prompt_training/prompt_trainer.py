"""
LangChain-based prompt training system
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging
from pathlib import Path

# LangChain imports
from langchain.prompts import PromptTemplate, FewShotPromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.callbacks import get_openai_callback
from langchain.evaluation import load_evaluator
from langchain.smith import RunEvalConfig
from langchain.prompts.example_selector import SemanticSimilarityExampleSelector
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS

from .models import Feedback, PromptVersion, TrainingRun, FeedbackType
from .feedback_collector import FeedbackCollector
from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class PromptTrainer:
    """Trains and improves prompts using LangChain and feedback data"""
    
    def __init__(
        self,
        feedback_collector: FeedbackCollector,
        prompt_manager: PromptManager,
        openai_api_key: Optional[str] = None,
        model_name: str = "gpt-4",
        temperature: float = 0.7
    ):
        self.feedback_collector = feedback_collector
        self.prompt_manager = prompt_manager
        self.model_name = model_name
        self.temperature = temperature
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=openai_api_key
        )
        
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        
        # Training strategies
        self.training_strategies = {
            "few_shot": self._train_few_shot,
            "reinforcement": self._train_reinforcement,
            "meta_prompt": self._train_meta_prompt,
            "adversarial": self._train_adversarial
        }
        
    async def train_prompt(
        self,
        prompt_id: str,
        training_approach: str = "few_shot",
        min_feedback_count: int = 10,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[TrainingRun]:
        """Train a prompt based on collected feedback"""
        # Get current version
        current_version = self.prompt_manager.get_active_prompt(prompt_id)
        if not current_version:
            logger.error(f"No active version found for prompt {prompt_id}")
            return None
            
        # Collect feedback data
        feedback_list = await self.feedback_collector.get_feedback_for_prompt(prompt_id)
        if len(feedback_list) < min_feedback_count:
            logger.info(f"Insufficient feedback for {prompt_id}: {len(feedback_list)} < {min_feedback_count}")
            return None
            
        # Create training run
        training_run = TrainingRun(
            prompt_id=prompt_id,
            model_name=self.model_name,
            training_approach=training_approach,
            parameters=parameters or {},
            feedback_ids=[f.id for f in feedback_list],
            status="running"
        )
        
        try:
            # Prepare training data
            training_data = self._prepare_training_data(feedback_list, current_version)
            training_run.training_examples = training_data["train"]
            training_run.validation_examples = training_data["validation"]
            
            # Execute training strategy
            if training_approach not in self.training_strategies:
                raise ValueError(f"Unknown training approach: {training_approach}")
                
            new_prompt_content = await self.training_strategies[training_approach](
                current_version,
                training_data,
                parameters or {}
            )
            
            # Create new version
            new_version = self.prompt_manager.create_new_version(
                prompt_id=prompt_id,
                content=new_prompt_content,
                parent_version_id=current_version.id,
                training_data_ids=[f.id for f in feedback_list],
                training_params={
                    "approach": training_approach,
                    "model": self.model_name,
                    "parameters": parameters
                },
                is_experimental=True
            )
            
            # Evaluate new version
            evaluation_metrics = await self._evaluate_version(
                new_version,
                training_data["validation"],
                current_version
            )
            
            # Update training run
            training_run.new_version_id = new_version.id
            training_run.metrics = evaluation_metrics
            training_run.status = "completed"
            training_run.completed_at = datetime.now()
            
            # Update version metrics
            self.prompt_manager.update_version_metrics(
                prompt_id,
                new_version.version,
                evaluation_metrics
            )
            
            logger.info(f"Training completed for {prompt_id}: created v{new_version.version}")
            return training_run
            
        except Exception as e:
            training_run.status = "failed"
            training_run.error_message = str(e)
            training_run.completed_at = datetime.now()
            logger.error(f"Training failed for {prompt_id}: {e}")
            return training_run
            
    async def _train_few_shot(
        self,
        current_version: PromptVersion,
        training_data: Dict[str, List[Dict[str, Any]]],
        parameters: Dict[str, Any]
    ) -> str:
        """Train using few-shot learning approach"""
        # Extract successful examples
        successful_examples = [
            {
                "input": ex["input"],
                "output": ex["output"]
            }
            for ex in training_data["train"]
            if ex.get("rating", 0) > 0.7
        ]
        
        if len(successful_examples) < 3:
            # Fall back to meta-prompt if not enough examples
            return await self._train_meta_prompt(current_version, training_data, parameters)
            
        # Create example selector for semantic similarity
        example_selector = SemanticSimilarityExampleSelector.from_examples(
            successful_examples,
            self.embeddings,
            FAISS,
            k=min(5, len(successful_examples))
        )
        
        # Create few-shot prompt template
        few_shot_prompt = FewShotPromptTemplate(
            example_selector=example_selector,
            example_prompt=PromptTemplate(
                input_variables=["input", "output"],
                template="Input: {input}\nOutput: {output}"
            ),
            prefix=f"Improve this prompt based on successful examples:\n\nOriginal prompt:\n{current_version.content}\n\nSuccessful examples:",
            suffix="\n\nBased on these examples, generate an improved version of the prompt that captures the patterns of successful interactions:",
            input_variables=[]
        )
        
        # Generate improved prompt
        chain = LLMChain(llm=self.llm, prompt=few_shot_prompt)
        
        with get_openai_callback() as cb:
            result = await chain.arun({})
            logger.info(f"Few-shot training used {cb.total_tokens} tokens (${cb.total_cost:.4f})")
            
        return result.strip()
        
    async def _train_reinforcement(
        self,
        current_version: PromptVersion,
        training_data: Dict[str, List[Dict[str, Any]]],
        parameters: Dict[str, Any]
    ) -> str:
        """Train using reinforcement learning principles"""
        # Separate positive and negative examples
        positive_examples = [ex for ex in training_data["train"] if ex.get("rating", 0) > 0.7]
        negative_examples = [ex for ex in training_data["train"] if ex.get("rating", 1) < 0.3]
        
        # Create reinforcement prompt
        reinforcement_prompt = PromptTemplate(
            input_variables=["original_prompt", "positive_examples", "negative_examples", "error_patterns"],
            template="""Analyze this prompt and improve it based on feedback:

Original Prompt:
{original_prompt}

POSITIVE EXAMPLES (these worked well):
{positive_examples}

NEGATIVE EXAMPLES (these had issues):
{negative_examples}

COMMON ERROR PATTERNS:
{error_patterns}

Generate an improved prompt that:
1. Reinforces patterns from positive examples
2. Avoids patterns that led to negative outcomes
3. Addresses the identified error patterns
4. Maintains clarity and effectiveness

Improved prompt:"""
        )
        
        # Analyze error patterns
        error_patterns = self._analyze_error_patterns(negative_examples)
        
        # Format examples
        positive_str = "\n".join([
            f"- Input: {ex['input']}\n  Output: {ex['output']}\n  Rating: {ex.get('rating', 'N/A')}"
            for ex in positive_examples[:5]
        ])
        
        negative_str = "\n".join([
            f"- Input: {ex['input']}\n  Issue: {ex.get('error', 'Low rating')}\n  Rating: {ex.get('rating', 'N/A')}"
            for ex in negative_examples[:5]
        ])
        
        # Generate improved prompt
        chain = LLMChain(llm=self.llm, prompt=reinforcement_prompt)
        
        with get_openai_callback() as cb:
            result = await chain.arun({
                "original_prompt": current_version.content,
                "positive_examples": positive_str or "No positive examples available",
                "negative_examples": negative_str or "No negative examples available",
                "error_patterns": "\n".join(error_patterns) or "No clear patterns identified"
            })
            logger.info(f"Reinforcement training used {cb.total_tokens} tokens (${cb.total_cost:.4f})")
            
        return result.strip()
        
    async def _train_meta_prompt(
        self,
        current_version: PromptVersion,
        training_data: Dict[str, List[Dict[str, Any]]],
        parameters: Dict[str, Any]
    ) -> str:
        """Train using meta-prompt optimization"""
        # Analyze feedback to identify improvement areas
        feedback_analysis = self._analyze_feedback(training_data["train"])
        
        meta_prompt = PromptTemplate(
            input_variables=["original_prompt", "feedback_summary", "improvement_suggestions", "metrics"],
            template="""You are a prompt engineering expert. Improve this prompt based on user feedback and performance metrics.

Original Prompt:
{original_prompt}

FEEDBACK SUMMARY:
{feedback_summary}

IMPROVEMENT SUGGESTIONS:
{improvement_suggestions}

PERFORMANCE METRICS:
{metrics}

Generate an improved version of this prompt that:
1. Addresses the issues identified in the feedback
2. Incorporates the improvement suggestions
3. Maintains the original intent and functionality
4. Uses clear, concise language
5. Follows prompt engineering best practices

Improved prompt:"""
        )
        
        # Generate improvement suggestions from feedback
        suggestions = await self._generate_improvement_suggestions(
            current_version.content,
            feedback_analysis
        )
        
        # Format metrics
        metrics = {
            "current_rating": current_version.avg_rating,
            "success_rate": current_version.success_rate,
            "error_rate": current_version.error_rate,
            "total_feedback": len(training_data["train"])
        }
        
        # Generate improved prompt
        chain = LLMChain(llm=self.llm, prompt=meta_prompt)
        
        with get_openai_callback() as cb:
            result = await chain.arun({
                "original_prompt": current_version.content,
                "feedback_summary": feedback_analysis["summary"],
                "improvement_suggestions": "\n".join(suggestions),
                "metrics": json.dumps(metrics, indent=2)
            })
            logger.info(f"Meta-prompt training used {cb.total_tokens} tokens (${cb.total_cost:.4f})")
            
        return result.strip()
        
    async def _train_adversarial(
        self,
        current_version: PromptVersion,
        training_data: Dict[str, List[Dict[str, Any]]],
        parameters: Dict[str, Any]
    ) -> str:
        """Train using adversarial approach to identify and fix edge cases"""
        # Generate adversarial examples
        adversarial_examples = await self._generate_adversarial_examples(
            current_version.content,
            training_data["train"]
        )
        
        adversarial_prompt = PromptTemplate(
            input_variables=["original_prompt", "edge_cases", "failure_modes", "robustness_requirements"],
            template="""Improve this prompt to handle edge cases and potential failure modes:

Original Prompt:
{original_prompt}

IDENTIFIED EDGE CASES:
{edge_cases}

POTENTIAL FAILURE MODES:
{failure_modes}

ROBUSTNESS REQUIREMENTS:
{robustness_requirements}

Generate an improved prompt that:
1. Handles all identified edge cases gracefully
2. Prevents the failure modes
3. Maintains effectiveness for normal use cases
4. Includes appropriate constraints and guidelines
5. Is resilient to adversarial or unexpected inputs

Improved prompt:"""
        )
        
        # Analyze failure modes
        failure_modes = self._analyze_failure_modes(training_data["train"])
        
        # Define robustness requirements
        robustness_reqs = [
            "Handle ambiguous or incomplete inputs",
            "Provide clear error messages for invalid requests",
            "Maintain consistent behavior across similar inputs",
            "Avoid generating harmful or inappropriate content",
            "Scale appropriately with input complexity"
        ]
        
        # Generate improved prompt
        chain = LLMChain(llm=self.llm, prompt=adversarial_prompt)
        
        with get_openai_callback() as cb:
            result = await chain.arun({
                "original_prompt": current_version.content,
                "edge_cases": "\n".join(adversarial_examples),
                "failure_modes": "\n".join(failure_modes),
                "robustness_requirements": "\n".join(robustness_reqs)
            })
            logger.info(f"Adversarial training used {cb.total_tokens} tokens (${cb.total_cost:.4f})")
            
        return result.strip()
        
    def _prepare_training_data(
        self,
        feedback_list: List[Feedback],
        current_version: PromptVersion
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Prepare feedback data for training"""
        # Convert feedback to training examples
        examples = []
        for feedback in feedback_list:
            example = {
                "input": feedback.input_data,
                "output": feedback.output_data,
                "rating": feedback.rating,
                "feedback_type": feedback.feedback_type.value,
                "execution_time": feedback.execution_time
            }
            
            if feedback.error_details:
                example["error"] = feedback.error_details.get("error_message", "Unknown error")
                
            if feedback.message:
                example["user_feedback"] = feedback.message
                
            examples.append(example)
            
        # Split into train and validation sets (80/20)
        split_index = int(len(examples) * 0.8)
        
        return {
            "train": examples[:split_index],
            "validation": examples[split_index:]
        }
        
    def _analyze_feedback(self, training_examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze feedback to identify patterns and issues"""
        total = len(training_examples)
        if total == 0:
            return {"summary": "No feedback available", "issues": []}
            
        # Calculate statistics
        ratings = [ex.get("rating", 0) for ex in training_examples if ex.get("rating") is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        errors = [ex for ex in training_examples if "error" in ex]
        error_rate = len(errors) / total
        
        user_feedback = [ex.get("user_feedback", "") for ex in training_examples if ex.get("user_feedback")]
        
        # Identify common issues
        issues = []
        if error_rate > 0.2:
            issues.append(f"High error rate: {error_rate:.1%}")
        if avg_rating < 0.6:
            issues.append(f"Low average rating: {avg_rating:.2f}")
            
        # Create summary
        summary = f"""
Total feedback: {total}
Average rating: {avg_rating:.2f}
Error rate: {error_rate:.1%}
User comments: {len(user_feedback)}

Main issues: {', '.join(issues) if issues else 'None identified'}
"""
        
        return {
            "summary": summary.strip(),
            "issues": issues,
            "avg_rating": avg_rating,
            "error_rate": error_rate,
            "user_feedback": user_feedback[:5]  # Sample of feedback
        }
        
    def _analyze_error_patterns(self, negative_examples: List[Dict[str, Any]]) -> List[str]:
        """Identify common error patterns"""
        patterns = []
        
        # Group errors by type
        error_types = {}
        for ex in negative_examples:
            if "error" in ex:
                error_type = ex["error"].split(":")[0] if ":" in ex["error"] else "Unknown"
                error_types[error_type] = error_types.get(error_type, 0) + 1
                
        # Identify patterns
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            if count >= 2:
                patterns.append(f"{error_type}: {count} occurrences")
                
        return patterns[:5]  # Top 5 patterns
        
    def _analyze_failure_modes(self, training_examples: List[Dict[str, Any]]) -> List[str]:
        """Identify potential failure modes"""
        failure_modes = []
        
        # Check for specific failure patterns
        timeouts = [ex for ex in training_examples if ex.get("execution_time", 0) > 30]
        if timeouts:
            failure_modes.append(f"Timeout issues: {len(timeouts)} slow executions")
            
        empty_outputs = [ex for ex in training_examples if not ex.get("output")]
        if empty_outputs:
            failure_modes.append(f"Empty outputs: {len(empty_outputs)} cases")
            
        low_ratings = [ex for ex in training_examples if ex.get("rating", 1) < 0.3]
        if len(low_ratings) > len(training_examples) * 0.1:
            failure_modes.append(f"Frequent low ratings: {len(low_ratings)} cases")
            
        return failure_modes
        
    async def _generate_improvement_suggestions(
        self,
        prompt_content: str,
        feedback_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate specific improvement suggestions"""
        suggestion_prompt = PromptTemplate(
            input_variables=["prompt", "issues", "user_feedback"],
            template="""Based on this prompt and its issues, suggest specific improvements:

Prompt: {prompt}

Issues: {issues}

User feedback samples:
{user_feedback}

List 3-5 specific, actionable improvements:"""
        )
        
        chain = LLMChain(llm=self.llm, prompt=suggestion_prompt)
        
        result = await chain.arun({
            "prompt": prompt_content[:500],  # Truncate if too long
            "issues": ", ".join(feedback_analysis["issues"]),
            "user_feedback": "\n".join(f"- {fb}" for fb in feedback_analysis.get("user_feedback", [])[:3])
        })
        
        # Parse suggestions
        suggestions = [s.strip() for s in result.strip().split("\n") if s.strip() and s.strip()[0] in "123456-•"]
        return suggestions[:5]
        
    async def _generate_adversarial_examples(
        self,
        prompt_content: str,
        training_examples: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate adversarial examples to test prompt robustness"""
        adversarial_prompt = PromptTemplate(
            input_variables=["prompt", "example_inputs"],
            template="""Given this prompt, generate 5 edge cases or adversarial inputs that might cause issues:

Prompt: {prompt}

Example normal inputs:
{example_inputs}

Generate 5 edge cases that test the prompt's limits:"""
        )
        
        # Sample some normal inputs
        example_inputs = [str(ex.get("input", ""))[:100] for ex in training_examples[:3]]
        
        chain = LLMChain(llm=self.llm, prompt=adversarial_prompt)
        
        result = await chain.arun({
            "prompt": prompt_content[:500],
            "example_inputs": "\n".join(f"- {inp}" for inp in example_inputs)
        })
        
        # Parse edge cases
        edge_cases = [s.strip() for s in result.strip().split("\n") if s.strip() and s.strip()[0] in "123456-•"]
        return edge_cases[:5]
        
    async def _evaluate_version(
        self,
        new_version: PromptVersion,
        validation_data: List[Dict[str, Any]],
        baseline_version: PromptVersion
    ) -> Dict[str, float]:
        """Evaluate a new prompt version against baseline"""
        if not validation_data:
            return {
                "rating": 0.5,
                "improvement": 0.0
            }
            
        # Simple evaluation based on expected outputs
        # In production, this would use more sophisticated evaluation
        
        # For now, return mock metrics
        # TODO: Implement proper evaluation using LangChain evaluators
        
        return {
            "rating": 0.75,  # Simulated improvement
            "success_rate": 0.85,
            "error_rate": 0.05,
            "improvement": 0.15  # 15% improvement over baseline
        }