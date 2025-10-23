"""
Finding Presenter - Rich formatting and presentation of analysis findings.

This module handles the user-facing presentation of edge cases, contradictions,
completeness gaps, and compressed requirements in a clear, actionable format.
"""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.tree import Tree
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
import json


class FindingPresenter:
    """
    Formats and presents analysis findings in a user-friendly way.

    Uses rich formatting to make complex technical findings accessible and actionable.
    Supports multiple output formats and export options.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.export_data = {}  # Store data for potential export

    def present_edge_cases(self, edge_cases: List[Dict[str, Any]]):
        """Present edge cases in a readable, actionable format."""
        if not edge_cases:
            self.console.print("✅ [green]No edge cases identified[/green]")
            return

        self.console.print(f"\n🔍 [bold yellow]Edge Cases Identified ({len(edge_cases)})[/bold yellow]")

        # Group edge cases by severity/priority
        grouped_cases = self._group_edge_cases_by_priority(edge_cases)

        for priority, cases in grouped_cases.items():
            if not cases:
                continue

            priority_color = self._get_priority_color(priority)

            panel_content = []
            for i, case in enumerate(cases, 1):
                case_text = f"[bold]{i}. {case.get('description', 'Unknown edge case')}[/bold]\n"

                # Add context if available
                if case.get('context'):
                    case_text += f"   [dim]Context:[/dim] {case['context']}\n"

                # Add impact assessment
                if case.get('impact'):
                    case_text += f"   [dim]Impact:[/dim] {case['impact']}\n"

                # Add current handling status
                if case.get('handled'):
                    case_text += f"   [green]✓ Handling defined:[/green] {case.get('handling', 'None')}\n"
                else:
                    case_text += f"   [red]⚠ No handling defined[/red]\n"

                panel_content.append(case_text)

            panel = Panel(
                "\n".join(panel_content),
                title=f"{priority.title()} Priority Edge Cases ({len(cases)})",
                border_style=priority_color,
                expand=False
            )
            self.console.print(panel)

        # Store for export
        self.export_data['edge_cases'] = {
            'total': len(edge_cases),
            'by_priority': {p: len(cases) for p, cases in grouped_cases.items()},
            'details': edge_cases
        }

    def present_contradictions(self, contradictions: List[Dict[str, Any]]):
        """Present contradictions with clear explanations."""
        if not contradictions:
            self.console.print("✅ [green]No contradictions found[/green]")
            return

        self.console.print(f"\n⚠️  [bold red]Contradictions Found ({len(contradictions)})[/bold red]")

        for i, contradiction in enumerate(contradictions, 1):
            # Create a table for each contradiction
            table = Table(show_header=True, header_style="bold red")
            table.add_column("Aspect", style="cyan", width=15)
            table.add_column("Details", style="white")

            table.add_row("Description", contradiction.get('description', 'Unknown contradiction'))

            # Show conflicting requirements
            if contradiction.get('conflicting_requirements'):
                req_text = "\n".join([
                    f"• {req}" for req in contradiction['conflicting_requirements']
                ])
                table.add_row("Conflicting Requirements", req_text)

            # Show severity and impact
            severity = contradiction.get('severity', 'medium')
            severity_color = self._get_severity_color(severity)
            table.add_row("Severity", f"[{severity_color}]{severity.title()}[/{severity_color}]")

            if contradiction.get('impact'):
                table.add_row("Impact", contradiction['impact'])

            # Show resolution status
            if contradiction.get('resolved'):
                table.add_row("Status", f"[green]✓ Resolved[/green]")
                if contradiction.get('resolution'):
                    table.add_row("Resolution", contradiction['resolution'])
            else:
                table.add_row("Status", f"[red]⚠ Unresolved[/red]")

            panel = Panel(
                table,
                title=f"Contradiction {i}",
                border_style="red",
                expand=False
            )
            self.console.print(panel)

        # Store for export
        self.export_data['contradictions'] = {
            'total': len(contradictions),
            'resolved': len([c for c in contradictions if c.get('resolved', False)]),
            'unresolved': len([c for c in contradictions if not c.get('resolved', False)]),
            'details': contradictions
        }

    def present_completeness_gaps(self, gaps: List[Dict[str, Any]]):
        """Present completeness gaps with priority."""
        if not gaps:
            self.console.print("✅ [green]No completeness gaps identified[/green]")
            return

        self.console.print(f"\n📋 [bold blue]Completeness Gaps ({len(gaps)})[/bold blue]")

        # Sort gaps by priority
        sorted_gaps = sorted(gaps, key=lambda x: self._get_priority_order(x.get('priority', 'medium')))

        # Create a tree structure for better visualization
        tree = Tree("🔍 [bold]Missing Requirements[/bold]")

        current_priority = None
        priority_node = None

        for gap in sorted_gaps:
            gap_priority = gap.get('priority', 'medium')

            # Create new priority node if needed
            if gap_priority != current_priority:
                current_priority = gap_priority
                priority_color = self._get_priority_color(gap_priority)
                priority_node = tree.add(f"[{priority_color}]{gap_priority.title()} Priority[/{priority_color}]")

            # Add gap to current priority node
            gap_text = gap.get('description', 'Unknown gap')
            if gap.get('suggested_requirement'):
                gap_text += f"\n[dim]Suggestion:[/dim] {gap['suggested_requirement']}"

            priority_node.add(gap_text)

        self.console.print(tree)

        # Show summary statistics
        priority_counts = {}
        for gap in gaps:
            priority = gap.get('priority', 'medium')
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        summary_table = Table(show_header=True, header_style="bold blue")
        summary_table.add_column("Priority", style="cyan")
        summary_table.add_column("Count", justify="right", style="white")
        summary_table.add_column("Percentage", justify="right", style="dim")

        total_gaps = len(gaps)
        for priority in ['high', 'medium', 'low']:
            count = priority_counts.get(priority, 0)
            percentage = (count / total_gaps * 100) if total_gaps > 0 else 0
            priority_color = self._get_priority_color(priority)

            summary_table.add_row(
                f"[{priority_color}]{priority.title()}[/{priority_color}]",
                str(count),
                f"{percentage:.1f}%"
            )

        self.console.print("\n", summary_table)

        # Store for export
        self.export_data['completeness_gaps'] = {
            'total': len(gaps),
            'by_priority': priority_counts,
            'details': gaps
        }

    def present_compressed_requirements(self, compressed: List[Dict[str, Any]]):
        """Show compressed requirements with before/after comparison."""
        if not compressed:
            self.console.print("✅ [green]No requirements compressed[/green]")
            return

        self.console.print(f"\n🗜️  [bold magenta]Compressed Requirements ({len(compressed)})[/bold magenta]")

        for i, compression in enumerate(compressed, 1):
            # Create side-by-side comparison
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Original", style="dim", width=40)
            table.add_column("Compressed", style="bright_white", width=40)
            table.add_column("Savings", style="green", width=10)

            original = compression.get('original_requirements', [])
            compressed_req = compression.get('compressed_requirement', '')

            # Calculate compression ratio
            original_length = sum(len(req.get('content', '')) for req in original)
            compressed_length = len(compressed_req)
            savings = f"{(1 - compressed_length/original_length)*100:.1f}%" if original_length > 0 else "N/A"

            # Format original requirements
            original_text = "\n".join([
                f"• {req.get('content', 'Unknown')}" for req in original
            ])

            table.add_row(original_text, compressed_req, savings)

            # Add confidence and quality metrics
            if compression.get('confidence'):
                table.add_row(
                    "",
                    f"[dim]Confidence: {compression['confidence']:.1%}[/dim]",
                    ""
                )

            panel = Panel(
                table,
                title=f"Compression {i}",
                border_style="magenta",
                expand=False
            )
            self.console.print(panel)

        # Store for export
        self.export_data['compressed_requirements'] = {
            'total': len(compressed),
            'average_savings': self._calculate_average_compression_savings(compressed),
            'details': compressed
        }

    def present_summary(self, analysis_results: Dict[str, Any]):
        """Present an overall summary of all findings."""
        self.console.print("\n" + "="*60)
        self.console.print("[bold cyan]📊 ANALYSIS SUMMARY[/bold cyan]")
        self.console.print("="*60)

        # Create summary table
        summary_table = Table(show_header=True, header_style="bold cyan")
        summary_table.add_column("Category", style="white", width=25)
        summary_table.add_column("Count", justify="right", style="bright_white", width=10)
        summary_table.add_column("Status", style="green", width=15)
        summary_table.add_column("Priority", style="yellow", width=15)

        # Add rows for each category
        categories = [
            ("Edge Cases", len(analysis_results.get('edge_cases', []))),
            ("Contradictions", len(analysis_results.get('contradictions', []))),
            ("Completeness Gaps", len(analysis_results.get('completeness_gaps', []))),
            ("Compressed Requirements", len(analysis_results.get('compressed_requirements', [])))
        ]

        for category, count in categories:
            if count == 0:
                status = "[green]✓ Clean[/green]"
                priority = "[dim]None[/dim]"
            elif count <= 3:
                status = "[yellow]⚠ Minor[/yellow]"
                priority = "[yellow]Review[/yellow]"
            else:
                status = "[red]⚠ Major[/red]"
                priority = "[red]Action Needed[/red]"

            summary_table.add_row(category, str(count), status, priority)

        self.console.print(summary_table)

        # Overall health score
        total_issues = sum(count for _, count in categories)
        if total_issues == 0:
            health_score = 100
            health_color = "green"
            health_status = "Excellent"
        elif total_issues <= 5:
            health_score = 85
            health_color = "yellow"
            health_status = "Good"
        elif total_issues <= 15:
            health_score = 70
            health_color = "orange"
            health_status = "Fair"
        else:
            health_score = 50
            health_color = "red"
            health_status = "Needs Work"

        health_panel = Panel(
            f"[bold {health_color}]{health_score}/100 - {health_status}[/bold {health_color}]\n"
            f"[dim]Total issues to address: {total_issues}[/dim]",
            title="📈 Specification Health Score",
            border_style=health_color,
            expand=False
        )
        self.console.print("\n", health_panel)

    def export_to_json(self, filename: str):
        """Export all findings to JSON format."""
        with open(filename, 'w') as f:
            json.dump(self.export_data, f, indent=2, default=str)

        self.console.print(f"\n💾 [green]Exported findings to {filename}[/green]")

    def export_to_markdown(self, filename: str):
        """Export findings to markdown format."""
        md_content = self._generate_markdown_report()

        with open(filename, 'w') as f:
            f.write(md_content)

        self.console.print(f"\n💾 [green]Exported markdown report to {filename}[/green]")

    def _group_edge_cases_by_priority(self, edge_cases: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group edge cases by priority level."""
        groups = {'high': [], 'medium': [], 'low': []}

        for case in edge_cases:
            priority = case.get('priority', 'medium')
            if priority in groups:
                groups[priority].append(case)
            else:
                groups['medium'].append(case)  # Default to medium

        return groups

    def _get_priority_color(self, priority: str) -> str:
        """Get color for priority level."""
        colors = {
            'high': 'red',
            'medium': 'yellow',
            'low': 'green'
        }
        return colors.get(priority, 'white')

    def _get_severity_color(self, severity: str) -> str:
        """Get color for severity level."""
        colors = {
            'critical': 'bright_red',
            'high': 'red',
            'medium': 'yellow',
            'low': 'green'
        }
        return colors.get(severity, 'white')

    def _get_priority_order(self, priority: str) -> int:
        """Get numeric order for priority sorting."""
        order = {
            'high': 1,
            'medium': 2,
            'low': 3
        }
        return order.get(priority, 2)

    def _calculate_average_compression_savings(self, compressed: List[Dict[str, Any]]) -> float:
        """Calculate average compression savings percentage."""
        if not compressed:
            return 0.0

        total_savings = 0
        valid_compressions = 0

        for compression in compressed:
            original = compression.get('original_requirements', [])
            compressed_req = compression.get('compressed_requirement', '')

            original_length = sum(len(req.get('content', '')) for req in original)
            compressed_length = len(compressed_req)

            if original_length > 0:
                savings = (1 - compressed_length/original_length) * 100
                total_savings += savings
                valid_compressions += 1

        return total_savings / valid_compressions if valid_compressions > 0 else 0.0

    def _generate_markdown_report(self) -> str:
        """Generate a comprehensive markdown report."""
        md = "# Specification Analysis Report\n\n"
        md += f"Generated on: {self._get_current_timestamp()}\n\n"

        # Executive Summary
        md += "## Executive Summary\n\n"
        total_issues = sum([
            self.export_data.get('edge_cases', {}).get('total', 0),
            self.export_data.get('contradictions', {}).get('total', 0),
            self.export_data.get('completeness_gaps', {}).get('total', 0)
        ])

        md += f"- **Total Issues Identified:** {total_issues}\n"
        md += f"- **Edge Cases:** {self.export_data.get('edge_cases', {}).get('total', 0)}\n"
        md += f"- **Contradictions:** {self.export_data.get('contradictions', {}).get('total', 0)}\n"
        md += f"- **Completeness Gaps:** {self.export_data.get('completeness_gaps', {}).get('total', 0)}\n"
        md += f"- **Requirements Compressed:** {self.export_data.get('compressed_requirements', {}).get('total', 0)}\n\n"

        # Detailed sections for each category
        if self.export_data.get('edge_cases'):
            md += self._markdown_section_edge_cases()

        if self.export_data.get('contradictions'):
            md += self._markdown_section_contradictions()

        if self.export_data.get('completeness_gaps'):
            md += self._markdown_section_gaps()

        if self.export_data.get('compressed_requirements'):
            md += self._markdown_section_compressed()

        return md

    def _markdown_section_edge_cases(self) -> str:
        """Generate markdown section for edge cases."""
        md = "## Edge Cases\n\n"

        edge_data = self.export_data['edge_cases']
        details = edge_data.get('details', [])

        for i, case in enumerate(details, 1):
            md += f"### {i}. {case.get('description', 'Unknown edge case')}\n\n"

            if case.get('context'):
                md += f"**Context:** {case['context']}\n\n"

            if case.get('impact'):
                md += f"**Impact:** {case['impact']}\n\n"

            priority = case.get('priority', 'medium')
            md += f"**Priority:** {priority.title()}\n\n"

            if case.get('handled'):
                md += f"**Status:** ✅ Handled\n"
                md += f"**Handling:** {case.get('handling', 'None specified')}\n\n"
            else:
                md += f"**Status:** ⚠️ Not handled\n\n"

        return md

    def _markdown_section_contradictions(self) -> str:
        """Generate markdown section for contradictions."""
        md = "## Contradictions\n\n"

        contradiction_data = self.export_data['contradictions']
        details = contradiction_data.get('details', [])

        for i, contradiction in enumerate(details, 1):
            md += f"### {i}. {contradiction.get('description', 'Unknown contradiction')}\n\n"

            if contradiction.get('conflicting_requirements'):
                md += "**Conflicting Requirements:**\n"
                for req in contradiction['conflicting_requirements']:
                    md += f"- {req}\n"
                md += "\n"

            severity = contradiction.get('severity', 'medium')
            md += f"**Severity:** {severity.title()}\n\n"

            if contradiction.get('impact'):
                md += f"**Impact:** {contradiction['impact']}\n\n"

            if contradiction.get('resolved'):
                md += f"**Status:** ✅ Resolved\n"
                if contradiction.get('resolution'):
                    md += f"**Resolution:** {contradiction['resolution']}\n\n"
            else:
                md += f"**Status:** ⚠️ Unresolved\n\n"

        return md

    def _markdown_section_gaps(self) -> str:
        """Generate markdown section for completeness gaps."""
        md = "## Completeness Gaps\n\n"

        gap_data = self.export_data['completeness_gaps']
        details = gap_data.get('details', [])

        # Group by priority
        priority_groups = {'high': [], 'medium': [], 'low': []}
        for gap in details:
            priority = gap.get('priority', 'medium')
            if priority in priority_groups:
                priority_groups[priority].append(gap)

        for priority in ['high', 'medium', 'low']:
            gaps = priority_groups[priority]
            if not gaps:
                continue

            md += f"### {priority.title()} Priority Gaps\n\n"

            for gap in gaps:
                md += f"- **{gap.get('description', 'Unknown gap')}**\n"
                if gap.get('suggested_requirement'):
                    md += f"  - *Suggestion:* {gap['suggested_requirement']}\n"
                md += "\n"

        return md

    def _markdown_section_compressed(self) -> str:
        """Generate markdown section for compressed requirements."""
        md = "## Compressed Requirements\n\n"

        compressed_data = self.export_data['compressed_requirements']
        details = compressed_data.get('details', [])
        avg_savings = compressed_data.get('average_savings', 0)

        md += f"**Average Compression Savings:** {avg_savings:.1f}%\n\n"

        for i, compression in enumerate(details, 1):
            md += f"### Compression {i}\n\n"

            md += "**Original Requirements:**\n"
            original = compression.get('original_requirements', [])
            for req in original:
                md += f"- {req.get('content', 'Unknown')}\n"

            md += "\n**Compressed To:**\n"
            md += f"{compression.get('compressed_requirement', 'Unknown')}\n\n"

            if compression.get('confidence'):
                md += f"**Confidence:** {compression['confidence']:.1%}\n\n"

        return md

    def _get_current_timestamp(self) -> str:
        """Get current timestamp for reports."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")