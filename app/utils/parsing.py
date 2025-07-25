"""
Parsing utilities for processing LLM responses and structured data.
"""

import re
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from app.core.logging import logger


class LLMResponseParser:
    """Utility class for parsing LLM responses into structured data."""
    
    @staticmethod
    def parse_idea_generation_response(response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response for idea generation into structured ideas.
        
        Args:
            response: Raw LLM response
            
        Returns:
            List of parsed ideas
        """
        try:
            ideas = []
            
            # Try to extract structured ideas from response
            # Look for numbered lists or bullet points
            idea_sections = LLMResponseParser._extract_idea_sections(response)
            
            for i, section in enumerate(idea_sections):
                idea = LLMResponseParser._parse_single_idea(section, i + 1)
                if idea:
                    ideas.append(idea)
            
            # If no structured ideas found, create a single idea from the response
            if not ideas and response.strip():
                ideas.append({
                    "title": LLMResponseParser._extract_title_from_text(response),
                    "description": response[:500] + "..." if len(response) > 500 else response,
                    "key_benefits": LLMResponseParser._extract_benefits(response),
                    "implementation_approach": LLMResponseParser._extract_implementation(response),
                    "potential_challenges": LLMResponseParser._extract_challenges(response),
                    "success_metrics": LLMResponseParser._extract_metrics(response),
                    "confidence_score": 0.7  # Default confidence
                })
            
            logger.debug(f"Parsed {len(ideas)} ideas from LLM response")
            return ideas
            
        except Exception as e:
            logger.error(f"Error parsing idea generation response: {e}")
            return []
    
    @staticmethod
    def parse_evaluation_response(response: str) -> Dict[str, Any]:
        """
        Parse LLM response for idea evaluation into structured evaluation.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Structured evaluation data
        """
        try:
            evaluation = {
                "overall_score": LLMResponseParser._extract_overall_score(response),
                "criterion_scores": LLMResponseParser._extract_criterion_scores(response),
                "strengths": LLMResponseParser._extract_strengths(response),
                "weaknesses": LLMResponseParser._extract_weaknesses(response),
                "recommendations": LLMResponseParser._extract_recommendations(response),
                "risks": LLMResponseParser._extract_risks(response),
                "success_probability": LLMResponseParser._extract_success_probability(response),
                "confidence": LLMResponseParser._extract_confidence(response)
            }
            
            logger.debug("Parsed evaluation response into structured data")
            return evaluation
            
        except Exception as e:
            logger.error(f"Error parsing evaluation response: {e}")
            return {}
    
    @staticmethod
    def parse_iteration_response(response: str, original_title: str) -> Dict[str, Any]:
        """
        Parse LLM response for idea iteration.
        
        Args:
            response: Raw LLM response
            original_title: Original idea title
            
        Returns:
            Structured iteration data
        """
        try:
            iteration = {
                "improved_title": LLMResponseParser._extract_improved_title(response, original_title),
                "improved_description": LLMResponseParser._extract_improved_description(response),
                "changes_made": LLMResponseParser._extract_changes_made(response),
                "improvement_summary": LLMResponseParser._extract_improvement_summary(response),
                "implementation_updates": LLMResponseParser._extract_implementation_updates(response)
            }
            
            logger.debug("Parsed iteration response into structured data")
            return iteration
            
        except Exception as e:
            logger.error(f"Error parsing iteration response: {e}")
            return {}
    
    # Private helper methods for parsing
    
    @staticmethod
    def _extract_idea_sections(response: str) -> List[str]:
        """Extract individual idea sections from response."""
        # Look for numbered ideas
        numbered_pattern = r'(?:^|\n)(?:\d+\.|\d+\)|\*|\-)\s*(.+?)(?=(?:\n\d+\.|\n\d+\)|\n\*|\n\-|$))'
        sections = re.findall(numbered_pattern, response, re.MULTILINE | re.DOTALL)
        
        if not sections:
            # Try to split by paragraphs
            paragraphs = response.split('\n\n')
            sections = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 50]
        
        return sections[:10]  # Limit to 10 ideas max
    
    @staticmethod
    def _parse_single_idea(section: str, index: int) -> Optional[Dict[str, Any]]:
        """Parse a single idea section."""
        if len(section.strip()) < 20:
            return None
        
        return {
            "title": LLMResponseParser._extract_title_from_text(section) or f"Generated Idea {index}",
            "description": section[:800] + "..." if len(section) > 800 else section,
            "key_benefits": LLMResponseParser._extract_benefits(section),
            "implementation_approach": LLMResponseParser._extract_implementation(section),
            "potential_challenges": LLMResponseParser._extract_challenges(section),
            "success_metrics": LLMResponseParser._extract_metrics(section),
            "confidence_score": 0.75  # Default confidence
        }
    
    @staticmethod
    def _extract_title_from_text(text: str) -> str:
        """Extract title from text."""
        # Look for title patterns
        title_patterns = [
            r'^(?:Title|Idea):?\s*(.+?)(?:\n|$)',
            r'^(.+?)(?:\n|$)',  # First line
            r'(?:^|\n)(?:\d+\.|\*|\-)\s*(.+?)(?:\n|$)'  # Numbered/bulleted first line
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text.strip(), re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                if len(title) > 10 and len(title) < 200:
                    return title
        
        # Fallback: use first 100 characters
        words = text.strip().split()
        title = " ".join(words[:15])
        return title[:100] + "..." if len(title) > 100 else title
    
    @staticmethod
    def _extract_benefits(text: str) -> List[str]:
        """Extract benefits from text."""
        benefit_patterns = [
            r'(?:benefits?|advantages?):?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'(?:pros?):?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'(?:\*|\-|\d+\.)\s*(.+benefit.+?)(?:\n|$)'
        ]
        
        benefits = []
        for pattern in benefit_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Split by bullets or numbers
                items = re.split(r'(?:\*|\-|\d+\.)\s*', match)
                benefits.extend([item.strip() for item in items if item.strip()])
        
        return benefits[:8]  # Limit to 8 benefits
    
    @staticmethod
    def _extract_implementation(text: str) -> str:
        """Extract implementation approach from text."""
        impl_patterns = [
            r'(?:implementation|approach|how to|steps?):?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'(?:execute|build|develop):?\s*(.+?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in impl_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                impl = match.group(1).strip()
                if len(impl) > 20:
                    return impl[:500] + "..." if len(impl) > 500 else impl
        
        return "Implementation details would need to be developed based on specific requirements."
    
    @staticmethod
    def _extract_challenges(text: str) -> List[str]:
        """Extract challenges from text."""
        challenge_patterns = [
            r'(?:challenges?|risks?|obstacles?|problems?):?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'(?:cons?|disadvantages?):?\s*(.+?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        challenges = []
        for pattern in challenge_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                items = re.split(r'(?:\*|\-|\d+\.)\s*', match)
                challenges.extend([item.strip() for item in items if item.strip()])
        
        return challenges[:6]  # Limit to 6 challenges
    
    @staticmethod
    def _extract_metrics(text: str) -> List[str]:
        """Extract success metrics from text."""
        metric_patterns = [
            r'(?:metrics?|kpis?|measures?|indicators?):?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'(?:success|track|measure):?\s*(.+?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        metrics = []
        for pattern in metric_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                items = re.split(r'(?:\*|\-|\d+\.)\s*', match)
                metrics.extend([item.strip() for item in items if item.strip()])
        
        return metrics[:8]  # Limit to 8 metrics
    
    @staticmethod
    def _extract_overall_score(text: str) -> float:
        """Extract overall score from evaluation text."""
        score_patterns = [
            r'(?:overall|total|final)\s*score:?\s*(\d+(?:\.\d+)?)',
            r'score:?\s*(\d+(?:\.\d+)?)\s*(?:/\s*10|out\s*of\s*10)',
            r'(\d+(?:\.\d+)?)\s*/\s*10'
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    return min(max(score, 0.0), 10.0)  # Clamp between 0 and 10
                except ValueError:
                    continue
        
        return 7.0  # Default score
    
    @staticmethod
    def _extract_criterion_scores(text: str) -> List[Dict[str, Any]]:
        """Extract individual criterion scores."""
        # This is a simplified implementation
        criteria = ["Feasibility", "Impact", "Innovation", "Market Fit"]
        scores = []
        
        for criterion in criteria:
            pattern = rf'{criterion}:?\s*(\d+(?:\.\d+)?)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    scores.append({
                        "criterion": criterion,
                        "score": min(max(score, 0.0), 10.0),
                        "justification": f"Analysis based on {criterion.lower()} assessment"
                    })
                except ValueError:
                    continue
        
        return scores
    
    @staticmethod
    def _extract_strengths(text: str) -> List[str]:
        """Extract strengths from evaluation text."""
        return LLMResponseParser._extract_list_items(text, ["strength", "pro", "advantage", "positive"])
    
    @staticmethod
    def _extract_weaknesses(text: str) -> List[str]:
        """Extract weaknesses from evaluation text."""
        return LLMResponseParser._extract_list_items(text, ["weakness", "con", "disadvantage", "negative", "limitation"])
    
    @staticmethod
    def _extract_recommendations(text: str) -> List[str]:
        """Extract recommendations from evaluation text."""
        return LLMResponseParser._extract_list_items(text, ["recommend", "suggest", "improve", "enhance"])
    
    @staticmethod
    def _extract_risks(text: str) -> List[str]:
        """Extract risks from evaluation text."""
        return LLMResponseParser._extract_list_items(text, ["risk", "threat", "concern", "issue"])
    
    @staticmethod
    def _extract_list_items(text: str, keywords: List[str]) -> List[str]:
        """Extract list items based on keywords."""
        items = []
        
        for keyword in keywords:
            pattern = rf'(?:{keyword}s?):?\s*(.+?)(?=\n\n|\n[A-Z]|$)'
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                list_items = re.split(r'(?:\*|\-|\d+\.)\s*', match)
                items.extend([item.strip() for item in list_items if item.strip() and len(item.strip()) > 10])
        
        return list(set(items))[:8]  # Remove duplicates and limit
    
    @staticmethod
    def _extract_success_probability(text: str) -> float:
        """Extract success probability from text."""
        prob_patterns = [
            r'(?:success|probability):?\s*(\d+(?:\.\d+)?)%',
            r'(\d+(?:\.\d+)?)%\s*(?:chance|probability|success)',
            r'probability:?\s*(\d+(?:\.\d+)?)'
        ]
        
        for pattern in prob_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    prob = float(match.group(1))
                    # If it's a percentage, convert to decimal
                    if prob > 1:
                        prob = prob / 100
                    return min(max(prob, 0.0), 1.0)
                except ValueError:
                    continue
        
        return 0.6  # Default probability
    
    @staticmethod
    def _extract_confidence(text: str) -> float:
        """Extract confidence level from text."""
        conf_patterns = [
            r'confidence:?\s*(\d+(?:\.\d+)?)%',
            r'(\d+(?:\.\d+)?)%\s*confident',
            r'confidence:?\s*(\d+(?:\.\d+)?)'
        ]
        
        for pattern in conf_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    conf = float(match.group(1))
                    if conf > 1:
                        conf = conf / 100
                    return min(max(conf, 0.0), 1.0)
                except ValueError:
                    continue
        
        return 0.8  # Default confidence
    
    @staticmethod
    def _extract_improved_title(text: str, original_title: str) -> str:
        """Extract improved title from iteration response."""
        # Look for explicit improved title
        title_patterns = [
            r'(?:improved|updated|new)\s*title:?\s*(.+?)(?:\n|$)',
            r'title:?\s*(.+?)(?:\n|$)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                if title and title != original_title:
                    return title[:500]  # Limit length
        
        return original_title  # Fallback to original
    
    @staticmethod
    def _extract_improved_description(text: str) -> str:
        """Extract improved description from iteration response."""
        # Look for improved description section
        desc_patterns = [
            r'(?:improved|updated|enhanced)\s*description:?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'description:?\s*(.+?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                desc = match.group(1).strip()
                if len(desc) > 50:
                    return desc[:2000]  # Limit length
        
        return text[:1000] + "..." if len(text) > 1000 else text  # Fallback
    
    @staticmethod
    def _extract_changes_made(text: str) -> List[str]:
        """Extract list of changes made during iteration."""
        return LLMResponseParser._extract_list_items(text, ["change", "update", "improve", "modify", "enhance"])
    
    @staticmethod
    def _extract_improvement_summary(text: str) -> str:
        """Extract improvement summary from iteration response."""
        summary_patterns = [
            r'(?:summary|overview):?\s*(.+?)(?=\n\n|\n[A-Z]|$)',
            r'(?:improved|enhanced):?\s*(.+?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                summary = match.group(1).strip()
                if len(summary) > 20:
                    return summary[:500]
        
        return "Idea has been improved based on provided feedback and suggestions."
    
    @staticmethod
    def _extract_implementation_updates(text: str) -> str:
        """Extract implementation updates from iteration response."""
        return LLMResponseParser._extract_implementation(text)


class DataStructureParser:
    """Utility class for parsing various data structures."""
    
    @staticmethod
    def parse_csv_line(line: str, delimiter: str = ',') -> List[str]:
        """Parse a CSV line respecting quoted fields."""
        import csv
        import io
        
        reader = csv.reader(io.StringIO(line), delimiter=delimiter)
        try:
            return next(reader)
        except StopIteration:
            return []
    
    @staticmethod
    def parse_key_value_pairs(text: str) -> Dict[str, str]:
        """Parse key-value pairs from text."""
        pairs = {}
        
        # Look for key: value patterns
        pattern = r'([^:\n]+):\s*([^\n]+)'
        matches = re.findall(pattern, text)
        
        for key, value in matches:
            key = key.strip()
            value = value.strip()
            if key and value:
                pairs[key] = value
        
        return pairs
    
    @staticmethod
    def parse_numbered_list(text: str) -> List[str]:
        """Parse numbered list from text."""
        pattern = r'(?:^|\n)\s*\d+\.?\s*(.+?)(?=\n\s*\d+\.|\n\n|$)'
        matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
        return [match.strip() for match in matches if match.strip()]
    
    @staticmethod
    def parse_bullet_list(text: str) -> List[str]:
        """Parse bullet list from text."""
        pattern = r'(?:^|\n)\s*[\*\-\•]\s*(.+?)(?=\n\s*[\*\-\•]|\n\n|$)'
        matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
        return [match.strip() for match in matches if match.strip()]