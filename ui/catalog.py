"""Navigation and editorial content for the strategy workspace."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Workspace:
    slug: str
    title: str
    icon: str
    summary: str
    question: str
    capabilities: tuple[str, ...]

    @property
    def script(self) -> str:
        return f"app_pages/{self.slug.replace('-', '_')}.py"


WORKSPACES = (
    Workspace(
        "market-intelligence",
        "Market Intelligence",
        ":material/radar:",
        "Research industry developments and track shifts in hospitality technology.",
        "Which market changes could affect our strategy?",
        (
            "Review industry developments with source links and publication dates.",
            "Track trends by segment, geography, and technology category.",
            "Summarize what emerging signals could mean for the business.",
        ),
    ),
    Workspace(
        "competitive-benchmarking",
        "Competitive Benchmarking",
        ":material/compare_arrows:",
        "Compare vendors by capabilities, customer segments, and positioning.",
        "Where do vendors compete, and where is there room to differentiate?",
        (
            "Build vendor profiles with evidence for each comparison.",
            "Compare product coverage, integrations, and target segments.",
            "Identify gaps and questions for further research.",
        ),
    ),
    Workspace(
        "product-growth-intelligence",
        "Product Growth Intelligence",
        ":material/trending_up:",
        "Identify product expansion, cross-selling, and partnership opportunities.",
        "Which opportunities deserve further validation?",
        (
            "Map adjacent products and customer needs.",
            "Identify cross-selling paths by customer segment and product fit.",
            "Document evidence and open questions before prioritizing opportunities.",
        ),
    ),
    Workspace(
        "financial-scenario-simulator",
        "Financial Scenario Simulator",
        ":material/calculate:",
        "Evaluate strategic investments using explicit assumptions and scenarios.",
        "Which assumptions could change an investment decision?",
        (
            "Define inputs for a strategic investment or product initiative.",
            "Compare base, upside, and downside scenarios.",
            "Test how changes in key assumptions affect projected outcomes.",
        ),
    ),
    Workspace(
        "ai-strategy-advisor",
        "Strategy Advisor",
        ":material/assignment:",
        "Turn research and analysis into executive recommendations.",
        "What should leadership do next, and what evidence supports it?",
        (
            "Synthesize findings across the research and analysis workspaces.",
            "Draft recommendations with supporting evidence and trade-offs.",
            "Identify uncertainties and follow-up questions for executive review.",
        ),
    ),
)

WORKSPACES_BY_SLUG = {workspace.slug: workspace for workspace in WORKSPACES}
