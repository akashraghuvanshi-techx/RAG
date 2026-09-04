"""Benchmark Evaluation Dataset containing 20 curated industrial RAG test queries.
Defines expected documents, key factual entities, and verification rules.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    query_id: str
    query: str
    expected_document: str
    expected_page: int
    expected_section: str
    expected_entities: List[str]
    category: str  # tag_search, standard, versioning, ocr_scanned, security, workflow
    required_clearance: str = "confidential"


EVALUATION_DATASET: List[EvaluationCase] = [
    EvaluationCase(
        query_id="Q01",
        query="What is the current maximum allowable cavitation pitting depth for pump P-101 impeller?",
        expected_document="SOP-MEC-PUMP-001_Rev5.pdf",
        expected_page=1,
        expected_section="SECTION 3.1: IMPELLER CAVITATION & WEAR TOLERANCES (CRITICAL)",
        expected_entities=["2.5 mm", "P-101", "Rev 5"],
        category="versioning"
    ),
    EvaluationCase(
        query_id="Q02",
        query="What was the historical impeller cavitation pitting limit under Rev 3 in 2021?",
        expected_document="SOP-MEC-PUMP-001_Rev3.docx",
        expected_page=1,
        expected_section="3.1 Impeller Inspection and Replacement Criteria",
        expected_entities=["4.5 mm", "Rev 3", "SUPERSEDED"],
        category="versioning"
    ),
    EvaluationCase(
        query_id="Q03",
        query="What was the measured pit depth found during emergency inspection of feed pump P-101?",
        expected_document="INSP-2026-P101-001_scanned.pdf",
        expected_page=1,
        expected_section="1. EXECUTIVE SUMMARY & MAJOR FINDINGS",
        expected_entities=["3.8 mm", "P-101", "cavitation"],
        category="ocr_scanned"
    ),
    EvaluationCase(
        query_id="Q04",
        query="What radial vibration velocity was measured on P-101 inboard bearing housing?",
        expected_document="INSP-2026-P101-001_scanned.pdf",
        expected_page=1,
        expected_section="2. MEASURED PARAMETERS TABLE",
        expected_entities=["6.2 mm/s", "CRITICAL ALARM"],
        category="ocr_scanned"
    ),
    EvaluationCase(
        query_id="Q05",
        query="What mechanical seal flush plan is mandated for hydrocarbon pumps P-101 and P-102?",
        expected_document="SOP-MEC-PUMP-001_Rev5.pdf",
        expected_page=2,
        expected_section="SECTION 4.2: MECHANICAL SEAL FLUSH & INSTRUMENTATION",
        expected_entities=["Plan 53A", "2.0 bar", "differential"],
        category="tag_search"
    ),
    EvaluationCase(
        query_id="Q06",
        query="What dynamic balancing grade is required for API 610 pump rotor assemblies?",
        expected_document="ENG-STD-API610_Centrifugal.pdf",
        expected_page=1,
        expected_section="CLAUSE 6.9: ROTOR DYNAMICS & VIBRATION LIMITS",
        expected_entities=["ISO 1940", "G2.5", "API 610"],
        category="standard"
    ),
    EvaluationCase(
        query_id="Q07",
        query="What is the design capacity and service fluid for Hydrocracker Feed Pump P-101?",
        expected_document="EQUIP-REG-2026.xlsx",
        expected_page=1,
        expected_section="Sheet: Refinery Unit 2 Register",
        expected_entities=["P-101", "350 m3/hr", "Heavy Vacuum Gas Oil"],
        category="tag_search"
    ),
    EvaluationCase(
        query_id="Q08",
        query="What was the reason and budget for separator vessel V-204 replacement approval note?",
        expected_document="APP-NOTE-2024-V204.docx",
        expected_page=1,
        expected_section="Subject: Approval for Replacement of Tray Section in High Pressure Separator V-204",
        expected_entities=["V-204", "ASME Section VIII", "45,00,000"],
        category="workflow"
    ),
    EvaluationCase(
        query_id="Q09",
        query="Which standard specifies the process piping interface requirements for pump overhaul?",
        expected_document="SOP-MEC-PUMP-001_Rev5.pdf",
        expected_page=1,
        expected_section="SECTION 2.0: OPERATIONAL INTEGRITY & CODES",
        expected_entities=["ASME B31.3", "API 610"],
        category="standard"
    ),
    EvaluationCase(
        query_id="Q10",
        query="What is the allowable vibration alarm threshold on bearing housing in SOP Rev 5?",
        expected_document="SOP-MEC-PUMP-001_Rev5.pdf",
        expected_page=1,
        expected_section="SECTION 3.1: IMPELLER CAVITATION & WEAR TOLERANCES (CRITICAL)",
        expected_entities=["4.5 mm/s", "6.0 mm/s"],
        category="tag_search"
    ),
    EvaluationCase(
        query_id="Q11",
        query="What metallurgical alloy is recommended for replacement of P-101 suction impeller?",
        expected_document="INSP-2026-P101-001_scanned.pdf",
        expected_page=1,
        expected_section="3. MANDATORY RECOMMENDATIONS FOR APPROVAL NOTE",
        expected_entities=["Super Duplex", "Stainless Steel", "P-101"],
        category="ocr_scanned"
    ),
    EvaluationCase(
        query_id="Q12",
        query="What is the design capacity of atmospheric column fractionator T-102?",
        expected_document="EQUIP-REG-2026.xlsx",
        expected_page=1,
        expected_section="Sheet: Refinery Unit 2 Register",
        expected_entities=["T-102", "15000 TPD", "Crude Distillate"],
        category="tag_search"
    ),
    EvaluationCase(
        query_id="Q13",
        query="Who is the final signing authority for pump component capital replacement?",
        expected_document="SOP-MEC-PUMP-001_Rev5.pdf",
        expected_page=2,
        expected_section="SECTION 5.0: APPROVAL WORKFLOW FOR COMPONENT REPLACEMENT",
        expected_entities=["General Manager", "Refinery Operations"],
        category="workflow"
    ),
    EvaluationCase(
        query_id="Q14",
        query="What is the minimum corrosion allowance specified for pump casings under API 610?",
        expected_document="ENG-STD-API610_Centrifugal.pdf",
        expected_page=1,
        expected_section="CLAUSE 6.1.1: CASING DESIGN & MATERIAL INTEGRITY",
        expected_entities=["3 mm", "MAWP"],
        category="standard"
    ),
    EvaluationCase(
        query_id="Q15",
        query="What is the criticality category assigned to gas separator V-204 in the equipment register?",
        expected_document="EQUIP-REG-2026.xlsx",
        expected_page=1,
        expected_section="Sheet: Refinery Unit 2 Register",
        expected_entities=["V-204", "Category A"],
        category="tag_search"
    ),
    EvaluationCase(
        query_id="Q16",
        query="What was the verdict on the impeller pitting depth in the scanned inspection report for P-101?",
        expected_document="INSP-2026-P101-001_scanned.pdf",
        expected_page=1,
        expected_section="2. MEASURED PARAMETERS TABLE",
        expected_entities=["CONDEMNED", "3.8 mm"],
        category="ocr_scanned"
    ),
    EvaluationCase(
        query_id="Q17",
        query="What is the in-service trip limit for vibration velocity in API 610 Clause 6.9?",
        expected_document="ENG-STD-API610_Centrifugal.pdf",
        expected_page=1,
        expected_section="CLAUSE 6.9: ROTOR DYNAMICS & VIBRATION LIMITS",
        expected_entities=["7.1 mm/s", "trip limit"],
        category="standard"
    ),
    EvaluationCase(
        query_id="Q18",
        query="What service and design standard is specified for feed preheater exchanger E-301?",
        expected_document="EQUIP-REG-2026.xlsx",
        expected_page=1,
        expected_section="Sheet: Refinery Unit 2 Register",
        expected_entities=["E-301", "TEMA R", "Category B"],
        category="tag_search"
    ),
    EvaluationCase(
        query_id="Q19",
        query="What date was the emergency inspection report INSP-2026-P101-001 conducted?",
        expected_document="INSP-2026-P101-001_scanned.pdf",
        expected_page=1,
        expected_section="Report Header",
        expected_entities=["15-JAN-2026", "INSP-2026-P101-001"],
        category="ocr_scanned"
    ),
    EvaluationCase(
        query_id="Q20",
        query="Which document was superseded by SOP-MEC-PUMP-001 Rev 5?",
        expected_document="SOP-MEC-PUMP-001_Rev5.pdf",
        expected_page=1,
        expected_section="Document Header",
        expected_entities=["Rev 4", "Rev 3", "Supersedes"],
        category="versioning"
    ),
]
