#!/usr/bin/env python3
"""
Command-line interface for prompt training system
"""

import asyncio
import click
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from .feedback_collector import FeedbackCollector
from .prompt_manager import PromptManager
from .prompt_trainer import PromptTrainer
from .evaluation import PromptEvaluator
from .auto_trainer import AutomaticPromptTrainer
from .models import PromptType, FeedbackType


@click.group()
def cli():
    """MCP Desktop Gateway Prompt Training System"""
    pass


@cli.group()
def prompt():
    """Manage prompts and versions"""
    pass


@prompt.command()
@click.argument('prompt_id')
@click.argument('prompt_file', type=click.Path(exists=True))
@click.option('--type', 'prompt_type', type=click.Choice(['system', 'user']), default='user')
@click.option('--metadata', type=str, help='JSON metadata')
def create(prompt_id: str, prompt_file: str, prompt_type: str, metadata: Optional[str]):
    """Create a new prompt"""
    manager = PromptManager()
    
    with open(prompt_file, 'r') as f:
        content = f.read()
        
    meta = json.loads(metadata) if metadata else {}
    
    version = manager.create_prompt(
        prompt_id=prompt_id,
        prompt_type=PromptType(prompt_type),
        content=content,
        metadata=meta
    )
    
    click.echo(f"Created prompt {prompt_id} v{version.version}")


@prompt.command()
@click.argument('prompt_id')
def show(prompt_id: str):
    """Show active prompt version"""
    manager = PromptManager()
    version = manager.get_active_prompt(prompt_id)
    
    if not version:
        click.echo(f"No active version found for {prompt_id}")
        return
        
    click.echo(f"\nPrompt: {prompt_id}")
    click.echo(f"Version: {version.version}")
    click.echo(f"Created: {version.created_at}")
    click.echo(f"Deployed: {version.deployed_at or 'Not deployed'}")
    click.echo(f"\nContent:\n{version.content}")
    click.echo(f"\nMetrics:")
    click.echo(f"  Average Rating: {version.avg_rating:.2f}")
    click.echo(f"  Success Rate: {version.success_rate:.1%}")
    click.echo(f"  Error Rate: {version.error_rate:.1%}")
    click.echo(f"  Usage Count: {version.usage_count}")


@prompt.command()
@click.argument('prompt_id')
def versions(prompt_id: str):
    """List all versions of a prompt"""
    manager = PromptManager()
    versions = manager.get_all_versions(prompt_id)
    
    if not versions:
        click.echo(f"No versions found for {prompt_id}")
        return
        
    click.echo(f"\nVersions for {prompt_id}:")
    for v in versions:
        status = "ACTIVE" if v.is_active else ("EXPERIMENTAL" if v.is_experimental else "RETIRED")
        click.echo(f"  v{v.version} - {status} - Created: {v.created_at.strftime('%Y-%m-%d %H:%M')}")


@prompt.command()
@click.argument('prompt_id')
@click.argument('version', type=int)
def deploy(prompt_id: str, version: int):
    """Deploy a specific prompt version"""
    manager = PromptManager()
    
    if manager.deploy_version(prompt_id, version):
        click.echo(f"Deployed {prompt_id} v{version}")
    else:
        click.echo(f"Failed to deploy {prompt_id} v{version}", err=True)


@prompt.command()
@click.argument('prompt_id')
def rollback(prompt_id: str):
    """Rollback to previous prompt version"""
    manager = PromptManager()
    
    if manager.rollback_prompt(prompt_id):
        version = manager.get_active_prompt(prompt_id)
        click.echo(f"Rolled back {prompt_id} to v{version.version}")
    else:
        click.echo(f"Failed to rollback {prompt_id}", err=True)


@prompt.command()
@click.argument('output_dir', type=click.Path())
@click.option('--type', 'prompt_type', type=click.Choice(['system', 'user', 'all']), default='all')
def export(output_dir: str, prompt_type: str):
    """Export prompts to directory"""
    manager = PromptManager()
    
    pt = None if prompt_type == 'all' else PromptType(prompt_type)
    manager.export_prompts(output_dir, pt)
    
    click.echo(f"Exported prompts to {output_dir}")


@cli.group()
def feedback():
    """Manage feedback collection"""
    pass


@feedback.command()
@click.argument('prompt_id')
@click.option('--limit', type=int, default=10)
def list(prompt_id: str, limit: int):
    """List recent feedback for a prompt"""
    async def _list():
        collector = FeedbackCollector()
        feedback_list = await collector.get_feedback_for_prompt(prompt_id, limit=limit)
        
        if not feedback_list:
            click.echo(f"No feedback found for {prompt_id}")
            return
            
        click.echo(f"\nRecent feedback for {prompt_id}:")
        for fb in feedback_list:
            click.echo(f"\n{fb.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {fb.feedback_type.value}")
            if fb.rating is not None:
                click.echo(f"  Rating: {fb.rating:.2f}")
            if fb.message:
                click.echo(f"  Message: {fb.message}")
            if fb.error_details:
                click.echo(f"  Error: {fb.error_details.get('error_message', 'Unknown')}")
                
    asyncio.run(_list())


@feedback.command()
@click.argument('prompt_id')
def summary(prompt_id: str):
    """Show feedback summary for a prompt"""
    async def _summary():
        collector = FeedbackCollector()
        summary = await collector.get_feedback_summary(prompt_id)
        
        click.echo(f"\nFeedback summary for {prompt_id}:")
        click.echo(f"  Total Feedback: {summary['total_feedback']}")
        click.echo(f"  Average Rating: {summary['average_rating']:.2f}" if summary['average_rating'] else "  Average Rating: N/A")
        click.echo(f"  Success Rate: {summary['success_rate']:.1%}")
        click.echo(f"  Error Rate: {summary['error_rate']:.1%}")
        
        click.echo("\nFeedback by type:")
        for ft, count in summary['feedback_types'].items():
            if count > 0:
                click.echo(f"  {ft}: {count}")
                
    asyncio.run(_summary())


@cli.group()
def train():
    """Train and improve prompts"""
    pass


@train.command()
@click.argument('prompt_id')
@click.option('--approach', type=click.Choice(['few_shot', 'reinforcement', 'meta_prompt', 'adversarial']), default='few_shot')
@click.option('--min-feedback', type=int, default=10)
@click.option('--api-key', envvar='OPENAI_API_KEY')
def run(prompt_id: str, approach: str, min_feedback: int, api_key: str):
    """Train a prompt based on feedback"""
    async def _train():
        collector = FeedbackCollector()
        manager = PromptManager()
        trainer = PromptTrainer(collector, manager, openai_api_key=api_key)
        
        click.echo(f"Training {prompt_id} using {approach} approach...")
        
        result = await trainer.train_prompt(
            prompt_id=prompt_id,
            training_approach=approach,
            min_feedback_count=min_feedback
        )
        
        if result:
            if result.status == "completed":
                click.echo(f"Training completed successfully!")
                click.echo(f"Created new version: v{manager.get_version(prompt_id, -1).version}")
                click.echo(f"Metrics: {json.dumps(result.metrics, indent=2)}")
            else:
                click.echo(f"Training failed: {result.error_message}", err=True)
        else:
            click.echo("Training could not be started (insufficient feedback?)", err=True)
            
    asyncio.run(_train())


@train.command('status')
@click.option('--api-key', envvar='OPENAI_API_KEY')
def status(api_key: str):
    """Check automatic training status"""
    async def _status():
        collector = FeedbackCollector()
        manager = PromptManager()
        auto_trainer = AutomaticPromptTrainer(collector, manager, openai_api_key=api_key)
        
        status = auto_trainer.get_training_status()
        
        click.echo(f"\nAutomatic Training Status:")
        click.echo(f"  Enabled: {status['enabled']}")
        click.echo(f"  Running: {status['running']}")
        click.echo(f"  Training Queue: {len(status['training_queue'])} prompts")
        click.echo(f"  Recent Training: {len(status['recent_training'])} prompts")
        
        if status['training_queue']:
            click.echo(f"\nQueued for Training:")
            for prompt_id in status['training_queue']:
                click.echo(f"  - {prompt_id}")
                
        if status['recent_training']:
            click.echo(f"\nRecent Training Sessions:")
            for prompt_id, timestamp in status['recent_training'].items():
                click.echo(f"  - {prompt_id}: {timestamp[:19]}")
                
    asyncio.run(_status())


@train.command('start-auto')
@click.option('--config', type=click.Path(), help='Configuration file for auto-trainer')
@click.option('--api-key', envvar='OPENAI_API_KEY')
def start_auto(config: Optional[str], api_key: str):
    """Start automatic training service"""
    async def _start():
        collector = FeedbackCollector()
        manager = PromptManager()
        auto_trainer = AutomaticPromptTrainer(
            collector, 
            manager, 
            openai_api_key=api_key,
            config_path=config
        )
        
        await collector.start()
        await auto_trainer.start()
        
        click.echo("Automatic training service started")
        click.echo("Press Ctrl+C to stop...")
        
        try:
            while True:
                await asyncio.sleep(60)
                # Show periodic status
                status = auto_trainer.get_training_status()
                if status['training_queue']:
                    click.echo(f"Training queue: {len(status['training_queue'])} prompts")
                    
        except KeyboardInterrupt:
            click.echo("\nStopping automatic training service...")
            await auto_trainer.stop()
            await collector.stop()
            
    asyncio.run(_start())


@train.command('trigger')
@click.argument('prompt_id')
@click.option('--approach', type=click.Choice(['few_shot', 'reinforcement', 'meta_prompt', 'adversarial']))
@click.option('--api-key', envvar='OPENAI_API_KEY')
def trigger(prompt_id: str, approach: Optional[str], api_key: str):
    """Manually trigger automatic training for a prompt"""
    async def _trigger():
        collector = FeedbackCollector()
        manager = PromptManager()
        auto_trainer = AutomaticPromptTrainer(collector, manager, openai_api_key=api_key)
        
        click.echo(f"Triggering training for {prompt_id}...")
        await auto_trainer.trigger_manual_training(prompt_id, approach)
        click.echo("Training request submitted")
        
    asyncio.run(_trigger())


@cli.group()
def evaluate():
    """Evaluate prompt versions"""
    pass


@evaluate.command()
@click.argument('prompt_id')
@click.argument('version', type=int)
@click.option('--baseline', type=int, help='Baseline version for comparison')
@click.option('--test-suite', help='Name of test suite to use')
@click.option('--api-key', envvar='OPENAI_API_KEY')
def version(prompt_id: str, version: int, baseline: Optional[int], test_suite: Optional[str], api_key: str):
    """Evaluate a specific prompt version"""
    async def _evaluate():
        manager = PromptManager()
        evaluator = PromptEvaluator(manager, openai_api_key=api_key)
        
        prompt_version = manager.get_version(prompt_id, version)
        if not prompt_version:
            click.echo(f"Version {version} not found for {prompt_id}", err=True)
            return
            
        baseline_version = None
        if baseline:
            baseline_version = manager.get_version(prompt_id, baseline)
            
        click.echo(f"Evaluating {prompt_id} v{version}...")
        
        result = await evaluator.evaluate_version(
            prompt_version,
            test_suite_name=test_suite,
            baseline_version=baseline_version
        )
        
        click.echo(f"\nEvaluation Results:")
        click.echo(f"  Test Cases: {result.test_cases_passed}/{result.test_cases_total} passed")
        click.echo(f"  Latency: p50={result.latency_p50:.2f}s, p95={result.latency_p95:.2f}s")
        click.echo(f"  Quality Scores:")
        click.echo(f"    Coherence: {result.coherence_score:.2f}")
        click.echo(f"    Relevance: {result.relevance_score:.2f}")
        click.echo(f"    Safety: {result.safety_score:.2f}")
        
        if result.improvement_delta:
            click.echo(f"\n  Improvements vs baseline:")
            for metric, delta in result.improvement_delta.items():
                click.echo(f"    {metric}: {delta:+.1%}")
                
        click.echo(f"\n  Recommendation: {result.recommendation.upper()} (confidence: {result.confidence:.2f})")
        if result.notes:
            click.echo(f"  Notes: {result.notes}")
            
    asyncio.run(_evaluate())


@evaluate.command('create-suite')
@click.argument('prompt_id')
@click.argument('suite_name')
@click.argument('test_file', type=click.Path(exists=True))
def create_suite(prompt_id: str, suite_name: str, test_file: str):
    """Create a test suite from JSON file"""
    async def _create():
        with open(test_file, 'r') as f:
            test_cases = json.load(f)
            
        manager = PromptManager()
        evaluator = PromptEvaluator(manager)
        
        await evaluator.create_test_suite(prompt_id, suite_name, test_cases)
        click.echo(f"Created test suite '{suite_name}' for {prompt_id}")
        
    asyncio.run(_create())


@cli.command()
@click.option('--config-file', type=click.Path(), help='Configuration file')
def init(config_file: Optional[str]):
    """Initialize prompt training system"""
    # Create directory structure
    directories = [
        "prompt_training/feedback",
        "prompt_training/system",
        "prompt_training/user",
        "prompt_training/versions",
        "prompt_training/models",
        "prompt_training/evaluation/test_suites",
        "prompt_training/evaluation/results",
        "prompt_training/configs"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        
    # Create default configuration
    default_config = {
        "training": {
            "model": "gpt-4",
            "temperature": 0.7,
            "approaches": ["few_shot", "reinforcement", "meta_prompt", "adversarial"],
            "min_feedback_required": 10
        },
        "evaluation": {
            "test_runs": 3,
            "metrics": ["coherence", "relevance", "safety"],
            "deployment_thresholds": {
                "success_rate": 0.8,
                "safety_score": 0.9,
                "improvement_required": 0.05
            }
        },
        "feedback": {
            "batch_size": 10,
            "retention_days": 90
        }
    }
    
    config_path = Path(config_file if config_file else "prompt_training/configs/default.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=2)
        
    click.echo(f"Initialized prompt training system")
    click.echo(f"Configuration saved to: {config_path}")
    
    # Create example test suite
    example_tests = [
        {
            "id": "test_1",
            "description": "Basic functionality test",
            "input": {"query": "Hello, how can you help?"},
            "expected_behavior": ["friendly", "informative", "clear"]
        },
        {
            "id": "test_2",
            "description": "Error handling test",
            "input": {"query": ""},
            "expected_behavior": ["handles_empty_input", "no_error"]
        }
    ]
    
    example_path = Path("prompt_training/evaluation/test_suites/example_suite.json")
    with open(example_path, 'w') as f:
        json.dump(example_tests, f, indent=2)
        
    click.echo(f"Created example test suite: {example_path}")


if __name__ == '__main__':
    cli()