"""
MEDLENS AI — Clinical Interview Engine (SIH PS 26047)
Conversational, Adaptive, Multilingual, Multimodal Patient Case-Taking Engine.
"""

from .ontology import CLINICAL_ONTOLOGY, get_pathway_for_complaint, get_generic_pathway
from .state_manager import PatientStateManager, create_initial_patient_state, get_parameter_value
from .answer_extractor import ClinicalAnswerExtractor
from .question_engine import ClinicalQuestionEngine
from .red_flag_engine import RedFlagEngine, RedFlagEngine as ClinicalRedFlagEngine
from .contradiction_engine import ContradictionEngine, ContradictionEngine as ClinicalContradictionEngine
from .provenance import ProvenanceTracker
from .confidence import ConfidenceManager, ConfidenceManager as ConfidenceEvaluator
from .summary_synthesizer import ClinicalSummarySynthesizer
from .document_request_engine import DocumentRequestEngine
from .pdf_generator import generate_clinical_pdf

__all__ = [
    "CLINICAL_ONTOLOGY",
    "get_pathway_for_complaint",
    "get_generic_pathway",
    "PatientStateManager",
    "create_initial_patient_state",
    "get_parameter_value",
    "ClinicalAnswerExtractor",
    "ClinicalQuestionEngine",
    "RedFlagEngine",
    "ClinicalRedFlagEngine",
    "ContradictionEngine",
    "ClinicalContradictionEngine",
    "ProvenanceTracker",
    "ConfidenceManager",
    "ConfidenceEvaluator",
    "ClinicalSummarySynthesizer",
    "DocumentRequestEngine",
    "generate_clinical_pdf",
]

