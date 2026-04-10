"""MCP Prompts: Pipeline templates and wiki page templates."""

from fastmcp import FastMCP


PIPELINE_TEMPLATES = {
    "REQ": """You are a requirements analyst. Parse the following user requirement into a structured spec.

Output format:
```markdown
# Requirements: {title}

## User Story
As a [user], I want [goal] so that [benefit].

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Constraints
- Technical constraints
- Non-functional requirements

## Open Questions
- Questions that need clarification
```

User requirement: {requirement}""",

    "ARCH": """You are a system architect. Design the architecture based on the requirements.

Output format:
```markdown
# Architecture: {title}

## System Design
- Components and their responsibilities
- Data flow

## API Contracts
```json
{ "endpoints": [] }
```

## Technology Choices
- Language, framework, database
- Justification for each choice

## Risks
- Technical risks
- Mitigation strategies
```

Requirements: {requirements}""",

    "DEV": """You are a senior developer. Implement the feature following the architecture and contracts.

Rules:
- Follow the API contracts exactly
- Write atomic functions (≤ 50 lines each)
- Include type hints and docstrings
- Handle error cases

Architecture: {architecture}
Contracts: {contracts}""",

    "INT": """You are an integration engineer. Wire all components together.

Tasks:
1. Verify all module interfaces match the contracts
2. Resolve integration conflicts
3. Ensure end-to-end data flow works
4. Test cross-module communication

Architecture: {architecture}
Contracts: {contracts}
Existing implementations: {implementations}""",

    "QA": """You are a QA engineer. Perform adversarial testing on the implementation.

Test categories:
1. **Boundary tests** — edge cases, empty inputs, max values
2. **Security tests** — injection, auth bypass, data exposure
3. **Concurrency tests** — race conditions, deadlocks
4. **Reliability tests** — error handling, recovery

Report format:
```markdown
# QA Report

## Pass/Fail Summary
| Test | Status | Details |
|------|--------|---------|

## Bugs Found
- Critical: ...
- Minor: ...

## Recommendations
- ...
```

Implementation: {implementation}""",

    "DEPLOY": """You are a DevOps engineer. Package and deploy the application.

Tasks:
1. Create deployment manifest
2. Set up environment configuration
3. Run pre-deployment checks
4. Package the application
5. Generate deployment instructions

Deployment target: {target}
Application: {implementation}""",
}

WIKI_PAGE_TEMPLATES = {
    "concept": """# {name}

## Definition
_Concise definition in 1-2 sentences._

## Context
_How this concept relates to other knowledge in the wiki._

## Examples
- Example 1
- Example 2

## Related
- [[related concept 1]]
- [[related concept 2]]

## Source
_Where this knowledge came from._""",

    "decision": """# Decision: {title}

## Context
_What prompted this decision?_

## Options Considered
1. **Option A** — Pros/Cons
2. **Option B** — Pros/Cons

## Decision
_What was chosen and why._

## Consequences
_What are the implications of this decision?_

## Date
{date}""",

    "guide": """# Guide: {title}

## Prerequisites
_What you need before starting._

## Steps
1. Step 1
2. Step 2
3. Step 3

## Troubleshooting
- Problem → Solution

## See Also
- Related guides""",
}


def register_prompts(mcp: FastMCP):
    """Register prompt templates."""

    @mcp.prompt(name="pipeline_template")
    def pipeline_template(stage: str = "REQ") -> str:
        """Get a prompt template for a pipeline stage.

        Args:
            stage: Pipeline stage (REQ, ARCH, DEV, INT, QA, DEPLOY)
        """
        stage_upper = stage.upper()
        template = PIPELINE_TEMPLATES.get(stage_upper)
        if not template:
            return (
                f"Unknown stage: {stage}\n"
                f"Available stages: {', '.join(PIPELINE_TEMPLATES.keys())}"
            )
        return template

    @mcp.prompt(name="wiki_page_template")
    def wiki_page_template(page_type: str = "concept") -> str:
        """Get a template for a wiki page.

        Args:
            page_type: Type of page (concept, decision, guide)
        """
        template = WIKI_PAGE_TEMPLATES.get(page_type)
        if not template:
            return (
                f"Unknown page type: {page_type}\n"
                f"Available types: {', '.join(WIKI_PAGE_TEMPLATES.keys())}"
            )
        return template
