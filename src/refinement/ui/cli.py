"""
CLI Interface - Rich interactive prompts and session management for refinement.

This module provides a beautiful, intuitive command-line interface for the
interactive refinement process. Features keyboard shortcuts, progress tracking,
session management, and multi-format export capabilities.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
import questionary
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
from datetime import datetime
import sys

from ..interactive_loop import RefinementLoop
from ..presenters.finding_presenter import FindingPresenter
from ..presenters.suggestion_generator import SuggestionGenerator
from ..presenters.approval_handler import ApprovalHandler
from ..models import FinalizedSpecification


class RefinementCLI:
    """
    Rich CLI interface for interactive specification refinement.

    Provides an intuitive, efficient interface with progress tracking,
    session management, and export capabilities.
    """

    def __init__(self):
        self.console = Console()
        self.current_session = None
        self.session_dir = Path.home() / ".specify" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def run_refinement(self,
                      refined_spec,
                      session_id: Optional[str] = None,
                      export_format: str = "json") -> FinalizedSpecification:
        """
        Run the interactive refinement process with rich CLI interface.

        Args:
            refined_spec: RefinedSpecification from Phase 2
            session_id: Optional session ID to resume
            export_format: Format for final export (json, markdown, yaml)

        Returns:
            FinalizedSpecification ready for Phase 4
        """
        try:
            # Initialize the refinement system
            self._show_welcome_banner()

            # Setup components
            presenter = FindingPresenter(self.console)
            suggestion_generator = SuggestionGenerator()
            approval_handler = ApprovalHandler(self.console)

            refinement_loop = RefinementLoop(
                presenter=presenter,
                suggestion_generator=suggestion_generator,
                approval_handler=approval_handler,
                session_dir=self.session_dir
            )

            # Handle session management
            if session_id:
                self._show_session_resume(session_id)
            else:
                session_id = self._handle_session_selection(refinement_loop)

            # Run the main refinement process
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
                transient=True
            ) as progress:

                # Initialize progress task
                task = progress.add_task(
                    "Starting refinement...",
                    total=100
                )

                # Start refinement
                progress.update(task, advance=10, description="Analyzing specification...")

                finalized_spec = refinement_loop.start_refinement(
                    refined_spec=refined_spec,
                    session_id=session_id
                )

                progress.update(task, advance=90, description="Finalizing specification...")

            # Show completion and export
            self._show_completion_summary(finalized_spec)
            self._handle_export(finalized_spec, export_format)

            return finalized_spec

        except KeyboardInterrupt:
            self._handle_interruption()
            return None

        except Exception as e:
            self._handle_error(e)
            return None

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available refinement sessions."""
        self._show_sessions_banner()

        refinement_loop = RefinementLoop(
            presenter=FindingPresenter(),
            suggestion_generator=SuggestionGenerator(),
            approval_handler=ApprovalHandler(),
            session_dir=self.session_dir
        )

        sessions = refinement_loop.list_sessions()

        if not sessions:
            self.console.print("📭 [yellow]No refinement sessions found[/yellow]")
            self.console.print("   Start a new refinement to create your first session.")
            return []

        # Display sessions in a nice table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Session ID", style="bright_white", width=12)
        table.add_column("Created", style="cyan", width=20)
        table.add_column("Status", style="green", width=12)
        table.add_column("Iterations", justify="right", style="yellow", width=10)
        table.add_column("Last Modified", style="dim", width=20)

        for session in sessions:
            # Format status
            status = "✅ Finalized" if session.get('is_finalized') else "🔄 In Progress"

            # Format dates
            created_at = session.get('created_at', 'Unknown')
            if created_at != 'Unknown':
                try:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_str = created_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    created_str = created_at[:16]  # Fallback
            else:
                created_str = 'Unknown'

            # Format last modified
            last_modified = session.get('last_modified', 0)
            if last_modified:
                modified_dt = datetime.fromtimestamp(last_modified)
                modified_str = modified_dt.strftime('%Y-%m-%d %H:%M')
            else:
                modified_str = 'Unknown'

            table.add_row(
                session['session_id'][:8] + "...",
                created_str,
                status,
                str(session.get('iterations', 0)),
                modified_str
            )

        panel = Panel(
            table,
            title="🗂️  Refinement Sessions",
            border_style="cyan"
        )
        self.console.print(panel)

        return sessions

    def resume_session(self, session_id: str):
        """Resume a specific refinement session."""
        self.console.print(f"🔄 [cyan]Resuming session {session_id[:8]}...[/cyan]")

        try:
            # Load and show session info
            session_file = self.session_dir / f"{session_id}.json"

            if not session_file.exists():
                self.console.print(f"❌ [red]Session {session_id} not found[/red]")
                return None

            with open(session_file, 'r') as f:
                session_data = json.load(f)

            # Show session summary
            self._show_session_info(session_data)

            if Confirm.ask("Continue with this session?", default=True):
                return self.run_refinement(
                    refined_spec=session_data.get('original_spec'),
                    session_id=session_id
                )

        except Exception as e:
            self.console.print(f"❌ [red]Error resuming session: {e}[/red]")
            return None

    def export_session(self, session_id: str, format_type: str = "json", output_path: Optional[str] = None):
        """Export a finalized session to various formats."""
        try:
            session_file = self.session_dir / f"{session_id}.json"

            if not session_file.exists():
                self.console.print(f"❌ [red]Session {session_id} not found[/red]")
                return

            with open(session_file, 'r') as f:
                session_data = json.load(f)

            if not session_data.get('is_finalized', False):
                self.console.print(f"⚠️  [yellow]Session is not finalized yet[/yellow]")
                if not Confirm.ask("Export anyway?", default=False):
                    return

            # Determine output path
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"specification_{session_id[:8]}_{timestamp}.{format_type}"

            # Export based on format
            if format_type == "json":
                self._export_json(session_data, output_path)
            elif format_type == "markdown":
                self._export_markdown(session_data, output_path)
            elif format_type == "yaml":
                self._export_yaml(session_data, output_path)
            else:
                self.console.print(f"❌ [red]Unsupported format: {format_type}[/red]")
                return

            self.console.print(f"✅ [green]Exported to {output_path}[/green]")

        except Exception as e:
            self.console.print(f"❌ [red]Export failed: {e}[/red]")

    def _show_welcome_banner(self):
        """Show welcome banner for refinement process."""
        banner_text = Text()
        banner_text.append("🔄 INTERACTIVE REFINEMENT\n", style="bold cyan")
        banner_text.append("Collaborate with AI to perfect your specification", style="dim")

        panel = Panel(
            banner_text,
            title="Phase 3: Interactive Refinement",
            border_style="cyan",
            padding=(1, 2)
        )

        self.console.print("\n", panel)

    def _show_sessions_banner(self):
        """Show banner for session management."""
        banner_text = Text()
        banner_text.append("🗂️  SESSION MANAGEMENT\n", style="bold cyan")
        banner_text.append("Manage your refinement sessions", style="dim")

        panel = Panel(
            banner_text,
            title="Refinement Sessions",
            border_style="cyan",
            padding=(1, 2)
        )

        self.console.print("\n", panel)

    def _show_session_resume(self, session_id: str):
        """Show session resume information."""
        self.console.print(f"\n🔄 [cyan]Resuming refinement session[/cyan]")
        self.console.print(f"   Session ID: [bright_white]{session_id[:8]}...[/bright_white]")

    def _handle_session_selection(self, refinement_loop: RefinementLoop) -> Optional[str]:
        """Handle session selection or creation."""
        existing_sessions = refinement_loop.list_sessions()

        if existing_sessions:
            # Show option to resume or create new
            choices = [
                "🆕 Start new session",
                "🔄 Resume existing session",
                "📋 List all sessions"
            ]

            choice = questionary.select(
                "What would you like to do?",
                choices=choices
            ).ask()

            if choice == "🔄 Resume existing session":
                return self._select_session_to_resume(existing_sessions)
            elif choice == "📋 List all sessions":
                self.list_sessions()
                return self._handle_session_selection(refinement_loop)  # Ask again

        # Default: create new session
        self.console.print("🆕 [green]Starting new refinement session[/green]")
        return None

    def _select_session_to_resume(self, sessions: List[Dict[str, Any]]) -> Optional[str]:
        """Let user select a session to resume."""
        if not sessions:
            return None

        # Prepare choices
        choices = []
        for session in sessions[:10]:  # Show max 10 recent sessions
            session_id = session['session_id']
            created_at = session.get('created_at', 'Unknown')
            status = "✅" if session.get('is_finalized') else "🔄"
            iterations = session.get('iterations', 0)

            choice_text = f"{status} {session_id[:8]}... ({iterations} iterations) - {created_at[:10]}"
            choices.append((choice_text, session_id))

        choices.append(("❌ Cancel", None))

        # Get selection
        choice_texts = [choice[0] for choice in choices]
        selected = questionary.select(
            "Select session to resume:",
            choices=choice_texts
        ).ask()

        # Find corresponding session ID
        for choice_text, session_id in choices:
            if choice_text == selected:
                return session_id

        return None

    def _show_session_info(self, session_data: Dict[str, Any]):
        """Show detailed information about a session."""
        # Create info table
        table = Table(show_header=False, box=None)
        table.add_column("Field", style="cyan", width=15)
        table.add_column("Value", style="white")

        session_id = session_data.get('session_id', 'Unknown')
        created_at = session_data.get('created_at', 'Unknown')
        is_finalized = session_data.get('is_finalized', False)
        iterations = len(session_data.get('iterations', []))

        table.add_row("Session ID", session_id[:16] + "...")
        table.add_row("Created", created_at[:19] if created_at != 'Unknown' else 'Unknown')
        table.add_row("Status", "✅ Finalized" if is_finalized else "🔄 In Progress")
        table.add_row("Iterations", str(iterations))

        if session_data.get('finalized_spec'):
            finalized_spec = session_data['finalized_spec']
            confidence = finalized_spec.get('confidence_score', 0)
            requirements_count = len(finalized_spec.get('requirements', []))

            table.add_row("Confidence", f"{confidence:.1%}")
            table.add_row("Requirements", str(requirements_count))

        panel = Panel(
            table,
            title="📋 Session Information",
            border_style="cyan"
        )

        self.console.print(panel)

    def _show_completion_summary(self, finalized_spec: FinalizedSpecification):
        """Show completion summary with key metrics."""
        if not finalized_spec:
            return

        self.console.print("\n🎉 [bold green]Refinement Complete![/bold green]")

        # Create summary table
        table = Table(show_header=True, header_style="bold green")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bright_white")
        table.add_column("Status", style="green")

        # Add key metrics
        confidence = finalized_spec.confidence_score
        requirements_count = len(finalized_spec.requirements)
        acceptance_rate = finalized_spec.user_acceptance_rate
        iterations = finalized_spec.total_iterations

        table.add_row(
            "Confidence Score",
            f"{confidence:.1%}",
            "✅ High" if confidence >= 0.8 else "⚠️ Medium" if confidence >= 0.6 else "❌ Low"
        )

        table.add_row(
            "Requirements",
            str(requirements_count),
            "✅ Complete" if finalized_spec.complete_requirement_set else "⚠️ Partial"
        )

        table.add_row(
            "User Acceptance",
            f"{acceptance_rate:.1%}",
            "✅ High" if acceptance_rate >= 0.7 else "⚠️ Medium" if acceptance_rate >= 0.5 else "❌ Low"
        )

        table.add_row(
            "Refinement Iterations",
            str(iterations),
            "✅ Efficient" if iterations <= 3 else "⚠️ Extended"
        )

        # Execution readiness
        readiness = finalized_spec.get_execution_readiness()
        ready_status = "✅ Ready" if readiness['ready_for_execution'] else "❌ Not Ready"

        table.add_row(
            "Execution Ready",
            f"{readiness['readiness_score']:.1%}",
            ready_status
        )

        panel = Panel(
            table,
            title="📊 Refinement Summary",
            border_style="green"
        )

        self.console.print(panel)

        # Show any blockers
        if readiness.get('blockers'):
            self.console.print("\n⚠️  [yellow]Execution Blockers:[/yellow]")
            for blocker in readiness['blockers']:
                self.console.print(f"   • {blocker}")

        # Show recommendations
        if readiness.get('recommendations'):
            self.console.print("\n💡 [cyan]Recommendations:[/cyan]")
            for rec in readiness['recommendations']:
                self.console.print(f"   • {rec}")

    def _handle_export(self, finalized_spec: FinalizedSpecification, export_format: str):
        """Handle specification export."""
        if not finalized_spec:
            return

        self.console.print(f"\n💾 [cyan]Exporting specification...[/cyan]")

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = finalized_spec.refinement_session_id[:8]
        filename = f"finalized_spec_{session_id}_{timestamp}.{export_format}"

        try:
            export_content = finalized_spec.export_to_format(export_format)

            with open(filename, 'w') as f:
                f.write(export_content)

            self.console.print(f"✅ [green]Exported to {filename}[/green]")

            # Offer to open file
            if Confirm.ask("View exported file?", default=False):
                self._show_export_preview(export_content, export_format)

        except Exception as e:
            self.console.print(f"❌ [red]Export failed: {e}[/red]")

    def _show_export_preview(self, content: str, format_type: str):
        """Show preview of exported content."""
        # Limit preview length
        preview_content = content[:2000]
        if len(content) > 2000:
            preview_content += "\n... (truncated)"

        # Apply syntax highlighting based on format
        if format_type == "json":
            from rich.syntax import Syntax
            syntax = Syntax(preview_content, "json", theme="monokai", line_numbers=True)
            panel = Panel(syntax, title="JSON Export Preview", border_style="blue")
        else:
            panel = Panel(preview_content, title=f"{format_type.upper()} Export Preview", border_style="blue")

        self.console.print(panel)

    def _handle_interruption(self):
        """Handle keyboard interruption gracefully."""
        self.console.print("\n\n⚠️  [yellow]Refinement interrupted![/yellow]")
        self.console.print("   Your progress has been saved automatically.")
        self.console.print("   Use 'specify resume <session-id>' to continue later.")

    def _handle_error(self, error: Exception):
        """Handle unexpected errors."""
        self.console.print(f"\n❌ [red]Unexpected error occurred:[/red]")
        self.console.print(f"   {str(error)}")

        if Confirm.ask("Show detailed error information?", default=False):
            import traceback
            self.console.print("\n[dim]" + traceback.format_exc() + "[/dim]")

    def _export_json(self, session_data: Dict[str, Any], output_path: str):
        """Export session data as JSON."""
        with open(output_path, 'w') as f:
            json.dump(session_data, f, indent=2, default=str)

    def _export_markdown(self, session_data: Dict[str, Any], output_path: str):
        """Export session data as Markdown."""
        # Generate markdown content
        finalized_spec_data = session_data.get('finalized_spec', {})

        if finalized_spec_data:
            # Create FinalizedSpecification object for markdown export
            finalized_spec = FinalizedSpecification.from_dict(finalized_spec_data)
            markdown_content = finalized_spec._to_markdown()
        else:
            # Fallback markdown generation
            markdown_content = self._generate_fallback_markdown(session_data)

        with open(output_path, 'w') as f:
            f.write(markdown_content)

    def _export_yaml(self, session_data: Dict[str, Any], output_path: str):
        """Export session data as YAML."""
        try:
            import yaml
            with open(output_path, 'w') as f:
                yaml.dump(session_data, f, default_flow_style=False, indent=2)
        except ImportError:
            self.console.print("❌ [red]PyYAML not installed. Install with: pip install PyYAML[/red]")
            raise

    def _generate_fallback_markdown(self, session_data: Dict[str, Any]) -> str:
        """Generate basic markdown for non-finalized sessions."""
        session_id = session_data.get('session_id', 'Unknown')
        created_at = session_data.get('created_at', 'Unknown')
        iterations = len(session_data.get('iterations', []))

        md = f"""# Refinement Session Report

**Session ID:** {session_id}
**Created:** {created_at}
**Iterations:** {iterations}
**Status:** {'Finalized' if session_data.get('is_finalized') else 'In Progress'}

## Current State

This session is not yet finalized. To complete the refinement process,
resume the session using:

```
specify resume {session_id}
```

## Session History

"""

        # Add iteration history if available
        for i, iteration in enumerate(session_data.get('iterations', []), 1):
            md += f"### Iteration {i}\n\n"
            md += f"- Suggestions: {iteration.get('suggestions_presented', 0)}\n"
            md += f"- Changes Applied: {iteration.get('changes_applied', 0)}\n"
            md += f"- Timestamp: {iteration.get('timestamp', 'Unknown')}\n\n"

        return md


# CLI Commands using Click
@click.group()
def refinement_cli():
    """Interactive Specification Refinement CLI."""
    pass


@refinement_cli.command()
@click.option('--session-id', help='Resume specific session')
@click.option('--export-format', default='json', type=click.Choice(['json', 'markdown', 'yaml']),
              help='Export format for finalized specification')
@click.argument('spec_file', type=click.Path(exists=True))
def refine(spec_file, session_id, export_format):
    """Start interactive refinement of a specification."""
    cli = RefinementCLI()

    # Load specification (this would be integrated with Phase 2 output)
    try:
        with open(spec_file, 'r') as f:
            spec_data = json.load(f)

        # This would normally be a RefinedSpecification object from Phase 2
        finalized_spec = cli.run_refinement(
            refined_spec=spec_data,
            session_id=session_id,
            export_format=export_format
        )

        if finalized_spec:
            click.echo(f"✅ Refinement completed successfully!")
        else:
            click.echo("⚠️  Refinement was interrupted or failed.")

    except Exception as e:
        click.echo(f"❌ Error: {e}")


@refinement_cli.command()
def sessions():
    """List all refinement sessions."""
    cli = RefinementCLI()
    cli.list_sessions()


@refinement_cli.command()
@click.argument('session_id')
def resume(session_id):
    """Resume a specific refinement session."""
    cli = RefinementCLI()
    result = cli.resume_session(session_id)

    if result:
        click.echo("✅ Session resumed and completed!")
    else:
        click.echo("⚠️  Session could not be resumed.")


@refinement_cli.command()
@click.argument('session_id')
@click.option('--format', 'format_type', default='json',
              type=click.Choice(['json', 'markdown', 'yaml']),
              help='Export format')
@click.option('--output', 'output_path', help='Output file path')
def export(session_id, format_type, output_path):
    """Export a refinement session."""
    cli = RefinementCLI()
    cli.export_session(session_id, format_type, output_path)


if __name__ == "__main__":
    refinement_cli()