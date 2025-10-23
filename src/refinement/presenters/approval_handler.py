"""
Approval Handler - Interactive user decision workflow for specification refinement.

This module manages the user approval process, allowing users to accept, reject,
modify, or provide custom input for suggestions. It implements a smart, non-annoying
interface that respects user time and preferences.
"""

from typing import List, Dict, Any, Optional, Tuple
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, TaskID
import questionary
from datetime import datetime

from ..models import UserFeedback, UserDecision, UserDecisionAction


class ApprovalHandler:
    """
    Manages the interactive approval process for refinement suggestions.

    Provides an intuitive, efficient interface for users to review and make
    decisions on suggestions. Includes smart defaults, batch operations,
    and keyboard shortcuts for power users.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.user_preferences = {
            'auto_accept_threshold': 0.9,  # Auto-accept suggestions above this confidence
            'show_examples': True,
            'batch_mode': False,
            'detailed_explanations': True
        }
        self.session_stats = {
            'total_suggestions': 0,
            'accepted': 0,
            'rejected': 0,
            'modified': 0,
            'custom': 0,
            'auto_accepted': 0
        }

    def process_suggestions(self,
                          suggestions: List[Dict[str, Any]],
                          current_state: Dict[str, Any]) -> UserFeedback:
        """
        Process all suggestions and collect user decisions.

        Args:
            suggestions: Ranked list of suggestions to review
            current_state: Current specification state

        Returns:
            UserFeedback containing all user decisions and overall feedback
        """
        self.session_stats['total_suggestions'] = len(suggestions)

        if not suggestions:
            self.console.print("✅ [green]No suggestions to review - specification looks good![/green]")
            return UserFeedback(
                decisions=[],
                overall_satisfaction=5,
                additional_comments="No suggestions needed",
                wants_to_continue=False
            )

        self.console.print(f"\n🔍 [bold cyan]Reviewing {len(suggestions)} Suggestions[/bold cyan]")
        self.console.print("=" * 50)

        # Get user preferences for this session
        self._configure_session_preferences()

        # Process suggestions with smart batching
        decisions = self._process_suggestions_intelligently(suggestions, current_state)

        # Get overall feedback
        overall_feedback = self._collect_overall_feedback()

        # Show session summary
        self._show_session_summary()

        return UserFeedback(
            decisions=decisions,
            overall_satisfaction=overall_feedback.get('satisfaction'),
            additional_comments=overall_feedback.get('comments'),
            wants_to_continue=overall_feedback.get('continue', True)
        )

    def _configure_session_preferences(self):
        """Configure user preferences for the current session."""
        self.console.print("\n⚙️  [dim]Quick Setup (press Enter for defaults)[/dim]")

        # Auto-accept threshold
        if Confirm.ask("Enable smart auto-accept for high-confidence suggestions?", default=True):
            threshold = IntPrompt.ask(
                "Auto-accept threshold (confidence %)",
                default=90,
                show_default=True
            ) / 100
            self.user_preferences['auto_accept_threshold'] = threshold
        else:
            self.user_preferences['auto_accept_threshold'] = 1.1  # Disable auto-accept

        # Detailed explanations
        self.user_preferences['detailed_explanations'] = Confirm.ask(
            "Show detailed explanations?",
            default=True
        )

        # Batch mode for many suggestions
        if len(self.session_stats.get('total_suggestions', 0)) > 10:
            self.user_preferences['batch_mode'] = Confirm.ask(
                "Use batch mode for similar suggestions?",
                default=True
            )

        self.console.print()

    def _process_suggestions_intelligently(self,
                                         suggestions: List[Dict[str, Any]],
                                         current_state: Dict[str, Any]) -> List[UserDecision]:
        """Process suggestions with intelligent batching and auto-accept."""
        decisions = []

        # Group suggestions for potential batch processing
        suggestion_groups = self._group_suggestions_for_processing(suggestions)

        for group_name, group_suggestions in suggestion_groups.items():
            if group_name == "auto_accept":
                # Auto-accept high-confidence suggestions
                auto_decisions = self._auto_accept_suggestions(group_suggestions)
                decisions.extend(auto_decisions)
            elif group_name == "individual":
                # Process individually
                individual_decisions = self._process_individual_suggestions(group_suggestions, current_state)
                decisions.extend(individual_decisions)
            else:
                # Process as batch
                batch_decisions = self._process_batch_suggestions(group_name, group_suggestions, current_state)
                decisions.extend(batch_decisions)

        return decisions

    def _group_suggestions_for_processing(self,
                                        suggestions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group suggestions for efficient processing."""
        groups = {
            "auto_accept": [],
            "individual": [],
            "edge_cases": [],
            "contradictions": [],
            "completeness": [],
            "compression": []
        }

        for suggestion in suggestions:
            confidence = suggestion.get('confidence', 0.0)
            suggestion_type = suggestion.get('type', 'individual')

            # Auto-accept group
            if confidence >= self.user_preferences['auto_accept_threshold']:
                groups["auto_accept"].append(suggestion)
            # Type-based grouping for batch processing
            elif self.user_preferences['batch_mode']:
                if suggestion_type == 'edge_case_handling':
                    groups["edge_cases"].append(suggestion)
                elif suggestion_type == 'contradiction_resolution':
                    groups["contradictions"].append(suggestion)
                elif suggestion_type == 'completeness_addition':
                    groups["completeness"].append(suggestion)
                elif suggestion_type == 'compression_refinement':
                    groups["compression"].append(suggestion)
                else:
                    groups["individual"].append(suggestion)
            else:
                groups["individual"].append(suggestion)

        # Remove empty groups
        return {k: v for k, v in groups.items() if v}

    def _auto_accept_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[UserDecision]:
        """Auto-accept high-confidence suggestions."""
        if not suggestions:
            return []

        self.console.print(f"\n🤖 [green]Auto-accepting {len(suggestions)} high-confidence suggestions[/green]")

        decisions = []
        for suggestion in suggestions:
            decision = UserDecision(
                suggestion_id=suggestion['id'],
                suggestion=suggestion,
                action=UserDecisionAction.ACCEPT,
                reasoning="Auto-accepted due to high confidence",
                timestamp=datetime.now()
            )
            decisions.append(decision)
            self.session_stats['auto_accepted'] += 1

        # Show summary of auto-accepted suggestions
        if self.user_preferences['detailed_explanations']:
            table = Table(show_header=True, header_style="bold green")
            table.add_column("Type", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Confidence", style="green")

            for suggestion in suggestions[:5]:  # Show first 5
                table.add_row(
                    suggestion.get('type', 'Unknown'),
                    suggestion.get('title', 'No title')[:50] + "...",
                    f"{suggestion.get('confidence', 0):.1%}"
                )

            if len(suggestions) > 5:
                table.add_row("...", f"+ {len(suggestions) - 5} more", "")

            panel = Panel(table, title="Auto-Accepted Suggestions", border_style="green")
            self.console.print(panel)

        return decisions

    def _process_individual_suggestions(self,
                                      suggestions: List[Dict[str, Any]],
                                      current_state: Dict[str, Any]) -> List[UserDecision]:
        """Process suggestions individually with full user interaction."""
        decisions = []

        for i, suggestion in enumerate(suggestions, 1):
            self.console.print(f"\n📋 [bold]Suggestion {i} of {len(suggestions)}[/bold]")
            self._display_suggestion_details(suggestion)

            decision = self._get_user_decision_for_suggestion(suggestion, current_state)
            decisions.append(decision)

            # Update stats
            self._update_session_stats(decision.action)

            # Quick exit check
            if len(decisions) >= 3 and self._should_offer_quick_exit():
                remaining = len(suggestions) - i
                if self._offer_quick_exit(remaining):
                    # Apply default action to remaining suggestions
                    default_decisions = self._apply_default_to_remaining(
                        suggestions[i:], UserDecisionAction.REJECT
                    )
                    decisions.extend(default_decisions)
                    break

        return decisions

    def _process_batch_suggestions(self,
                                 group_name: str,
                                 suggestions: List[Dict[str, Any]],
                                 current_state: Dict[str, Any]) -> List[UserDecision]:
        """Process a batch of similar suggestions."""
        if not suggestions:
            return []

        self.console.print(f"\n📦 [bold yellow]Batch Processing: {group_name.title()}[/bold yellow]")
        self.console.print(f"Found {len(suggestions)} similar suggestions")

        # Show batch summary
        self._display_batch_summary(group_name, suggestions)

        # Get batch decision
        batch_action = self._get_batch_decision(group_name, suggestions)

        if batch_action == "individual":
            # User wants to review individually
            return self._process_individual_suggestions(suggestions, current_state)
        elif batch_action == "all_accept":
            return self._apply_action_to_batch(suggestions, UserDecisionAction.ACCEPT, "Batch accepted")
        elif batch_action == "all_reject":
            return self._apply_action_to_batch(suggestions, UserDecisionAction.REJECT, "Batch rejected")
        else:
            # Custom batch handling
            return self._handle_custom_batch_decision(batch_action, suggestions, current_state)

    def _display_suggestion_details(self, suggestion: Dict[str, Any]):
        """Display detailed information about a suggestion."""
        # Create main information table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Field", style="cyan", width=15)
        table.add_column("Value", style="white")

        table.add_row("Title", suggestion.get('title', 'No title'))
        table.add_row("Type", suggestion.get('type', 'Unknown').replace('_', ' ').title())
        table.add_row("Confidence", f"{suggestion.get('confidence', 0):.1%}")
        table.add_row("Impact", suggestion.get('impact', 'Unknown'))
        table.add_row("Effort", suggestion.get('effort', 'Unknown'))

        # Show rationale if available
        if suggestion.get('rationale') and self.user_preferences['detailed_explanations']:
            table.add_row("Rationale", suggestion['rationale'])

        # Create panel with suggestion details
        panel_content = [table]

        # Add description
        if suggestion.get('description'):
            panel_content.append(Text(f"\n{suggestion['description']}", style="dim"))

        # Add examples if available and requested
        if suggestion.get('examples') and self.user_preferences['show_examples']:
            examples_text = Text("\nExamples:", style="bold")
            for example in suggestion['examples'][:3]:  # Show max 3 examples
                examples_text.append(f"\n• {example}", style="dim")
            panel_content.append(examples_text)

        panel = Panel(
            *panel_content,
            title=f"💡 {suggestion.get('type', 'suggestion').replace('_', ' ').title()}",
            border_style=self._get_suggestion_border_style(suggestion),
            expand=False
        )

        self.console.print(panel)

    def _get_user_decision_for_suggestion(self,
                                        suggestion: Dict[str, Any],
                                        current_state: Dict[str, Any]) -> UserDecision:
        """Get user decision for a single suggestion."""
        # Present choices based on suggestion type
        choices = [
            "✅ Accept",
            "❌ Reject",
            "✏️  Modify",
            "➕ Add Custom",
            "❓ Need More Info"
        ]

        # Add quick shortcuts
        shortcuts = {
            'a': "✅ Accept",
            'r': "❌ Reject",
            'm': "✏️  Modify",
            'c': "➕ Add Custom",
            'i': "❓ Need More Info"
        }

        choice = questionary.select(
            "What would you like to do?",
            choices=choices,
            instruction="(Use arrow keys or shortcuts: a/r/m/c/i)"
        ).ask()

        # Map choice to action
        action_map = {
            "✅ Accept": UserDecisionAction.ACCEPT,
            "❌ Reject": UserDecisionAction.REJECT,
            "✏️  Modify": UserDecisionAction.MODIFY,
            "➕ Add Custom": UserDecisionAction.CUSTOM,
            "❓ Need More Info": UserDecisionAction.CLARIFY
        }

        action = action_map[choice]

        # Handle specific actions
        reasoning = None
        modification = None
        custom_content = None

        if action == UserDecisionAction.ACCEPT:
            reasoning = "Accepted as suggested"

        elif action == UserDecisionAction.REJECT:
            reasoning = Prompt.ask(
                "Why reject? (optional)",
                default="Not applicable"
            )

        elif action == UserDecisionAction.MODIFY:
            modification = self._get_modification_details(suggestion)
            reasoning = "Modified to better fit requirements"

        elif action == UserDecisionAction.CUSTOM:
            custom_content = self._get_custom_content(suggestion)
            reasoning = "Added custom requirement"

        elif action == UserDecisionAction.CLARIFY:
            reasoning = Prompt.ask(
                "What clarification do you need?",
                default="Need more information"
            )

        return UserDecision(
            suggestion_id=suggestion['id'],
            suggestion=suggestion,
            action=action,
            reasoning=reasoning,
            modification=modification,
            custom_content=custom_content,
            timestamp=datetime.now()
        )

    def _get_modification_details(self, suggestion: Dict[str, Any]) -> Dict[str, Any]:
        """Get modification details from user."""
        self.console.print("\n✏️  [yellow]Modifying suggestion...[/yellow]")

        original_content = suggestion.get('content', {})
        modified_content = original_content.copy()

        # Present editable fields based on suggestion type
        suggestion_type = suggestion.get('type', 'unknown')

        if suggestion_type == 'edge_case_handling':
            self._modify_edge_case_suggestion(modified_content)
        elif suggestion_type == 'contradiction_resolution':
            self._modify_contradiction_suggestion(modified_content)
        elif suggestion_type == 'completeness_addition':
            self._modify_completeness_suggestion(modified_content)
        else:
            # Generic modification
            self._modify_generic_suggestion(modified_content)

        return modified_content

    def _modify_edge_case_suggestion(self, content: Dict[str, Any]):
        """Modify edge case handling suggestion."""
        current_handling = content.get('handling_strategy', 'Unknown')
        self.console.print(f"Current handling strategy: [cyan]{current_handling}[/cyan]")

        new_strategy = Prompt.ask(
            "New handling strategy",
            default=current_handling
        )
        content['handling_strategy'] = new_strategy

        if 'implementation' in content:
            new_implementation = Prompt.ask(
                "Implementation details",
                default=content.get('implementation', '')
            )
            content['implementation'] = new_implementation

    def _modify_contradiction_suggestion(self, content: Dict[str, Any]):
        """Modify contradiction resolution suggestion."""
        current_resolution = content.get('resolution_strategy', 'Unknown')
        self.console.print(f"Current resolution: [cyan]{current_resolution}[/cyan]")

        new_resolution = Prompt.ask(
            "New resolution approach",
            default=current_resolution
        )
        content['resolution_strategy'] = new_resolution

    def _modify_completeness_suggestion(self, content: Dict[str, Any]):
        """Modify completeness addition suggestion."""
        current_req = content.get('new_requirement', {}).get('content', '')
        self.console.print(f"Current requirement: [cyan]{current_req}[/cyan]")

        new_req_content = Prompt.ask(
            "Modified requirement",
            default=current_req
        )

        if 'new_requirement' not in content:
            content['new_requirement'] = {}

        content['new_requirement']['content'] = new_req_content

    def _modify_generic_suggestion(self, content: Dict[str, Any]):
        """Modify generic suggestion."""
        # Allow user to modify key fields
        for key, value in content.items():
            if isinstance(value, str) and len(value) < 200:  # Only modify short strings
                new_value = Prompt.ask(
                    f"Modify {key}",
                    default=str(value)
                )
                content[key] = new_value

    def _get_custom_content(self, suggestion: Dict[str, Any]) -> str:
        """Get custom content from user."""
        self.console.print("\n➕ [yellow]Adding custom requirement...[/yellow]")

        # Provide context from the original suggestion
        suggestion_context = suggestion.get('title', 'Related to current suggestion')
        self.console.print(f"Context: [dim]{suggestion_context}[/dim]")

        custom_content = Prompt.ask(
            "Enter your custom requirement or note",
            multiline=True
        )

        return custom_content

    def _display_batch_summary(self, group_name: str, suggestions: List[Dict[str, Any]]):
        """Display summary of batch suggestions."""
        # Create summary table
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("#", width=3)
        table.add_column("Title", width=40)
        table.add_column("Confidence", width=10)
        table.add_column("Impact", width=8)

        for i, suggestion in enumerate(suggestions[:10], 1):  # Show first 10
            table.add_row(
                str(i),
                suggestion.get('title', 'No title')[:35] + ("..." if len(suggestion.get('title', '')) > 35 else ""),
                f"{suggestion.get('confidence', 0):.0%}",
                suggestion.get('impact', 'N/A')
            )

        if len(suggestions) > 10:
            table.add_row("...", f"+ {len(suggestions) - 10} more", "", "")

        panel = Panel(
            table,
            title=f"Batch: {group_name.title()} ({len(suggestions)} suggestions)",
            border_style="yellow"
        )
        self.console.print(panel)

    def _get_batch_decision(self, group_name: str, suggestions: List[Dict[str, Any]]) -> str:
        """Get user decision for batch processing."""
        choices = [
            "🔍 Review individually",
            "✅ Accept all",
            "❌ Reject all",
            "⚡ Smart batch (high confidence only)"
        ]

        # Add group-specific choices
        if group_name == "edge_cases":
            choices.append("🛡️ Accept critical only")
        elif group_name == "contradictions":
            choices.append("⚠️ Accept high-severity only")

        choice = questionary.select(
            f"How would you like to handle these {group_name}?",
            choices=choices
        ).ask()

        # Map choices to actions
        choice_map = {
            "🔍 Review individually": "individual",
            "✅ Accept all": "all_accept",
            "❌ Reject all": "all_reject",
            "⚡ Smart batch (high confidence only)": "smart_batch",
            "🛡️ Accept critical only": "critical_only",
            "⚠️ Accept high-severity only": "high_severity_only"
        }

        return choice_map.get(choice, "individual")

    def _apply_action_to_batch(self,
                             suggestions: List[Dict[str, Any]],
                             action: UserDecisionAction,
                             reasoning: str) -> List[UserDecision]:
        """Apply the same action to all suggestions in batch."""
        decisions = []

        for suggestion in suggestions:
            decision = UserDecision(
                suggestion_id=suggestion['id'],
                suggestion=suggestion,
                action=action,
                reasoning=reasoning,
                timestamp=datetime.now()
            )
            decisions.append(decision)
            self._update_session_stats(action)

        self.console.print(f"✅ Applied {action.value} to {len(suggestions)} suggestions")
        return decisions

    def _handle_custom_batch_decision(self,
                                    batch_action: str,
                                    suggestions: List[Dict[str, Any]],
                                    current_state: Dict[str, Any]) -> List[UserDecision]:
        """Handle custom batch decision logic."""
        decisions = []

        if batch_action == "smart_batch":
            # Accept high confidence, reject low confidence
            high_conf_threshold = 0.8
            for suggestion in suggestions:
                confidence = suggestion.get('confidence', 0.0)
                if confidence >= high_conf_threshold:
                    action = UserDecisionAction.ACCEPT
                    reasoning = f"High confidence ({confidence:.1%})"
                else:
                    action = UserDecisionAction.REJECT
                    reasoning = f"Low confidence ({confidence:.1%})"

                decision = UserDecision(
                    suggestion_id=suggestion['id'],
                    suggestion=suggestion,
                    action=action,
                    reasoning=reasoning,
                    timestamp=datetime.now()
                )
                decisions.append(decision)
                self._update_session_stats(action)

        elif batch_action == "critical_only":
            # Accept only critical/high impact suggestions
            for suggestion in suggestions:
                impact = suggestion.get('impact', 'medium')
                if impact == 'high':
                    action = UserDecisionAction.ACCEPT
                    reasoning = "High impact edge case"
                else:
                    action = UserDecisionAction.REJECT
                    reasoning = f"Lower impact ({impact})"

                decision = UserDecision(
                    suggestion_id=suggestion['id'],
                    suggestion=suggestion,
                    action=action,
                    reasoning=reasoning,
                    timestamp=datetime.now()
                )
                decisions.append(decision)
                self._update_session_stats(action)

        return decisions

    def _should_offer_quick_exit(self) -> bool:
        """Determine if we should offer quick exit based on user patterns."""
        total_processed = (
            self.session_stats['accepted'] +
            self.session_stats['rejected'] +
            self.session_stats['modified']
        )

        if total_processed < 3:
            return False

        # If user is rejecting most suggestions, offer quick exit
        rejection_rate = self.session_stats['rejected'] / total_processed
        return rejection_rate > 0.7

    def _offer_quick_exit(self, remaining_count: int) -> bool:
        """Offer user option to quick-exit with default action."""
        self.console.print(f"\n⚡ [yellow]Quick Exit Available[/yellow]")
        self.console.print(f"You have {remaining_count} suggestions remaining.")
        self.console.print("Based on your patterns, you might want to apply a default action.")

        return Confirm.ask(
            f"Apply 'reject' to remaining {remaining_count} suggestions?",
            default=True
        )

    def _apply_default_to_remaining(self,
                                  suggestions: List[Dict[str, Any]],
                                  default_action: UserDecisionAction) -> List[UserDecision]:
        """Apply default action to remaining suggestions."""
        decisions = []

        for suggestion in suggestions:
            decision = UserDecision(
                suggestion_id=suggestion['id'],
                suggestion=suggestion,
                action=default_action,
                reasoning="Applied via quick exit",
                timestamp=datetime.now()
            )
            decisions.append(decision)
            self._update_session_stats(default_action)

        return decisions

    def _collect_overall_feedback(self) -> Dict[str, Any]:
        """Collect overall feedback from user."""
        self.console.print("\n📝 [bold cyan]Overall Feedback[/bold cyan]")

        # Satisfaction rating
        satisfaction = questionary.select(
            "How satisfied are you with the suggestions?",
            choices=[
                "😍 Very satisfied (5/5)",
                "😊 Satisfied (4/5)",
                "😐 Neutral (3/5)",
                "😕 Unsatisfied (2/5)",
                "😞 Very unsatisfied (1/5)"
            ]
        ).ask()

        satisfaction_map = {
            "😍 Very satisfied (5/5)": 5,
            "😊 Satisfied (4/5)": 4,
            "😐 Neutral (3/5)": 3,
            "😕 Unsatisfied (2/5)": 2,
            "😞 Very unsatisfied (1/5)": 1
        }

        satisfaction_score = satisfaction_map.get(satisfaction, 3)

        # Additional comments
        comments = Prompt.ask(
            "Any additional comments or feedback? (optional)",
            default=""
        )

        # Continue refinement?
        wants_to_continue = True
        if satisfaction_score >= 4:
            wants_to_continue = Confirm.ask(
                "Would you like to continue refining?",
                default=False  # If satisfied, default to not continuing
            )
        else:
            wants_to_continue = Confirm.ask(
                "Would you like another refinement iteration?",
                default=True  # If not satisfied, default to continuing
            )

        return {
            'satisfaction': satisfaction_score,
            'comments': comments,
            'continue': wants_to_continue
        }

    def _show_session_summary(self):
        """Show summary of the approval session."""
        stats = self.session_stats
        total = stats['total_suggestions']

        if total == 0:
            return

        self.console.print("\n📊 [bold cyan]Session Summary[/bold cyan]")

        # Create summary table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Action", style="white")
        table.add_column("Count", justify="right", style="bright_white")
        table.add_column("Percentage", justify="right", style="dim")

        actions = [
            ("Accepted", stats['accepted'], "green"),
            ("Auto-accepted", stats['auto_accepted'], "bright_green"),
            ("Modified", stats['modified'], "yellow"),
            ("Rejected", stats['rejected'], "red"),
            ("Custom", stats['custom'], "magenta")
        ]

        for action_name, count, color in actions:
            if count > 0:
                percentage = (count / total) * 100
                table.add_row(
                    f"[{color}]{action_name}[/{color}]",
                    str(count),
                    f"{percentage:.1f}%"
                )

        self.console.print(table)

        # Overall acceptance rate
        accepted_total = stats['accepted'] + stats['auto_accepted'] + stats['modified']
        acceptance_rate = (accepted_total / total) * 100

        if acceptance_rate >= 70:
            rate_color = "green"
            rate_emoji = "✅"
        elif acceptance_rate >= 40:
            rate_color = "yellow"
            rate_emoji = "⚠️"
        else:
            rate_color = "red"
            rate_emoji = "❌"

        self.console.print(f"\n{rate_emoji} [bold {rate_color}]Overall Acceptance Rate: {acceptance_rate:.1f}%[/bold {rate_color}]")

    def _update_session_stats(self, action: UserDecisionAction):
        """Update session statistics."""
        if action == UserDecisionAction.ACCEPT:
            self.session_stats['accepted'] += 1
        elif action == UserDecisionAction.REJECT:
            self.session_stats['rejected'] += 1
        elif action == UserDecisionAction.MODIFY:
            self.session_stats['modified'] += 1
        elif action == UserDecisionAction.CUSTOM:
            self.session_stats['custom'] += 1

    def _get_suggestion_border_style(self, suggestion: Dict[str, Any]) -> str:
        """Get border style based on suggestion properties."""
        confidence = suggestion.get('confidence', 0.0)
        impact = suggestion.get('impact', 'medium')

        if confidence >= 0.9 and impact == 'high':
            return "bright_green"
        elif confidence >= 0.8:
            return "green"
        elif confidence >= 0.6:
            return "yellow"
        else:
            return "red"