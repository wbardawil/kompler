"""Test Spanish document classification and entity extraction.
Critical validation: does our AI work for LATAM market?"""
import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv(override=True)

SPANISH_DOCS = [
    {
        "name": "SOP de Control de Calidad",
        "text": """
PROCEDIMIENTO OPERATIVO ESTANDAR
POE-015: Control de Calidad en Linea de Produccion B

Revision: 2.0
Fecha de vigencia: 15 de enero de 2025
Fecha de proxima revision: 15 de enero de 2026

1. OBJETIVO
Este procedimiento establece los lineamientos para la inspeccion de materiales
recibidos del proveedor Grupo Industrial del Norte S.A. de C.V. conforme a los
requisitos de ISO 9001:2015 clausula 8.6.

2. ALCANCE
Aplica a todos los materiales entrantes para la Linea de Produccion B
en la Planta Monterrey.

3. PROCEDIMIENTO
3.1 Temperatura maxima para tratamiento termico: 175 grados Celsius
3.2 Todos los materiales deben ser inspeccionados dentro de las 48 horas de recepcion
3.3 Los registros de inspeccion deben mantenerse segun ISO 9001:2015 clausula 7.5

4. RESPONSABLE
Gerente de Calidad: Carlos Rodriguez Martinez
Aprobado por: Ana Maria Gonzalez, Directora de Operaciones
"""
    },
    {
        "name": "Certificado de Proveedor IMMEX",
        "text": """
CERTIFICADO DE PROVEEDOR APROBADO

Empresa: Aceros y Metales del Pacifico S.A. de C.V.
RFC: AMP201115KJ7
Numero de certificado: CERT-2024-0847
Fecha de emision: 01 de marzo de 2024
Fecha de vencimiento: 28 de febrero de 2025

Productos certificados:
- Lamina de acero calibre 14 y 16
- Tubo estructural PTR
- Angulo de hierro 1" x 1"

Este certificado ampara que el proveedor cumple con los requisitos
del programa IMMEX para importacion temporal de materias primas
conforme al Decreto para el Fomento de la Industria Maquiladora.

Numero de programa IMMEX: IMMEX-2019-3847
Secretaria de Economia - Registro vigente

Certificado por: Instituto Mexicano de Normalizacion y Certificacion A.C.
"""
    },
    {
        "name": "Factura CFDI",
        "text": """
FACTURA ELECTRONICA - CFDI 4.0

Emisor: MANUFACTURERA DEL BAJIO S.A. DE C.V.
RFC Emisor: MDB180523LP4
Regimen Fiscal: 601 - General de Ley Personas Morales

Receptor: COMPONENTES AUTOMOTRICES DE MEXICO S. DE R.L. DE C.V.
RFC Receptor: CAM150812QR3
Uso CFDI: G03 - Gastos en general

Folio fiscal: 8A7B3C4D-1234-5678-9ABC-DEF012345678
Fecha de emision: 15 de marzo de 2026

Conceptos:
  1. Servicio de maquinado CNC - 50 piezas    $45,000.00
  2. Tratamiento termico                        $12,500.00
  3. Inspeccion de calidad                       $3,200.00

Subtotal: $60,700.00
IVA 16%: $9,712.00
Total: $70,412.00

Metodo de pago: PPD - Pago en parcialidades o diferido
Forma de pago: 03 - Transferencia electronica de fondos

Sello digital del SAT: vigente
Certificado del SAT: 00001000000509B73600
"""
    },
    {
        "name": "Politica de Calidad",
        "text": """
POLITICA DE CALIDAD

GRUPO MANUFACTURERO AZTECA S.A. DE C.V.

En Grupo Manufacturero Azteca estamos comprometidos con:

1. Satisfacer los requisitos de nuestros clientes y las partes interesadas
2. Cumplir con los requisitos legales y reglamentarios aplicables,
   incluyendo normas ISO 9001:2015, regulaciones IMMEX y certificacion REPSE
3. Mejorar continuamente la eficacia de nuestro Sistema de Gestion de Calidad
4. Proporcionar los recursos necesarios para lograr los objetivos de calidad
5. Mantener un ambiente de trabajo seguro conforme a NOM-035-STPS-2018

Esta politica es comunicada y entendida por todos los niveles de la organizacion
y esta disponible para las partes interesadas pertinentes.

Aprobado por: Ing. Roberto Fernandez Luna
Cargo: Director General
Fecha: 01 de enero de 2026
Revision: 5.0
"""
    },
    {
        "name": "Registro REPSE",
        "text": """
CONSTANCIA DE REGISTRO REPSE

Registro de Prestadoras de Servicios Especializados u Obras Especializadas

Razon Social: SERVICIOS INDUSTRIALES TECNICOS DEL NORTE S.A. DE C.V.
RFC: SIT190827MN5
Numero de registro REPSE: REG-2023-REPSE-48291

Servicios especializados registrados:
- Mantenimiento industrial especializado (codigo SCIAN: 811310)
- Servicios de limpieza industrial (codigo SCIAN: 561720)
- Servicios de vigilancia y seguridad privada (codigo SCIAN: 561612)

Fecha de registro: 15 de agosto de 2023
Fecha de vencimiento: 14 de agosto de 2026
Periodo de renovacion: 15 de mayo de 2026 al 14 de agosto de 2026

Requisitos de cumplimiento vigente:
- Constancia de Situacion Fiscal del SAT: Vigente
- Cumplimiento IMSS: Al corriente
- Cumplimiento INFONAVIT: Al corriente
- Registro SISUB: Actualizado

STPS - Secretaria del Trabajo y Prevision Social
"""
    }
]

async def test():
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("No API key!")
        return

    client = anthropic.AsyncAnthropic(api_key=api_key)

    classify_prompt = """You are a document classification expert for regulated industries.
Analyze the document text and return a JSON object with these fields:
{"doc_type": "sop|work_instruction|quality_record|supplier_certificate|audit_report|policy|procedure|specification|invoice|contract|correspondence|training_record|corrective_action|risk_assessment|regulatory_registration|tax_document|other",
"confidence": 0.0-1.0,
"summary": "2-3 sentence summary in THE SAME LANGUAGE as the document",
"language": "detected language code (es, en, etc.)",
"compliance_frameworks": ["list: iso_9001, immex, repse, cfdi, etc."],
"expiry_date": "YYYY-MM-DD if found, null otherwise",
"review_due_date": "YYYY-MM-DD if found, null otherwise",
"entities_preview": ["top 5 key entities found"]}
Respond ONLY with valid JSON."""

    extract_prompt = """Extract entities from this document. Return JSON:
{"entities": [
  {"entity_type": "person|organization|regulation|certificate|date|location|product|process|standard|document_reference|tax_id",
   "value": "exact text from document",
   "normalized_value": "standardized form",
   "confidence": 0.0-1.0}
]}
Respond ONLY with valid JSON."""

    print("=" * 70)
    print("SPANISH DOCUMENT CLASSIFICATION & EXTRACTION TEST")
    print("=" * 70)

    all_passed = True

    for doc in SPANISH_DOCS:
        print(f"\n--- {doc['name']} ---")

        # Classification
        try:
            response = await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                system=classify_prompt,
                messages=[{"role": "user", "content": doc["text"]}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                lines = [l for l in raw.split("\n") if not l.strip().startswith("```")]
                raw = "\n".join(lines)
            result = json.loads(raw)

            print(f"  Type: {result.get('doc_type')} ({result.get('confidence', 0)*100:.0f}%)")
            print(f"  Language: {result.get('language')}")
            print(f"  Frameworks: {result.get('compliance_frameworks', [])}")
            print(f"  Expiry: {result.get('expiry_date', 'none')}")
            print(f"  Review due: {result.get('review_due_date', 'none')}")
            print(f"  Summary: {result.get('summary', '')[:120]}")

            if result.get('language') != 'es':
                print(f"  WARNING: Language detected as '{result.get('language')}', expected 'es'")
                all_passed = False

        except Exception as e:
            print(f"  CLASSIFICATION FAILED: {e}")
            all_passed = False

        # Entity extraction
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=extract_prompt,
                messages=[{"role": "user", "content": doc["text"]}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                lines = [l for l in raw.split("\n") if not l.strip().startswith("```")]
                raw = "\n".join(lines)
            result = json.loads(raw)

            entities = result.get("entities", [])
            print(f"  Entities: {len(entities)} found")
            for e in entities[:5]:
                print(f"    [{e.get('entity_type')}] {e.get('value')}")
            if len(entities) > 5:
                print(f"    ... +{len(entities)-5} more")

        except Exception as e:
            print(f"  EXTRACTION FAILED: {e}")
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("RESULT: ALL TESTS PASSED - Spanish classification works!")
    else:
        print("RESULT: SOME ISSUES FOUND - Review warnings above")
    print("=" * 70)

asyncio.run(test())
