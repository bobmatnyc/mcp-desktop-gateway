# Prompt Training System

An advanced prompt training and improvement system for the MCP Desktop Gateway that uses LangChain and machine learning to continuously improve prompts based on user feedback and error analysis.

## Features

- **Automatic Feedback Collection**: Captures user ratings, errors, and success metrics
- **Version Control**: Maintains version history for all prompts with rollback capability
- **LangChain Training**: Multiple training approaches (few-shot, reinforcement, meta-prompt, adversarial)
- **Comprehensive Evaluation**: Automated testing and quality metrics
- **A/B Testing**: Compare prompt versions in production
- **CLI Management**: Full command-line interface for prompt operations

## Architecture

```
prompt_training/
├── feedback/          # Collected feedback data
├── system/           # System-level prompts
├── user/            # User-facing prompts  
├── versions/        # Prompt version history
├── models/          # Trained models
├── evaluation/      # Test suites and results
└── configs/         # Configuration files
```

## Components

### 1. Feedback Collector
Collects various types of feedback:
- User ratings (0.0 to 1.0)
- Error reports with details
- Success metrics (execution time, etc.)
- Improvement suggestions
- Automated metrics

### 2. Prompt Manager
Manages prompt versions:
- Create and update prompts
- Version control with metadata
- Deploy/rollback versions
- Export prompts for use
- Track performance metrics

### 3. Prompt Trainer
Trains improved prompts using LangChain:
- **Few-shot learning**: Learn from successful examples
- **Reinforcement learning**: Reinforce positive patterns, avoid negative ones
- **Meta-prompt optimization**: Use LLM to improve prompts
- **Adversarial training**: Identify and fix edge cases

### 4. Evaluator
Tests and evaluates prompt versions:
- Run test suites
- Calculate quality metrics (coherence, relevance, safety)
- Compare with baselines
- Generate deployment recommendations

## Installation

```bash
# Install dependencies
pip install langchain openai tiktoken faiss-cpu

# Initialize the system
python -m prompt_training.cli init
```

## Usage

### CLI Commands

```bash
# Create a new prompt
python -m prompt_training.cli prompt create my_prompt prompt.txt --type user

# View prompt details
python -m prompt_training.cli prompt show my_prompt

# List versions
python -m prompt_training.cli prompt versions my_prompt

# Deploy a version
python -m prompt_training.cli prompt deploy my_prompt 2

# Rollback to previous version
python -m prompt_training.cli prompt rollback my_prompt

# View feedback
python -m prompt_training.cli feedback list my_prompt
python -m prompt_training.cli feedback summary my_prompt

# Train improved version
python -m prompt_training.cli train run my_prompt --approach few_shot

# Evaluate a version
python -m prompt_training.cli evaluate version my_prompt 2 --baseline 1

# Export prompts
python -m prompt_training.cli prompt export ./exported_prompts
```

### Integration with MCP Gateway

1. **Add to configuration** (`config/config.yaml`):
```yaml
connectors:
  - name: prompt_training
    type: prompt_training
    enabled: true
    config:
      auto_collect: true
      collect_errors: true
      collect_success: true
      prompt_improvement_enabled: true
```

2. **Use middleware in connectors**:
```python
from prompt_training.integration import PromptTrainingMiddleware

class MyConnector(BaseConnector):
    def __init__(self, name, config):
        super().__init__(name, config)
        self.training = PromptTrainingMiddleware()
        
    async def execute_prompt(self, prompt_name, arguments):
        # Wrap execution with training middleware
        return await self.training.intercept_prompt_execution(
            self, prompt_name, arguments,
            lambda p, a: super().execute_prompt(p, a)
        )
```

3. **Collect feedback from users**:
```python
# In your connector or tool
await self.training.collect_user_feedback(
    prompt_id="my_prompt",
    rating=0.8,
    message="Good response but could be clearer"
)
```

## Training Approaches

### Few-Shot Learning
Best for prompts with many successful examples:
- Extracts patterns from high-rated interactions
- Uses semantic similarity to select relevant examples
- Generates improved prompts that follow successful patterns

### Reinforcement Learning
Best for fixing specific issues:
- Analyzes positive and negative examples separately
- Identifies error patterns
- Reinforces good behaviors while avoiding bad ones

### Meta-Prompt Optimization
Best for general improvements:
- Uses GPT-4 to analyze feedback and suggest improvements
- Considers performance metrics and user suggestions
- Applies prompt engineering best practices

### Adversarial Training
Best for robustness:
- Generates edge cases and adversarial inputs
- Identifies potential failure modes
- Creates more resilient prompts

## Evaluation Metrics

- **Success Rate**: Percentage of successful executions
- **Latency**: Response time (p50, p95)
- **Token Usage**: Average tokens consumed
- **Quality Scores**:
  - Coherence: Clarity and logical flow
  - Relevance: How well output matches input
  - Safety: Absence of harmful content
- **User Ratings**: Average user satisfaction

## Best Practices

1. **Collect Diverse Feedback**: Ensure feedback represents various use cases
2. **Test Thoroughly**: Always evaluate new versions before deployment
3. **Monitor Metrics**: Track performance after deployment
4. **Gradual Rollout**: Use A/B testing for major changes
5. **Document Changes**: Keep notes on why changes were made

## Configuration

Default configuration (`prompt_training/configs/default.json`):
```json
{
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
```

## API Key

Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your-api-key
```

## Troubleshooting

### Insufficient Feedback
- Minimum 10 feedback items required for training
- Use `feedback summary` to check count
- Consider lowering `min_feedback_required` in config

### Training Fails
- Check API key is set correctly
- Verify feedback quality (not all errors)
- Try different training approach

### Poor Evaluation Results
- Review test cases for relevance
- Check baseline version performance
- Analyze failure patterns in feedback

## Future Enhancements

- Real-time A/B testing integration
- Multi-model training support
- Automated deployment based on metrics
- Feedback UI for easier collection
- Integration with LangSmith for monitoring