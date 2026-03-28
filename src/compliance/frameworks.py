"""Regulatory framework definitions — the knowledge that makes compliance scoring work.

Each framework defines:
- Required documents (what MUST exist)
- Required records (what MUST be maintained)
- Rules (what conditions must be met)
- Review periods (how often documents must be reviewed)

This is what marketplace agent packs will eventually contain.
For now, we ship ISO 9001, IMMEX, and REPSE as built-in frameworks.
"""

from typing import Any


# =============================================================================
# ISO 9001:2015 — Quality Management Systems
# =============================================================================

ISO_9001 = {
    "id": "iso_9001",
    "name": "ISO 9001:2015",
    "full_name": "ISO 9001:2015 Quality Management Systems — Requirements",
    "version": "2015",
    "category": "quality",

    "required_documents": [
        {
            "clause": "4.3",
            "name": "QMS Scope",
            "description": "Documented scope of the quality management system",
            "doc_types": ["policy", "procedure", "quality_record"],
            "keywords": ["scope", "qms scope", "quality management system scope", "alcance"],
            "mandatory": True,
        },
        {
            "clause": "5.2",
            "name": "Quality Policy",
            "description": "Quality policy appropriate to the purpose and context of the organization",
            "doc_types": ["policy"],
            "keywords": ["quality policy", "politica de calidad", "quality commitment"],
            "mandatory": True,
        },
        {
            "clause": "6.2",
            "name": "Quality Objectives",
            "description": "Quality objectives for relevant functions, levels, and processes",
            "doc_types": ["policy", "quality_record"],
            "keywords": ["quality objectives", "objetivos de calidad", "quality goals"],
            "mandatory": True,
        },
        {
            "clause": "8.4.1",
            "name": "Supplier Evaluation Criteria",
            "description": "Criteria for evaluation, selection, monitoring, and re-evaluation of suppliers",
            "doc_types": ["procedure", "policy"],
            "keywords": ["supplier evaluation", "evaluacion de proveedores", "vendor assessment", "supplier criteria"],
            "mandatory": True,
        },
    ],

    "required_records": [
        {
            "clause": "7.1.5.1",
            "name": "Monitoring & Measuring Equipment Calibration",
            "doc_types": ["quality_record", "calibration_record"],
            "keywords": ["calibration", "calibracion", "measuring equipment"],
        },
        {
            "clause": "7.2",
            "name": "Competence Records",
            "description": "Evidence of competence (training, skills, experience, qualifications)",
            "doc_types": ["training_record", "quality_record"],
            "keywords": ["training", "competence", "capacitacion", "skills", "qualifications"],
        },
        {
            "clause": "8.2.3",
            "name": "Product/Service Requirements Review",
            "doc_types": ["quality_record"],
            "keywords": ["requirements review", "contract review", "order review"],
        },
        {
            "clause": "8.4.1",
            "name": "Supplier Evaluation Records",
            "doc_types": ["quality_record", "supplier_certificate"],
            "keywords": ["supplier evaluation", "supplier audit", "vendor assessment"],
        },
        {
            "clause": "8.6",
            "name": "Product Conformity Records",
            "description": "Evidence of conformity with acceptance criteria",
            "doc_types": ["quality_record", "inspection_report"],
            "keywords": ["conformity", "inspection", "test results", "acceptance"],
        },
        {
            "clause": "8.7.2",
            "name": "Nonconforming Outputs Records",
            "doc_types": ["quality_record", "corrective_action"],
            "keywords": ["nonconforming", "no conforme", "rejection", "deviation"],
        },
        {
            "clause": "9.1.1",
            "name": "Monitoring and Measurement Results",
            "doc_types": ["quality_record"],
            "keywords": ["monitoring results", "measurement", "KPI", "metrics"],
        },
        {
            "clause": "9.2",
            "name": "Internal Audit Program & Results",
            "doc_types": ["audit_report", "procedure"],
            "keywords": ["internal audit", "audit program", "auditoria interna", "audit results"],
        },
        {
            "clause": "9.3",
            "name": "Management Review Results",
            "doc_types": ["quality_record"],
            "keywords": ["management review", "revision por la direccion", "management meeting"],
        },
        {
            "clause": "10.2",
            "name": "Corrective Action Records",
            "doc_types": ["corrective_action", "quality_record"],
            "keywords": ["corrective action", "accion correctiva", "CAPA", "root cause"],
        },
    ],

    "rules": [
        {
            "id": "sop_annual_review",
            "type": "review_period",
            "doc_types": ["sop", "procedure", "work_instruction", "policy"],
            "period_days": 365,
            "clause": "7.5.3",
            "severity": "warning",
            "message_en": "Controlled documents must be reviewed at least annually",
            "message_es": "Los documentos controlados deben revisarse al menos anualmente",
        },
        {
            "id": "supplier_cert_expiry",
            "type": "expiry_tracking",
            "doc_types": ["supplier_certificate"],
            "warn_days": [90, 30, 14],
            "clause": "8.4",
            "severity": "critical",
            "message_en": "Supplier certificates must be current and valid",
            "message_es": "Los certificados de proveedores deben estar vigentes",
        },
    ],
}


# =============================================================================
# IMMEX — Maquiladora / Temporary Import Program (Mexico)
# =============================================================================

IMMEX = {
    "id": "immex",
    "name": "IMMEX",
    "full_name": "Programa de Industria Manufacturera, Maquiladora y de Servicios de Exportacion",
    "version": "2024",
    "category": "trade_compliance",

    "required_documents": [
        {
            "clause": "IMMEX-REG",
            "name": "IMMEX Registration Certificate",
            "description": "Active IMMEX program registration from Secretaria de Economia",
            "doc_types": ["regulatory_registration", "certificate"],
            "keywords": ["IMMEX", "programa IMMEX", "registro IMMEX", "maquiladora"],
            "mandatory": True,
        },
        {
            "clause": "IMMEX-RFC",
            "name": "Active RFC Registration",
            "description": "Active registration in Federal Taxpayers Register (RFC) for IMMEX address",
            "doc_types": ["regulatory_registration", "tax_document"],
            "keywords": ["RFC", "registro federal", "contribuyentes", "SAT"],
            "mandatory": True,
        },
        {
            "clause": "IMMEX-ANNEX",
            "name": "IMMEX Annex Listings",
            "description": "Updated annex listings per current decree specifying permitted imports",
            "doc_types": ["regulatory_registration", "quality_record"],
            "keywords": ["annex", "anexo", "decreto", "importacion temporal"],
            "mandatory": True,
        },
        {
            "clause": "IMMEX-CONTRACT",
            "name": "Maquiladora Service Contract",
            "description": "Contract, purchase orders, or evidence of export manufacturing activity",
            "doc_types": ["contract"],
            "keywords": ["maquiladora contract", "contrato", "purchase order", "export project"],
            "mandatory": True,
        },
    ],

    "required_records": [
        {
            "clause": "IMMEX-PED",
            "name": "Pedimento Records (Customs Declarations)",
            "doc_types": ["tax_document", "quality_record"],
            "keywords": ["pedimento", "customs declaration", "declaracion aduanera", "importacion"],
        },
        {
            "clause": "IMMEX-INV",
            "name": "Inventory Control Records (Annex 24)",
            "description": "Automated inventory system tracking temporary imports and exports",
            "doc_types": ["quality_record"],
            "keywords": ["inventory", "inventario", "annex 24", "anexo 24", "control de inventario"],
        },
        {
            "clause": "IMMEX-PROD",
            "name": "Production Process Documentation",
            "description": "Description of production process, installed capacity, and utilization",
            "doc_types": ["sop", "procedure", "specification"],
            "keywords": ["production process", "proceso de produccion", "installed capacity", "capacidad instalada"],
        },
    ],

    "rules": [
        {
            "id": "immex_annual_audit",
            "type": "expiry_tracking",
            "doc_types": ["regulatory_registration"],
            "warn_days": [90, 60, 30],
            "clause": "IMMEX-AUDIT",
            "severity": "critical",
            "message_en": "IMMEX registration subject to annual audit by Secretaria de Economia",
            "message_es": "El registro IMMEX esta sujeto a auditoria anual por la Secretaria de Economia",
        },
    ],
}


# =============================================================================
# REPSE — Registro de Prestadoras de Servicios Especializados (Mexico)
# =============================================================================

REPSE = {
    "id": "repse",
    "name": "REPSE",
    "full_name": "Registro de Prestadoras de Servicios Especializados u Obras Especializadas",
    "version": "2023",
    "category": "labor_compliance",

    "required_documents": [
        {
            "clause": "REPSE-REG",
            "name": "REPSE Registration Certificate",
            "description": "Active REPSE registration number from STPS",
            "doc_types": ["regulatory_registration", "certificate"],
            "keywords": ["REPSE", "registro REPSE", "servicios especializados", "STPS"],
            "mandatory": True,
        },
        {
            "clause": "REPSE-FISCAL",
            "name": "Constancia de Situacion Fiscal",
            "description": "Proof of compliance with tax obligations from SAT",
            "doc_types": ["tax_document", "certificate"],
            "keywords": ["situacion fiscal", "constancia fiscal", "SAT", "opinion de cumplimiento"],
            "mandatory": True,
        },
        {
            "clause": "REPSE-IMSS",
            "name": "IMSS Compliance Certificate",
            "description": "Proof of compliance with social security obligations",
            "doc_types": ["certificate", "regulatory_registration"],
            "keywords": ["IMSS", "seguro social", "social security", "opinion IMSS"],
            "mandatory": True,
        },
        {
            "clause": "REPSE-INFONAVIT",
            "name": "INFONAVIT Compliance Certificate",
            "description": "Proof of compliance with housing fund obligations",
            "doc_types": ["certificate", "regulatory_registration"],
            "keywords": ["INFONAVIT", "housing fund", "fondo de vivienda"],
            "mandatory": True,
        },
    ],

    "required_records": [
        {
            "clause": "REPSE-PERSONNEL",
            "name": "Personnel Lists",
            "description": "Complete list of personnel providing specialized services",
            "doc_types": ["quality_record"],
            "keywords": ["personnel list", "lista de personal", "nomina", "employees"],
        },
        {
            "clause": "REPSE-CONTRACTS",
            "name": "Service Agreements",
            "description": "Signed service agreements with beneficiary companies",
            "doc_types": ["contract"],
            "keywords": ["service agreement", "contrato de servicios", "acuerdo de servicios"],
        },
        {
            "clause": "REPSE-SISUB",
            "name": "SISUB Registration",
            "description": "Updated registration in SISUB (subcontracting information system)",
            "doc_types": ["regulatory_registration", "quality_record"],
            "keywords": ["SISUB", "subcontratacion", "subcontracting registry"],
        },
    ],

    "rules": [
        {
            "id": "repse_renewal",
            "type": "expiry_tracking",
            "doc_types": ["regulatory_registration"],
            "warn_days": [180, 90, 45, 30],
            "clause": "REPSE-RENEWAL",
            "severity": "critical",
            "message_en": "REPSE registration must be renewed every 3 years. Renewal window is 3 months before expiry.",
            "message_es": "El registro REPSE debe renovarse cada 3 anos. La ventana de renovacion es 3 meses antes del vencimiento.",
        },
    ],
}


# =============================================================================
# IATF 16949:2016 — Automotive Quality Management
# =============================================================================

IATF_16949 = {
    "id": "iatf_16949",
    "name": "IATF 16949:2016",
    "full_name": "IATF 16949:2016 Automotive Quality Management Systems",
    "version": "2016",
    "category": "automotive_quality",

    "required_documents": [
        {
            "clause": "4.3",
            "name": "QMS Scope (Automotive)",
            "description": "QMS scope including automotive-specific requirements and customer-specific requirements",
            "doc_types": ["policy", "procedure"],
            "keywords": ["scope", "alcance", "automotive", "automotriz", "IATF"],
            "mandatory": True,
        },
        {
            "clause": "5.2",
            "name": "Quality Policy (Automotive)",
            "description": "Quality policy with automotive customer-specific commitments",
            "doc_types": ["policy"],
            "keywords": ["quality policy", "politica de calidad", "automotive", "automotriz"],
            "mandatory": True,
        },
        {
            "clause": "6.1.2.1",
            "name": "Risk Analysis (FMEA)",
            "description": "Risk analysis including PFMEA, DFMEA, and contingency plans",
            "doc_types": ["quality_record", "risk_assessment"],
            "keywords": ["FMEA", "risk analysis", "analisis de riesgo", "failure mode", "modo de falla"],
            "mandatory": True,
        },
        {
            "clause": "6.1.2.3",
            "name": "Contingency Plans",
            "description": "Emergency response and contingency plans for supply chain disruption",
            "doc_types": ["procedure", "policy"],
            "keywords": ["contingency", "contingencia", "emergency", "emergencia", "business continuity"],
            "mandatory": True,
        },
    ],

    "required_records": [
        {
            "clause": "7.1.5.1.1",
            "name": "MSA Studies (Measurement System Analysis)",
            "doc_types": ["quality_record"],
            "keywords": ["MSA", "measurement system analysis", "analisis de sistema de medicion", "Gage R&R"],
        },
        {
            "clause": "7.2.3",
            "name": "Internal Auditor Competency Records",
            "description": "Evidence of internal auditor competency for QMS, manufacturing, and product audits",
            "doc_types": ["training_record", "quality_record"],
            "keywords": ["auditor competency", "competencia auditor", "auditor qualification", "VDA 6.3"],
        },
        {
            "clause": "8.3.4.4",
            "name": "Product Approval Process (PPAP/PPA)",
            "description": "Product part approval records including PPAP submissions",
            "doc_types": ["quality_record"],
            "keywords": ["PPAP", "product approval", "aprobacion de producto", "PPA", "part submission warrant"],
        },
        {
            "clause": "8.4.2.4.1",
            "name": "Second-Party Audit Records",
            "description": "Supplier audit records and second-party audit results",
            "doc_types": ["audit_report", "quality_record"],
            "keywords": ["supplier audit", "auditoria proveedor", "second party", "segunda parte", "VDA 6.3"],
        },
        {
            "clause": "8.5.1.1",
            "name": "Control Plan",
            "description": "Control plans for pre-launch and production phases",
            "doc_types": ["quality_record", "procedure"],
            "keywords": ["control plan", "plan de control", "APQP"],
        },
        {
            "clause": "8.5.2.1",
            "name": "Traceability Records",
            "description": "Product identification and traceability throughout manufacturing",
            "doc_types": ["quality_record"],
            "keywords": ["traceability", "trazabilidad", "lot tracking", "serial number"],
        },
        {
            "clause": "8.7.1.4",
            "name": "Rework/Repair Records",
            "description": "Control of reworked and repaired product with re-inspection records",
            "doc_types": ["quality_record", "corrective_action"],
            "keywords": ["rework", "retrabajo", "repair", "reparacion", "re-inspection"],
        },
        {
            "clause": "9.2.2.1",
            "name": "QMS Audit Program (Automotive)",
            "description": "Internal audit program covering QMS, manufacturing process, and product audits",
            "doc_types": ["audit_report", "procedure"],
            "keywords": ["audit program", "programa de auditoria", "manufacturing audit", "process audit", "product audit"],
        },
    ],

    "rules": [
        {
            "id": "iatf_audit_cycle",
            "type": "review_period",
            "doc_types": ["sop", "procedure", "control_plan"],
            "period_days": 365,
            "clause": "9.2.2.1",
            "severity": "warning",
            "message_en": "Automotive QMS requires annual audit cycle covering all processes",
            "message_es": "El SGC automotriz requiere ciclo de auditoria anual cubriendo todos los procesos",
        },
    ],
}


# =============================================================================
# LFPIORPI — Mexican Anti-Money Laundering Law
# =============================================================================

LFPIORPI = {
    "id": "lfpiorpi",
    "name": "LFPIORPI (Ley Antilavado)",
    "full_name": "Ley Federal para la Prevencion e Identificacion de Operaciones con Recursos de Procedencia Ilicita",
    "version": "2025",
    "category": "anti_money_laundering",

    "required_documents": [
        {
            "clause": "AML-REG",
            "name": "Registro ante el SAT como Sujeto Obligado",
            "description": "Alta en el portal de prevencion de lavado de dinero del SAT como sujeto obligado por realizar actividades vulnerables",
            "doc_types": ["regulatory_registration", "certificate"],
            "keywords": ["SAT", "sujeto obligado", "actividades vulnerables", "portal antilavado", "registro PLD"],
            "mandatory": True,
        },
        {
            "clause": "AML-MANUAL",
            "name": "Manual de Prevencion de Lavado de Dinero (PLD)",
            "description": "Manual interno de politicas y procedimientos para prevencion de lavado de dinero y financiamiento al terrorismo",
            "doc_types": ["policy", "procedure"],
            "keywords": ["manual PLD", "prevencion lavado", "anti money laundering", "antilavado", "PLD/FT"],
            "mandatory": True,
        },
        {
            "clause": "AML-KYC",
            "name": "Politica de Identificacion del Cliente (KYC)",
            "description": "Procedimiento de identificacion y verificacion de clientes, incluyendo beneficiario controlador para personas morales",
            "doc_types": ["policy", "procedure"],
            "keywords": ["KYC", "conoce tu cliente", "identificacion cliente", "beneficiario controlador", "due diligence"],
            "mandatory": True,
        },
        {
            "clause": "AML-EFIRMA",
            "name": "e.firma Vigente (Firma Electronica Avanzada)",
            "description": "Certificado de e.firma vigente ante el SAT, requerido para presentar avisos",
            "doc_types": ["certificate", "regulatory_registration"],
            "keywords": ["e.firma", "firma electronica", "FIEL", "certificado SAT"],
            "mandatory": True,
        },
    ],

    "required_records": [
        {
            "clause": "AML-AVISOS",
            "name": "Avisos Mensuales al SAT",
            "description": "Reportes mensuales de actividades vulnerables presentados ante el portal del SAT (incluyendo avisos en cero cuando no haya operaciones)",
            "doc_types": ["quality_record", "tax_document"],
            "keywords": ["aviso", "reporte mensual", "actividades vulnerables", "portal SAT", "aviso en cero"],
        },
        {
            "clause": "AML-EXPEDIENTES",
            "name": "Expedientes de Identificacion de Clientes",
            "description": "Expedientes con documentos de identificacion de cada cliente en operaciones que superen el umbral (3,210 UMAs para vehiculos)",
            "doc_types": ["quality_record"],
            "keywords": ["expediente cliente", "identificacion oficial", "INE", "pasaporte", "comprobante domicilio", "RFC cliente"],
        },
        {
            "clause": "AML-BENEFICIARIO",
            "name": "Identificacion del Beneficiario Controlador",
            "description": "Documentacion que identifica al beneficiario controlador en operaciones con personas morales o fideicomisos",
            "doc_types": ["quality_record"],
            "keywords": ["beneficiario controlador", "beneficial owner", "persona moral", "fideicomiso", "acta constitutiva"],
        },
        {
            "clause": "AML-RESGUARDO",
            "name": "Archivo de Resguardo (10 anos)",
            "description": "Custodia y proteccion de informacion por 10 anos contados a partir de la realizacion de la actividad vulnerable (reformado de 5 a 10 anos en 2025)",
            "doc_types": ["quality_record", "policy"],
            "keywords": ["resguardo", "custodia", "proteccion informacion", "retencion", "10 anos"],
        },
        {
            "clause": "AML-CAPACITACION",
            "name": "Registros de Capacitacion PLD",
            "description": "Evidencia de capacitacion del personal en materia de prevencion de lavado de dinero",
            "doc_types": ["training_record", "quality_record"],
            "keywords": ["capacitacion PLD", "entrenamiento antilavado", "formacion", "prevencion lavado"],
        },
    ],

    "rules": [
        {
            "id": "lfpiorpi_monthly_report",
            "type": "review_period",
            "doc_types": ["quality_record", "tax_document"],
            "period_days": 30,
            "clause": "AML-AVISOS",
            "severity": "critical",
            "message_en": "Monthly vulnerability reports must be filed with SAT, including zero-activity reports",
            "message_es": "Los avisos mensuales de actividades vulnerables deben presentarse ante el SAT, incluyendo avisos en cero",
        },
        {
            "id": "lfpiorpi_retention",
            "type": "retention",
            "doc_types": ["quality_record"],
            "period_days": 3650,
            "clause": "AML-RESGUARDO",
            "severity": "critical",
            "message_en": "Client identification records must be retained for 10 years (increased from 5 in 2025 reform)",
            "message_es": "Los expedientes de identificacion deben resguardarse por 10 anos (incrementado de 5 en reforma 2025)",
        },
    ],
}


# =============================================================================
# FRAMEWORK REGISTRY
# =============================================================================

FRAMEWORKS: dict[str, dict[str, Any]] = {
    "iso_9001": ISO_9001,
    "immex": IMMEX,
    "repse": REPSE,
    "iatf_16949": IATF_16949,
    "lfpiorpi": LFPIORPI,
}


def get_framework(framework_id: str) -> dict | None:
    """Get a framework by ID."""
    return FRAMEWORKS.get(framework_id)


def list_frameworks() -> list[dict]:
    """List all available frameworks."""
    return [
        {
            "id": f["id"],
            "name": f["name"],
            "full_name": f["full_name"],
            "category": f["category"],
            "required_documents": len(f.get("required_documents", [])),
            "required_records": len(f.get("required_records", [])),
            "rules": len(f.get("rules", [])),
        }
        for f in FRAMEWORKS.values()
    ]
