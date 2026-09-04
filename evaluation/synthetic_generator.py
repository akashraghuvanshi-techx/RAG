"""Synthetic Industrial Dataset Generator.
Generates realistic industrial documents (SOPs, Scanned Inspection Reports, Standards, Excel registries)
used by refineries, PSUs, and defense engineering units.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import docx
import openpyxl
import pymupdf


def generate_synthetic_documents(output_dir: Path) -> dict:
    """Generates a complete suite of synthetic industrial documents."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = {}

    # -------------------------------------------------------------
    # 1. SOP Rev 3 (Obsolete DOCX)
    # -------------------------------------------------------------
    sop_rev3_path = output_dir / "SOP-MEC-PUMP-001_Rev3.docx"
    doc3 = docx.Document()
    doc3.add_heading("BHARAT REFINERY & PETROCHEMICALS LTD.", level=0)
    doc3.add_heading("Standard Operating Procedure: Centrifugal Pump Overhaul (Rev 3)", level=1)
    p = doc3.add_paragraph("Document Number: SOP-MEC-PUMP-001 | Revision: Rev 3 | Effective: 2021-03-01 | Status: SUPERSEDED")
    doc3.add_heading("1. Purpose and Scope", level=2)
    doc3.add_paragraph("This standard procedure applies to maintenance of all process centrifugal pumps including P-101, P-102, and P-103.")
    doc3.add_heading("3.1 Impeller Inspection and Replacement Criteria", level=2)
    doc3.add_paragraph(
        "Historical replacement threshold: Under Rev 3 guidelines, centrifugal pump impeller replacement "
        "was mandated when cavitation pitting depth exceeded 4.5 mm. Note: This standard has been superseded."
    )
    doc3.save(sop_rev3_path)
    generated_files["sop_rev3"] = sop_rev3_path

    # -------------------------------------------------------------
    # 2. SOP Rev 5 (Current Active Native PDF)
    # -------------------------------------------------------------
    sop_rev5_path = output_dir / "SOP-MEC-PUMP-001_Rev5.pdf"
    doc5 = pymupdf.open()
    page1 = doc5.new_page(width=595, height=842)

    p1_text = """SOVEREIGN REFINERIES CORPORATION
STANDARD OPERATING PROCEDURE: CENTRIFUGAL PUMP INSPECTION & OVERHAUL
Document ID: SOP-MEC-PUMP-001 | Revision: Rev 5 | Effective Date: 2025-01-10
Department: Mechanical Maintenance | Classification: CONFIDENTIAL | Status: ACTIVE
Supersedes: SOP-MEC-PUMP-001 Rev 4 and Rev 3

SECTION 1.0: SCOPE & APPLICABILITY
This standard operating procedure governs the condition monitoring, scheduled overhaul, and critical component
replacement thresholds for API 610 heavy-duty centrifugal pumps in high-pressure hydrocarbon services,
specifically including Primary Hydrocracker Feed Pumps P-101 and P-102.

SECTION 2.0: OPERATIONAL INTEGRITY & CODES
All overhaul operations must comply with ASME B31.3 process piping interfaces and API 610 11th Edition
(ISO 13709) mechanical construction requirements. Dynamic balancing of impellers shall conform to ISO 1940 Grade G2.5.

SECTION 3.1: IMPELLER CAVITATION & WEAR TOLERANCES (CRITICAL)
Visual and non-destructive examination (NDE) of the suction impeller vanes shall be conducted during every turnaround:
1. Maximum Permissible Cavitation Pitting Depth: 2.5 mm.
2. If ultrasonic thickness gauging or pit depth measurement reveals localized erosion or cavitation exceeding 2.5 mm,
   the impeller must be condemned and an immediate Capital Replacement Approval Note initiated.
3. Maximum overall vibration velocity at bearing housings: 4.5 mm/s RMS (Alarm threshold: 6.0 mm/s RMS).
4. Any pump exhibiting vibration exceeding 6.0 mm/s RMS combined with cavitation pitting above 2.5 mm shall be
   isolated immediately to prevent catastrophic shaft fatigue failure.
"""
    page1.insert_text((50, 60), p1_text, fontsize=10, fontname="helv")

    page2 = doc5.new_page(width=595, height=842)
    p2_text = """SECTION 4.2: MECHANICAL SEAL FLUSH & INSTRUMENTATION
Centrifugal pumps P-101 and P-102 operate with dual pressurized mechanical seals configured under API Plan 53A:
- Barrier fluid reservoir pressure must maintain a minimum differential of 2.0 bar above stuffing box pressure.
- Maximum allowable seal face leakage is 5 drops/minute during steady-state hydrocarbon pumping.

SECTION 5.0: APPROVAL WORKFLOW FOR COMPONENT REPLACEMENT
1. An inspection report documenting ultrasonic pit measurements must be certified by the Level II NDE Inspector.
2. The Mechanical Maintenance Lead Engineer shall draft an Approval Note citing SOP-MEC-PUMP-001 Rev 5 Section 3.1.
3. Final financial and operational concurrence must be signed by the General Manager (Refinery Operations).
"""
    page2.insert_text((50, 60), p2_text, fontsize=10, fontname="helv")
    doc5.save(sop_rev5_path)
    doc5.close()
    generated_files["sop_rev5"] = sop_rev5_path

    # -------------------------------------------------------------
    # 3. Scanned Inspection Report PDF (Image-Only, Requires OCR)
    # -------------------------------------------------------------
    insp_scanned_path = output_dir / "INSP-2026-P101-001_scanned.pdf"

    # Render a high-resolution scanned page image
    img = Image.new("RGB", (1240, 1754), color=(250, 250, 245))  # slightly off-white scanner paper
    draw = ImageDraw.Draw(img)

    # Simulated scanned inspection report text
    draw.text((80, 80), "BHARAT PETROCHEMICALS & REFINERIES LTD - PLANT INSPECTION WING", fill=(30, 30, 30))
    draw.text((80, 120), "OFFICIAL NON-DESTRUCTIVE TESTING & INSPECTION REPORT", fill=(20, 20, 20))
    draw.text((80, 160), "Report No: INSP-2026-P101-001       Inspection Date: 15-JAN-2026", fill=(40, 40, 40))
    draw.text((80, 200), "Equipment Tag: P-101                Service: Hydrocracker Feed Pump", fill=(40, 40, 40))
    draw.text((80, 240), "Department: Mechanical Maintenance  Clearance: CONFIDENTIAL", fill=(40, 40, 40))
    draw.text((80, 280), "--------------------------------------------------------------------------------", fill=(80, 80, 80))

    draw.text((80, 320), "1. EXECUTIVE SUMMARY & MAJOR FINDINGS:", fill=(10, 10, 10))
    draw.text((80, 360), "Emergency inspection of Hydrocracker Feed Pump P-101 was conducted following", fill=(30, 30, 30))
    draw.text((80, 400), "high acoustic emission and abnormal vibration alarms during full throughput operation.", fill=(30, 30, 30))
    draw.text((80, 440), "Detailed optical boroscopy and pit gauge depth measurement revealed severe cavitation", fill=(30, 30, 30))
    draw.text((80, 480), "erosion across the suction impeller vane root faces with measured pit depth of 3.8 mm.", fill=(30, 30, 30))
    draw.text((80, 520), "This measured 3.8 mm cavitation pit depth significantly exceeds the 2.5 mm maximum", fill=(30, 30, 30))
    draw.text((80, 560), "permissible threshold specified in SOP-MEC-PUMP-001 Rev 5 Section 3.1.", fill=(30, 30, 30))
    draw.text((80, 600), "Inboard bearing housing radial vibration velocity reached 6.2 mm/s RMS (Alarm limit 6.0).", fill=(30, 30, 30))

    # Draw inspection data table
    draw.text((80, 670), "2. MEASURED PARAMETERS TABLE:", fill=(10, 10, 10))
    draw.rectangle([80, 710, 1150, 950], outline=(60, 60, 60), width=2)
    draw.line([80, 760, 1150, 760], fill=(60, 60, 60), width=2)
    draw.line([350, 710, 350, 950], fill=(60, 60, 60), width=1)
    draw.line([600, 710, 600, 950], fill=(60, 60, 60), width=1)
    draw.line([850, 710, 850, 950], fill=(60, 60, 60), width=1)

    draw.text((90, 725), "Component / Location", fill=(20, 20, 20))
    draw.text((360, 725), "Measured Value", fill=(20, 20, 20))
    draw.text((610, 725), "Allowable Limit", fill=(20, 20, 20))
    draw.text((860, 725), "Status / Verdict", fill=(20, 20, 20))

    draw.line([80, 820, 1150, 820], fill=(120, 120, 120), width=1)
    draw.text((90, 780), "Impeller Pitting Depth (P-101)", fill=(30, 30, 30))
    draw.text((360, 780), "3.8 mm", fill=(30, 30, 30))
    draw.text((610, 780), "2.5 mm (SOP Rev 5)", fill=(30, 30, 30))
    draw.text((860, 780), "CONDEMNED", fill=(180, 20, 20))

    draw.line([80, 880, 1150, 880], fill=(120, 120, 120), width=1)
    draw.text((90, 840), "Radial Vibration Velocity", fill=(30, 30, 30))
    draw.text((360, 840), "6.2 mm/s RMS", fill=(30, 30, 30))
    draw.text((610, 840), "4.5 mm/s RMS", fill=(30, 30, 30))
    draw.text((860, 840), "CRITICAL ALARM", fill=(180, 20, 20))

    draw.text((90, 900), "Seal Flush Pressure (Plan 53A)", fill=(30, 30, 30))
    draw.text((360, 900), "2.2 bar diff", fill=(30, 30, 30))
    draw.text((610, 900), "2.0 bar min", fill=(30, 30, 30))
    draw.text((860, 900), "NORMAL", fill=(20, 120, 20))

    draw.text((80, 1000), "3. MANDATORY RECOMMENDATIONS FOR APPROVAL NOTE:", fill=(10, 10, 10))
    draw.text((80, 1040), "- Immediate replacement of P-101 suction impeller with Super Duplex Stainless Steel alloy.", fill=(30, 30, 30))
    draw.text((80, 1080), "- Replace inboard deep-groove ball bearings and re-align drive shaft to API 610 tolerance.", fill=(30, 30, 30))
    draw.text((80, 1120), "- Initiate official Capital Replacement Approval Note citing inspection report INSP-2026-P101-001.", fill=(30, 30, 30))
    draw.text((80, 1250), "Certified by: Chief Mechanical Inspector (Govt Approved NDE Level III)", fill=(40, 40, 40))

    # Save as image-only PDF (no text stream) to strictly test OCR
    scanned_pdf = pymupdf.open()
    rect = pymupdf.Rect(0, 0, 595, 842)
    scanned_page = scanned_pdf.new_page(width=595, height=842)

    import io
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    scanned_page.insert_image(rect, stream=img_byte_arr.getvalue())
    scanned_pdf.save(insp_scanned_path)
    scanned_pdf.close()
    generated_files["insp_scanned"] = insp_scanned_path

    # -------------------------------------------------------------
    # 4. Engineering Standard API 610 (PDF)
    # -------------------------------------------------------------
    api610_path = output_dir / "ENG-STD-API610_Centrifugal.pdf"
    doc_api = pymupdf.open()
    p_api = doc_api.new_page(width=595, height=842)
    api_text = """AMERICAN PETROLEUM INSTITUTE - STANDARD API 610
CENTRIFUGAL PUMPS FOR PETROLEUM, PETROCHEMICAL AND NATURAL GAS INDUSTRIES
Classification: RESTRICTED | Department: Engineering

CLAUSE 6.1.1: CASING DESIGN & MATERIAL INTEGRITY
Pump casings shall be designed to withstand maximum allowable working pressure (MAWP) with minimum 3 mm
corrosion allowance. Radial split casings are mandatory for hydrocarbons above 200 deg C or operating pressures > 35 bar.

CLAUSE 6.9: ROTOR DYNAMICS & VIBRATION LIMITS
Rotor assemblies shall be dynamically balanced to ISO 1940 Grade G2.5. Unfiltered vibration measured on
the bearing housing during shop acceptance test shall not exceed 3.0 mm/s RMS. In-service trip limit is 7.1 mm/s RMS.
"""
    p_api.insert_text((50, 60), api_text, fontsize=10, fontname="helv")
    doc_api.save(api610_path)
    doc_api.close()
    generated_files["api_610"] = api610_path

    # -------------------------------------------------------------
    # 5. Approval Note (DOCX)
    # -------------------------------------------------------------
    app_note_path = output_dir / "APP-NOTE-2024-V204.docx"
    doc_app = docx.Document()
    doc_app.add_heading("INTERNAL APPROVAL NOTE: CAPEX REPLACEMENT", level=0)
    doc_app.add_paragraph("Approval Note ID: APP-NOTE-2024-V204 | Date: 2024-08-12 | Department: Operations")
    doc_app.add_heading("Subject: Approval for Replacement of Tray Section in High Pressure Separator V-204", level=1)
    doc_app.add_paragraph(
        "Based on ultrasonic wall thickness measurement and internal corrosion survey, separator V-204 "
        "has reached minimum allowable retirement thickness per ASME Section VIII Div 1. "
        "Estimated budget requirement: INR 45,00,000. Approved by Executive Director (Refineries)."
    )
    doc_app.save(app_note_path)
    generated_files["app_note"] = app_note_path

    # -------------------------------------------------------------
    # 6. Equipment Register (XLSX)
    # -------------------------------------------------------------
    equip_path = output_dir / "EQUIP-REG-2026.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Refinery Unit 2 Register"
    ws.append(["Tag No", "Equipment Name", "Service", "Design Capacity", "Design Standard", "Criticality"])
    ws.append(["P-101", "Hydrocracker Feed Pump A", "Heavy Vacuum Gas Oil", "350 m3/hr", "API 610", "Category A (Critical)"])
    ws.append(["P-102", "Hydrocracker Feed Pump B (Standby)", "Heavy Vacuum Gas Oil", "350 m3/hr", "API 610", "Category A (Critical)"])
    ws.append(["V-204", "High Pressure Gas Separator", "Hydrocarbon Vapor/Liquid", "5000 Nm3/hr", "ASME Section VIII", "Category A (Critical)"])
    ws.append(["E-301", "Feed Preheater Exchanger", "Light Naphtha / Steam", "1200 kW", "TEMA R", "Category B"])
    ws.append(["T-102", "Atmospheric Column Fractionator", "Crude Distillate", "15000 TPD", "ASME B31.3", "Category A (Critical)"])
    wb.save(equip_path)
    wb.close()
    generated_files["equipment_register"] = equip_path

    return generated_files


if __name__ == "__main__":
    out = Path("./data/synthetic_corpus")
    files = generate_synthetic_documents(out)
    print(f"Generated {len(files)} synthetic documents in {out}")
