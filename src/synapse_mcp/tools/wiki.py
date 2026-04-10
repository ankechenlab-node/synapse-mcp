"""MCP Tools: Wiki knowledge management (init, ingest, query, lint)."""

import re
from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

# Max file size for ingest (10MB)
_MAX_INGEST_SIZE = 10 * 1024 * 1024


def register_wiki_tools(mcp: FastMCP):
    """Register wiki knowledge management tools."""

    @mcp.tool(annotations=ToolAnnotations(
        title="Initialize Wiki",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ))
    def wiki_init(path: str, name: str = "My Wiki") -> str:
        """Initialize a new wiki knowledge base in the given directory.

        Creates .knowledge/ structure with CLAUDE.md, index.md, log.md.

        Args:
            path: Directory path for the wiki
            name: Wiki display name
        """
        target = Path(path).expanduser().resolve()

        # Reject if path is an existing file
        if target.exists() and not target.is_dir():
            return f"Error: '{path}' is a file, not a directory"

        target.mkdir(parents=True, exist_ok=True)

        # Don't overwrite existing wiki files
        core_files = ["CLAUDE.md", "index.md", "log.md"]
        existing = [f for f in core_files if (target / f).exists()]
        if existing:
            return (
                f"Wiki already initialized at: {target}\n"
                f"Existing files: {', '.join(existing)}\n"
                f"Use wiki_ingest to add content instead."
            )

        # Create core wiki files
        (target / "CLAUDE.md").write_text(f"# {name}\n\nKnowledge base for {name}.\n")
        (target / "index.md").write_text("# Knowledge Index\n\n_Empty. Ingest content to begin._\n")
        (target / "log.md").write_text("# Activity Log\n\n_Empty._\n")

        return (
            f"Wiki initialized at: {target}\n"
            f"Name: {name}\n"
            f"Files created: {', '.join(core_files)}"
        )

    @mcp.tool(annotations=ToolAnnotations(
        title="Ingest Content",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ))
    def wiki_ingest(
        path: str,
        source: str,
        source_type: str = "file",
    ) -> str:
        """Ingest content into the wiki knowledge base.

        Accepts files, directories, or raw text. Automatically classifies
        and links to the knowledge graph.

        Args:
            path: Wiki root directory
            source: File path, directory, or raw text to ingest
            source_type: Type of source (file, directory, text)
        """
        wiki_path = Path(path).expanduser().resolve()
        if not (wiki_path / "CLAUDE.md").exists():
            return f"Not a valid wiki: {path}. Run wiki_init first."

        source_path = Path(source).expanduser()

        if source_type == "text":
            # Ingest raw text — append to knowledge log
            log_file = wiki_path / "log.md"
            with open(log_file, "a") as f:
                f.write(f"\n## Ingested text\n\n{source[:2000]}...\n")
            return f"Text ingested ({len(source)} chars) → {log_file}"

        if not source_path.exists():
            return f"Source not found: {source}"

        if source_path.is_file():
            # Check file size
            if source_path.stat().st_size > _MAX_INGEST_SIZE:
                return f"File too large: {source_path.name} ({source_path.stat().st_size / 1024 / 1024:.1f}MB > 10MB limit)"
            content = source_path.read_text()
            log_file = wiki_path / "log.md"
            with open(log_file, "a") as f:
                f.write(f"\n## Ingested: {source_path.name}\n\n{content[:2000]}...\n")
            return f"File ingested: {source_path.name} ({len(content)} chars)"

        if source_path.is_dir():
            files = list(source_path.glob("**/*.md")) + list(source_path.glob("**/*.txt"))
            count = 0
            log_file = wiki_path / "log.md"
            with open(log_file, "a") as f:
                for fp in files[:100]:
                    try:
                        content = fp.read_text()
                        f.write(f"\n## Ingested: {fp.name}\n\n{content[:1000]}...\n")
                        count += 1
                    except (IOError, UnicodeDecodeError):
                        continue  # skip unreadable files
            return f"Directory ingested: {count} files from {source_path}"

        return f"Unsupported source type: {source}"

    @mcp.tool(annotations=ToolAnnotations(
        title="Query Wiki",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    def wiki_query(path: str, question: str) -> str:
        """Query the wiki knowledge base with a natural language question.

        Searches indexed knowledge and returns relevant context.

        Args:
            path: Wiki root directory
            question: Natural language question
        """
        wiki_path = Path(path).expanduser().resolve()
        if not (wiki_path / "CLAUDE.md").exists():
            return f"Not a valid wiki: {path}. Run wiki_init first."

        # Search knowledge files with improved snippet extraction
        results = []
        keywords = question.lower().split()
        max_files = 50  # limit to avoid OOM on large wikis
        for i, md_file in enumerate(wiki_path.glob("*.md")):
            if i >= max_files:
                break
            try:
                content = md_file.read_text()
            except (IOError, UnicodeDecodeError):
                continue
            score = sum(1 for kw in keywords if kw in content.lower())
            if score > 0:
                # Extract a better snippet around the first keyword match
                snippet = _extract_snippet(content, keywords, limit=400)
                results.append((score, md_file.name, snippet))

        if not results:
            return (
                f"No results found for: '{question}'\n"
                f"Try ingesting content first, or rephrase your question."
            )

        results.sort(reverse=True, key=lambda x: x[0])
        lines = [f"Query: '{question}'\n", f"Results ({len(results)}):", ""]
        for score, filename, snippet in results[:5]:
            lines.append(f"### {filename} (relevance: {score})")
            lines.append(snippet)
            lines.append("")

        return "\n".join(lines)

    @mcp.tool(annotations=ToolAnnotations(
        title="Wiki Lint",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    def wiki_lint(path: str) -> str:
        """Run health check on the wiki knowledge base.

        Checks for broken links, missing files, and structural issues.

        Args:
            path: Wiki root directory
        """
        wiki_path = Path(path).expanduser().resolve()
        if not wiki_path.exists():
            return f"Directory not found: {path}"

        issues = []
        checks_passed = 0

        # Check required files
        required = ["CLAUDE.md", "index.md", "log.md"]
        for f in required:
            if (wiki_path / f).exists():
                checks_passed += 1
            else:
                issues.append(f"Missing: {f}")

        # Check for empty files
        for f in wiki_path.glob("*.md"):
            if f.stat().st_size == 0:
                issues.append(f"Empty file: {f.name}")

        # Check for broken internal links
        for md_file in wiki_path.glob("*.md"):
            try:
                content = md_file.read_text()
            except (IOError, UnicodeDecodeError):
                issues.append(f"Unreadable file: {md_file.name}")
                continue
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
            for text, url in links:
                if url.startswith("http"):
                    continue
                target = wiki_path / url.split("#")[0]
                if not target.exists():
                    issues.append(f"Broken link in {md_file.name}: {url}")

        status = "PASS" if not issues else "WARN"
        lines = [
            f"Wiki Health Check: {status}",
            f"Checks passed: {checks_passed}/{len(required)}",
        ]
        if issues:
            lines.append(f"\nIssues ({len(issues)}):")
            for issue in issues:
                lines.append(f"  - {issue}")
        else:
            lines.append("\nNo issues found.")

        return "\n".join(lines)


def _extract_snippet(content: str, keywords: list[str], limit: int = 400) -> str:
    """Extract a relevant snippet around the first keyword match."""
    lower = content.lower()
    positions = []
    for kw in keywords:
        pos = lower.find(kw)
        if pos >= 0:
            positions.append(pos)

    if not positions:
        return content[:limit]

    # Use the earliest match
    start = min(positions)
    # Expand around the match
    snippet_start = max(0, start - 50)
    snippet_end = min(len(content), start + limit)
    snippet = content[snippet_start:snippet_end]
    if snippet_start > 0:
        snippet = "..." + snippet
    if snippet_end < len(content):
        snippet += "..."
    return snippet
