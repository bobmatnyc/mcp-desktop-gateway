"""
Prompt evaluation and testing framework
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging
from pathlib import Path
import statistics

from langchain.evaluation import load_evaluator, EvaluatorType
from langchain.evaluation.criteria import CriteriaEvalChain
from langchain.chat_models import ChatOpenAI
from langchain.callbacks import get_openai_callback

from .models import PromptVersion, EvaluationResult
from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class PromptEvaluator:
    """Evaluates prompt versions using various metrics and tests"""
    
    def __init__(
        self,
        prompt_manager: PromptManager,
        openai_api_key: Optional[str] = None,
        model_name: str = "gpt-4"
    ):
        self.prompt_manager = prompt_manager
        self.model_name = model_name
        
        # Initialize LLM for evaluation
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.0,  # Deterministic for evaluation
            openai_api_key=openai_api_key
        )
        
        # Initialize evaluators
        self._init_evaluators()
        
        # Test suites storage
        self.test_suites_path = Path("prompt_training/evaluation/test_suites")
        self.test_suites_path.mkdir(parents=True, exist_ok=True)
        
    def _init_evaluators(self):
        """Initialize LangChain evaluators"""
        # Criteria-based evaluator
        self.criteria_evaluator = load_evaluator(
            EvaluatorType.CRITERIA,
            llm=self.llm,
            criteria="helpfulness"
        )
        
        # Custom criteria evaluators
        self.custom_evaluators = {
            "clarity": CriteriaEvalChain.from_llm(
                llm=self.llm,
                criteria={
                    "clarity": "Is the output clear and easy to understand?"
                }
            ),
            "completeness": CriteriaEvalChain.from_llm(
                llm=self.llm,
                criteria={
                    "completeness": "Does the output fully address the input request?"
                }
            ),
            "safety": CriteriaEvalChain.from_llm(
                llm=self.llm,
                criteria={
                    "safety": "Is the output safe and free from harmful content?"
                }
            )
        }
        
    async def evaluate_version(
        self,
        prompt_version: PromptVersion,
        test_suite_name: Optional[str] = None,
        baseline_version: Optional[PromptVersion] = None,
        num_runs: int = 3
    ) -> EvaluationResult:
        """Comprehensively evaluate a prompt version"""
        logger.info(f"Evaluating prompt {prompt_version.prompt_id} v{prompt_version.version}")
        
        # Load or generate test suite
        test_cases = await self._load_test_suite(
            prompt_version.prompt_id,
            test_suite_name
        )
        
        # Run evaluation
        evaluation_start = datetime.now()
        
        # Execute test cases
        test_results = await self._run_test_cases(
            prompt_version,
            test_cases,
            num_runs
        )
        
        # Calculate metrics
        metrics = self._calculate_metrics(test_results)
        
        # Compare with baseline if provided
        improvement_delta = {}
        if baseline_version:
            baseline_results = await self._run_test_cases(
                baseline_version,
                test_cases,
                num_runs
            )
            baseline_metrics = self._calculate_metrics(baseline_results)
            improvement_delta = self._calculate_improvement(metrics, baseline_metrics)
            
        # Generate recommendation
        recommendation, confidence = self._generate_recommendation(
            metrics,
            improvement_delta,
            test_results
        )
        
        # Create evaluation result
        result = EvaluationResult(
            prompt_version_id=prompt_version.id,
            evaluated_at=evaluation_start,
            test_cases_passed=metrics["passed"],
            test_cases_total=metrics["total"],
            latency_p50=metrics["latency_p50"],
            latency_p95=metrics["latency_p95"],
            token_usage_avg=metrics["token_usage_avg"],
            coherence_score=metrics["coherence_score"],
            relevance_score=metrics["relevance_score"],
            safety_score=metrics["safety_score"],
            baseline_version_id=baseline_version.id if baseline_version else None,
            improvement_delta=improvement_delta,
            recommendation=recommendation,
            confidence=confidence,
            notes=self._generate_notes(metrics, test_results)
        )
        
        # Save evaluation result
        await self._save_evaluation_result(result)
        
        logger.info(f"Evaluation complete. Recommendation: {recommendation} (confidence: {confidence:.2f})")
        return result
        
    async def create_test_suite(
        self,
        prompt_id: str,
        suite_name: str,
        test_cases: List[Dict[str, Any]]
    ):
        """Create a test suite for a prompt"""
        suite_path = self.test_suites_path / prompt_id / f"{suite_name}.json"
        suite_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate test cases
        validated_cases = []
        for case in test_cases:
            validated_case = {
                "id": case.get("id", f"test_{len(validated_cases) + 1}"),
                "description": case.get("description", ""),
                "input": case["input"],  # Required
                "expected_output": case.get("expected_output"),
                "expected_behavior": case.get("expected_behavior", []),
                "tags": case.get("tags", []),
                "weight": case.get("weight", 1.0)
            }
            validated_cases.append(validated_case)
            
        # Save test suite
        with open(suite_path, 'w') as f:
            json.dump({
                "prompt_id": prompt_id,
                "suite_name": suite_name,
                "created_at": datetime.now().isoformat(),
                "test_cases": validated_cases
            }, f, indent=2)
            
        logger.info(f"Created test suite '{suite_name}' with {len(validated_cases)} test cases")
        
    async def run_a_b_test(
        self,
        version_a: PromptVersion,
        version_b: PromptVersion,
        test_duration_hours: int = 24,
        traffic_split: float = 0.5
    ) -> Dict[str, Any]:
        """Run A/B test between two prompt versions"""
        logger.info(f"Starting A/B test: v{version_a.version} vs v{version_b.version}")
        
        # This is a simplified A/B test framework
        # In production, this would integrate with the actual system
        
        test_id = f"ab_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create A/B test configuration
        ab_config = {
            "test_id": test_id,
            "version_a": {
                "id": version_a.id,
                "version": version_a.version
            },
            "version_b": {
                "id": version_b.id,
                "version": version_b.version
            },
            "started_at": datetime.now().isoformat(),
            "duration_hours": test_duration_hours,
            "traffic_split": traffic_split,
            "status": "running"
        }
        
        # In a real implementation, this would:
        # 1. Configure the system to route traffic
        # 2. Collect metrics during the test period
        # 3. Analyze results after completion
        
        # For now, return the configuration
        return ab_config
        
    async def _load_test_suite(
        self,
        prompt_id: str,
        suite_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Load test suite for evaluation"""
        if suite_name:
            suite_path = self.test_suites_path / prompt_id / f"{suite_name}.json"
            if suite_path.exists():
                with open(suite_path, 'r') as f:
                    data = json.load(f)
                    return data["test_cases"]
                    
        # Generate default test cases if no suite specified
        return self._generate_default_test_cases(prompt_id)
        
    def _generate_default_test_cases(self, prompt_id: str) -> List[Dict[str, Any]]:
        """Generate default test cases for a prompt"""
        # Basic test cases that apply to most prompts
        return [
            {
                "id": "test_basic",
                "description": "Basic functionality test",
                "input": {"query": "test"},
                "expected_behavior": ["responds", "coherent"]
            },
            {
                "id": "test_empty",
                "description": "Empty input handling",
                "input": {"query": ""},
                "expected_behavior": ["handles_gracefully", "no_error"]
            },
            {
                "id": "test_long",
                "description": "Long input handling",
                "input": {"query": "x" * 1000},
                "expected_behavior": ["handles_length", "maintains_performance"]
            }
        ]
        
    async def _run_test_cases(
        self,
        prompt_version: PromptVersion,
        test_cases: List[Dict[str, Any]],
        num_runs: int
    ) -> List[Dict[str, Any]]:
        """Execute test cases against a prompt version"""
        results = []
        
        for test_case in test_cases:
            test_result = {
                "test_id": test_case["id"],
                "description": test_case["description"],
                "runs": []
            }
            
            # Run each test case multiple times
            for run_idx in range(num_runs):
                run_start = datetime.now()
                
                try:
                    # Execute prompt with test input
                    with get_openai_callback() as cb:
                        # Simulate prompt execution
                        # In production, this would use the actual prompt
                        output = await self._execute_prompt(
                            prompt_version.content,
                            test_case["input"]
                        )
                        
                        run_time = (datetime.now() - run_start).total_seconds()
                        
                        run_result = {
                            "run_index": run_idx,
                            "success": True,
                            "output": output,
                            "latency": run_time,
                            "tokens": cb.total_tokens,
                            "cost": cb.total_cost
                        }
                        
                    # Evaluate output
                    if test_case.get("expected_output"):
                        run_result["exact_match"] = output == test_case["expected_output"]
                        
                    # Evaluate behaviors
                    if test_case.get("expected_behavior"):
                        behavior_scores = await self._evaluate_behaviors(
                            output,
                            test_case["expected_behavior"]
                        )
                        run_result["behavior_scores"] = behavior_scores
                        
                    # Evaluate quality metrics
                    quality_scores = await self._evaluate_quality(
                        test_case["input"],
                        output
                    )
                    run_result["quality_scores"] = quality_scores
                    
                except Exception as e:
                    run_result = {
                        "run_index": run_idx,
                        "success": False,
                        "error": str(e),
                        "latency": (datetime.now() - run_start).total_seconds()
                    }
                    
                test_result["runs"].append(run_result)
                
            results.append(test_result)
            
        return results
        
    async def _execute_prompt(
        self,
        prompt_content: str,
        test_input: Dict[str, Any]
    ) -> str:
        """Execute a prompt with test input"""
        # This is a simplified execution
        # In production, this would use the actual prompt template
        
        messages = [
            {"role": "system", "content": prompt_content},
            {"role": "user", "content": json.dumps(test_input)}
        ]
        
        response = await self.llm.apredict_messages(messages)
        return response.content
        
    async def _evaluate_behaviors(
        self,
        output: str,
        expected_behaviors: List[str]
    ) -> Dict[str, float]:
        """Evaluate if output exhibits expected behaviors"""
        scores = {}
        
        for behavior in expected_behaviors:
            # Use LLM to evaluate behavior
            evaluator = CriteriaEvalChain.from_llm(
                llm=self.llm,
                criteria={behavior: f"Does the output exhibit '{behavior}' behavior?"}
            )
            
            result = evaluator.evaluate_strings(
                prediction=output,
                input=behavior
            )
            
            scores[behavior] = result.get("score", 0.0)
            
        return scores
        
    async def _evaluate_quality(
        self,
        input_data: Dict[str, Any],
        output: str
    ) -> Dict[str, float]:
        """Evaluate output quality metrics"""
        scores = {}
        
        # Evaluate using custom evaluators
        for metric_name, evaluator in self.custom_evaluators.items():
            try:
                result = evaluator.evaluate_strings(
                    prediction=output,
                    input=json.dumps(input_data)
                )
                scores[metric_name] = result.get("score", 0.0)
            except Exception as e:
                logger.error(f"Error evaluating {metric_name}: {e}")
                scores[metric_name] = 0.0
                
        return scores
        
    def _calculate_metrics(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aggregate metrics from test results"""
        all_latencies = []
        all_tokens = []
        all_quality_scores = {"clarity": [], "completeness": [], "safety": []}
        passed_count = 0
        total_count = 0
        
        for test_result in test_results:
            for run in test_result["runs"]:
                total_count += 1
                
                if run.get("success", False):
                    passed_count += 1
                    all_latencies.append(run.get("latency", 0))
                    all_tokens.append(run.get("tokens", 0))
                    
                    # Collect quality scores
                    quality = run.get("quality_scores", {})
                    for metric in all_quality_scores:
                        if metric in quality:
                            all_quality_scores[metric].append(quality[metric])
                            
        # Calculate percentiles and averages
        metrics = {
            "passed": passed_count,
            "total": total_count,
            "success_rate": passed_count / total_count if total_count > 0 else 0,
            "latency_p50": statistics.median(all_latencies) if all_latencies else 0,
            "latency_p95": self._percentile(all_latencies, 0.95) if all_latencies else 0,
            "token_usage_avg": statistics.mean(all_tokens) if all_tokens else 0,
            "coherence_score": statistics.mean(all_quality_scores["clarity"]) if all_quality_scores["clarity"] else 0,
            "relevance_score": statistics.mean(all_quality_scores["completeness"]) if all_quality_scores["completeness"] else 0,
            "safety_score": statistics.mean(all_quality_scores["safety"]) if all_quality_scores["safety"] else 0
        }
        
        return metrics
        
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of a list"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]
        
    def _calculate_improvement(
        self,
        new_metrics: Dict[str, Any],
        baseline_metrics: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate improvement between versions"""
        improvement = {}
        
        # Calculate deltas for key metrics
        for metric in ["success_rate", "latency_p50", "coherence_score", "relevance_score", "safety_score"]:
            if metric in new_metrics and metric in baseline_metrics:
                baseline_val = baseline_metrics[metric]
                new_val = new_metrics[metric]
                
                if baseline_val > 0:
                    # For latency, lower is better
                    if metric == "latency_p50":
                        delta = (baseline_val - new_val) / baseline_val
                    else:
                        delta = (new_val - baseline_val) / baseline_val
                    improvement[f"{metric}_delta"] = delta
                    
        return improvement
        
    def _generate_recommendation(
        self,
        metrics: Dict[str, Any],
        improvement_delta: Dict[str, float],
        test_results: List[Dict[str, Any]]
    ) -> Tuple[str, float]:
        """Generate deployment recommendation"""
        # Decision logic based on metrics and improvements
        
        confidence = 0.5  # Base confidence
        
        # Check success rate
        if metrics["success_rate"] < 0.8:
            return "reject", 0.9
            
        # Check safety
        if metrics["safety_score"] < 0.8:
            return "hold", 0.8
            
        # If we have improvement data
        if improvement_delta:
            avg_improvement = statistics.mean(improvement_delta.values())
            
            if avg_improvement > 0.1:  # 10% improvement
                confidence = min(0.9, 0.5 + avg_improvement)
                return "deploy", confidence
            elif avg_improvement > 0:
                return "test_more", 0.6
            else:
                return "hold", 0.7
                
        # No baseline comparison
        if metrics["success_rate"] > 0.9 and metrics["safety_score"] > 0.9:
            return "deploy", 0.7
        else:
            return "test_more", 0.5
            
    def _generate_notes(
        self,
        metrics: Dict[str, Any],
        test_results: List[Dict[str, Any]]
    ) -> str:
        """Generate evaluation notes"""
        notes = []
        
        # Note any concerning metrics
        if metrics["success_rate"] < 0.8:
            notes.append(f"Low success rate: {metrics['success_rate']:.1%}")
            
        if metrics["latency_p95"] > 5.0:
            notes.append(f"High latency detected: p95={metrics['latency_p95']:.1f}s")
            
        if metrics["safety_score"] < 0.9:
            notes.append(f"Safety concerns: score={metrics['safety_score']:.2f}")
            
        # Note any test failures
        failures = []
        for test_result in test_results:
            failed_runs = [r for r in test_result["runs"] if not r.get("success", False)]
            if failed_runs:
                failures.append(f"{test_result['test_id']}: {len(failed_runs)} failures")
                
        if failures:
            notes.append(f"Test failures: {', '.join(failures[:3])}")
            
        return "; ".join(notes) if notes else "All metrics within acceptable ranges"
        
    async def _save_evaluation_result(self, result: EvaluationResult):
        """Save evaluation result to disk"""
        result_dir = Path("prompt_training/evaluation/results")
        result_dir.mkdir(parents=True, exist_ok=True)
        
        result_file = result_dir / f"{result.prompt_version_id}_{result.id}.json"
        
        with open(result_file, 'w') as f:
            json.dump({
                "id": result.id,
                "prompt_version_id": result.prompt_version_id,
                "evaluated_at": result.evaluated_at.isoformat(),
                "test_cases_passed": result.test_cases_passed,
                "test_cases_total": result.test_cases_total,
                "latency_p50": result.latency_p50,
                "latency_p95": result.latency_p95,
                "token_usage_avg": result.token_usage_avg,
                "coherence_score": result.coherence_score,
                "relevance_score": result.relevance_score,
                "safety_score": result.safety_score,
                "baseline_version_id": result.baseline_version_id,
                "improvement_delta": result.improvement_delta,
                "recommendation": result.recommendation,
                "confidence": result.confidence,
                "notes": result.notes
            }, f, indent=2)