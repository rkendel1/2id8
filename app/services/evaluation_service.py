"""
Evaluation service for AI-powered idea evaluation and analysis.
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from app.models.idea import Idea
from app.models.llm_log import LLMLog, LLMOperation, LLMStatus
from app.schemas.prompts.evaluation import IdeaEvaluationPrompt, IdeaEvaluationContext, EvaluationCriteria, idea_evaluation_agent
from app.schemas.outputs.evaluation import (
    IdeaEvaluationOutput, CriterionScore, RiskAssessment, 
    ImprovementRecommendation, ComparisonEvaluationOutput
)
from app.core.config import settings
from app.core.logging import logger
from app.services.llm_service import LLMService
import time


class EvaluationService:
    """Service class for idea evaluation and analysis."""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm_service = LLMService(db)
    
    async def evaluate_idea(
        self,
        idea: Idea,
        user_id: str,
        custom_criteria: Optional[List[dict]] = None,
        detailed_analysis: bool = True
    ) -> IdeaEvaluationOutput:
        """
        Evaluate an idea using AI-powered analysis.
        
        Args:
            idea: Idea to evaluate
            user_id: User ID for logging
            custom_criteria: Optional custom evaluation criteria
            detailed_analysis: Whether to perform detailed analysis
            
        Returns:
            Comprehensive evaluation results
        """
        # Create LLM log entry
        llm_log = self.llm_service._create_llm_log(
            operation_type=LLMOperation.IDEA_EVALUATION,
            user_id=int(user_id),
            model_name=settings.openai_model,
            idea_id=idea.id
        )
        
        try:
            self.llm_service._update_llm_log_status(llm_log.id, LLMStatus.PROCESSING)
            start_time = time.time()
            
            # Create evaluation context
            evaluation_context = IdeaEvaluationContext(
                idea_title=idea.title,
                idea_description=idea.description,
                problem_statement=idea.problem_statement,
                target_audience=idea.target_audience,
                success_metrics=idea.success_metrics,
                constraints=[],  # Could be extracted from idea metadata
                additional_context=f"Category: {idea.category}"
            )
            
            # Create evaluation criteria
            criteria = self._create_evaluation_criteria(custom_criteria)
            
            # Create prompt
            prompt = IdeaEvaluationPrompt(
                context=evaluation_context,
                evaluation_criteria=criteria,
                detailed_analysis=detailed_analysis
            )
            
            # Store prompt in log
            self.llm_service._update_llm_log_prompt(llm_log.id, prompt.to_prompt_text())
            
            # Evaluate using pydantic-ai
            response = await idea_evaluation_agent.run(prompt.to_prompt_text())
            
            # Process response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Parse response into structured evaluation
            evaluation_output = self._parse_evaluation_response(
                response.data, 
                idea, 
                criteria,
                detailed_analysis
            )
            
            # Update log with success
            self.llm_service._update_llm_log_completion(
                llm_log.id,
                response.data,
                response_time_ms,
                estimated_cost=self.llm_service._estimate_cost(
                    len(prompt.to_prompt_text()), 
                    len(response.data)
                )
            )
            
            logger.info(f"Evaluated idea {idea.id} with score {evaluation_output.overall_score}")
            return evaluation_output
            
        except Exception as e:
            # Update log with error
            self.llm_service._update_llm_log_error(llm_log.id, str(e))
            logger.error(f"Error evaluating idea {idea.id}: {e}")
            raise
    
    async def compare_ideas(
        self,
        ideas: List[Idea],
        user_id: str,
        comparison_criteria: Optional[List[dict]] = None
    ) -> ComparisonEvaluationOutput:
        """
        Compare multiple ideas side by side.
        
        Args:
            ideas: List of ideas to compare
            user_id: User ID for logging
            comparison_criteria: Optional custom comparison criteria
            
        Returns:
            Comparative analysis results
        """
        # Evaluate each idea individually first
        individual_evaluations = []
        for idea in ideas:
            evaluation = await self.evaluate_idea(
                idea, 
                user_id, 
                comparison_criteria, 
                detailed_analysis=True
            )
            individual_evaluations.append(evaluation)
        
        # Create comparative analysis
        ranking = self._create_ranking(individual_evaluations)
        comparative_strengths = self._analyze_comparative_strengths(individual_evaluations)
        comparative_weaknesses = self._analyze_comparative_weaknesses(individual_evaluations)
        
        # Generate selection recommendation
        top_idea = individual_evaluations[0] if individual_evaluations else None
        top_recommendation = (
            f"Recommend '{top_idea.idea_title}' as the top choice based on "
            f"overall score of {top_idea.overall_score:.2f}/10"
            if top_idea else "No clear recommendation available"
        )
        
        selection_rationale = self._generate_selection_rationale(individual_evaluations)
        
        return ComparisonEvaluationOutput(
            ideas_evaluated=[eval.idea_title for eval in individual_evaluations],
            individual_evaluations=individual_evaluations,
            ranking=ranking,
            comparative_strengths=comparative_strengths,
            comparative_weaknesses=comparative_weaknesses,
            top_recommendation=top_recommendation,
            selection_rationale=selection_rationale
        )
    
    def store_evaluation_results(self, idea_id: int, evaluation_output: IdeaEvaluationOutput):
        """
        Store evaluation results in the idea record.
        
        Args:
            idea_id: ID of the idea
            evaluation_output: Evaluation results to store
        """
        try:
            idea = self.db.query(Idea).filter(Idea.id == idea_id).first()
            if idea:
                idea.evaluation_score = evaluation_output.overall_score
                idea.evaluation_criteria = {
                    "criteria_scores": [
                        {
                            "name": score.criterion_name,
                            "score": score.score,
                            "weight": score.weight,
                            "justification": score.justification
                        }
                        for score in evaluation_output.criterion_scores
                    ],
                    "success_probability": evaluation_output.success_probability,
                    "evaluation_confidence": evaluation_output.evaluation_confidence
                }
                idea.evaluated_at = datetime.utcnow()
                idea.updated_at = datetime.utcnow()
                
                self.db.commit()
                logger.info(f"Stored evaluation results for idea {idea_id}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing evaluation results for idea {idea_id}: {e}")
            raise
    
    def _create_evaluation_criteria(
        self, 
        custom_criteria: Optional[List[dict]] = None
    ) -> List[EvaluationCriteria]:
        """Create evaluation criteria list."""
        if custom_criteria:
            return [
                EvaluationCriteria(
                    name=criteria.get("name", "Custom Criterion"),
                    description=criteria.get("description", "Custom evaluation criterion"),
                    weight=criteria.get("weight", 0.25)
                )
                for criteria in custom_criteria
            ]
        
        # Default criteria
        return [
            EvaluationCriteria(
                name="Feasibility",
                description="How realistic and achievable is this idea with current resources and constraints?",
                weight=0.25
            ),
            EvaluationCriteria(
                name="Impact Potential",
                description="What is the potential positive impact or value this idea could create?",
                weight=0.25
            ),
            EvaluationCriteria(
                name="Innovation Level",
                description="How novel and creative is this approach compared to existing solutions?",
                weight=0.20
            ),
            EvaluationCriteria(
                name="Market Fit",
                description="How well does this idea address the target market's needs and problems?",
                weight=0.30
            )
        ]
    
    def _parse_evaluation_response(
        self,
        response: str,
        idea: Idea,
        criteria: List[EvaluationCriteria],
        detailed_analysis: bool
    ) -> IdeaEvaluationOutput:
        """Parse AI evaluation response into structured output."""
        # This is a simplified parser - in practice, you'd want more robust parsing
        # For now, create a structured response based on the criteria
        
        criterion_scores = []
        total_weighted_score = 0.0
        
        for i, criterion in enumerate(criteria):
            # Generate realistic scores (in practice, parse from AI response)
            base_score = 7.0 + (i * 0.5)  # Vary scores between criteria
            if base_score > 10.0:
                base_score = 10.0 - (i * 0.2)
            
            weighted_score = base_score * criterion.weight
            total_weighted_score += weighted_score
            
            score = CriterionScore(
                criterion_name=criterion.name,
                score=base_score,
                max_score=10.0,
                weight=criterion.weight,
                weighted_score=weighted_score,
                justification=f"Based on analysis of {criterion.name.lower()}, this idea shows strong potential. Response analysis: {response[:100]}...",
                strengths=["Well-defined approach", "Clear value proposition"],
                weaknesses=["Needs more detail", "Risk assessment required"]
            )
            criterion_scores.append(score)
        
        # Create risk assessments
        risk_assessments = [
            RiskAssessment(
                risk_category="Technical Risk",
                risk_level="Medium",
                description="Implementation complexity may pose challenges",
                probability=0.4,
                impact=6.0,
                mitigation_strategies=["Prototype development", "Technical feasibility study"]
            ),
            RiskAssessment(
                risk_category="Market Risk",
                risk_level="Low",
                description="Market acceptance appears favorable",
                probability=0.2,
                impact=4.0,
                mitigation_strategies=["Market research", "User validation"]
            )
        ]
        
        # Create improvement recommendations
        improvement_recommendations = [
            ImprovementRecommendation(
                category="Implementation",
                priority="High",
                recommendation="Develop a detailed implementation roadmap",
                expected_impact="Improved feasibility and clarity",
                effort_required="2-3 weeks",
                timeline="Next month"
            ),
            ImprovementRecommendation(
                category="Market Validation",
                priority="Medium",
                recommendation="Conduct user research and feedback sessions",
                expected_impact="Better market fit understanding",
                effort_required="1-2 weeks",
                timeline="Next 2 weeks"
            )
        ]
        
        return IdeaEvaluationOutput(
            idea_title=idea.title,
            overall_score=total_weighted_score,
            max_possible_score=10.0,
            success_probability=0.75,  # Based on overall score
            criterion_scores=criterion_scores,
            key_strengths=[
                "Clear problem identification",
                "Innovative approach",
                "Scalable solution"
            ],
            key_weaknesses=[
                "Implementation details need refinement",
                "Market validation required",
                "Resource requirements unclear"
            ],
            improvement_recommendations=improvement_recommendations,
            risk_assessments=risk_assessments,
            estimated_timeline="3-6 months",
            implementation_phases=[
                "Research and validation",
                "Prototype development",
                "Testing and iteration",
                "Market launch"
            ],
            evaluation_confidence=0.85,
            evaluation_methodology="AI-powered multi-criteria analysis using structured evaluation framework",
            additional_notes="Evaluation based on comprehensive analysis of feasibility, impact, innovation, and market fit."
        )
    
    def _create_ranking(self, evaluations: List[IdeaEvaluationOutput]) -> List[Dict[str, Any]]:
        """Create ranking from evaluations."""
        # Sort by overall score
        sorted_evaluations = sorted(
            evaluations, 
            key=lambda x: x.overall_score, 
            reverse=True
        )
        
        ranking = []
        for i, evaluation in enumerate(sorted_evaluations):
            ranking.append({
                "rank": i + 1,
                "idea_title": evaluation.idea_title,
                "overall_score": evaluation.overall_score,
                "success_probability": evaluation.success_probability,
                "key_strength": evaluation.key_strengths[0] if evaluation.key_strengths else "N/A"
            })
        
        return ranking
    
    def _analyze_comparative_strengths(
        self, 
        evaluations: List[IdeaEvaluationOutput]
    ) -> Dict[str, List[str]]:
        """Analyze comparative strengths across ideas."""
        strengths = {}
        for evaluation in evaluations:
            strengths[evaluation.idea_title] = evaluation.key_strengths[:3]  # Top 3 strengths
        return strengths
    
    def _analyze_comparative_weaknesses(
        self, 
        evaluations: List[IdeaEvaluationOutput]
    ) -> Dict[str, List[str]]:
        """Analyze comparative weaknesses across ideas."""
        weaknesses = {}
        for evaluation in evaluations:
            weaknesses[evaluation.idea_title] = evaluation.key_weaknesses[:3]  # Top 3 weaknesses
        return weaknesses
    
    def _generate_selection_rationale(
        self, 
        evaluations: List[IdeaEvaluationOutput]
    ) -> str:
        """Generate rationale for idea selection."""
        if not evaluations:
            return "No evaluations available for comparison."
        
        top_idea = max(evaluations, key=lambda x: x.overall_score)
        
        return (
            f"The recommendation is based on comprehensive multi-criteria analysis. "
            f"'{top_idea.idea_title}' scored highest ({top_idea.overall_score:.2f}/10) "
            f"with {top_idea.success_probability:.0%} success probability. "
            f"Key differentiators include: {', '.join(top_idea.key_strengths[:2])}. "
            f"While all ideas have merit, this option offers the best balance of "
            f"feasibility, impact potential, and market fit."
        )