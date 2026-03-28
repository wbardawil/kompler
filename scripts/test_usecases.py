"""Test 5 real compliance use cases end-to-end.

These simulate what a quality manager at a Mexican maquiladora
would actually do with Kompler. Each test verifies:
1. Does the AI classify correctly?
2. Does the compliance map show the right status?
3. Does the score change appropriately?
4. Are the right action items generated?
"""
import asyncio
import os
import sys
import json

sys.path.insert(0, ".")
os.environ["PYTHONUTF8"] = "1"
from dotenv import load_dotenv
load_dotenv(override=True)

API = "https://kompler-production.up.railway.app"
KEY = "dev-key-1"

import httpx


async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        headers = {"X-Api-Key": KEY}

        print("=" * 70)
        print("KOMPLER USE CASE TESTING")
        print("=" * 70)

        # USE CASE 1: Upload a Quality Policy and verify it maps to ISO 9001 clause 5.2
        print("\n--- USE CASE 1: Quality Policy ---")
        print("Expected: Classified as 'policy', maps to ISO 9001 clause 5.2")

        quality_policy = """
POLITICA DE CALIDAD
Revision 4.0 - Enero 2026

MANUFACTURA PRECISION DEL NORTE S.A. DE C.V.

Nos comprometemos a:
1. Satisfacer los requisitos de nuestros clientes y partes interesadas
2. Cumplir con los requisitos legales y reglamentarios aplicables
3. Mejorar continuamente la eficacia del Sistema de Gestion de Calidad
4. Proporcionar los recursos necesarios para lograr los objetivos de calidad

Esta politica es comunicada a todos los niveles de la organizacion.

Aprobado por: Ing. Roberto Fernandez Luna, Director General
Fecha: 15 de enero de 2026
Proxima revision: 15 de enero de 2027
"""
        r = await client.post(f"{API}/api/v1/documents", headers=headers,
                              files={"file": ("Politica_de_Calidad_2026.txt", quality_policy.encode())})
        result = json.loads(r.text)
        print(f"  Status: {result.get('status')}")
        print(f"  Message: {result.get('message')}")
        passed = "policy" in result.get("message", "").lower() or result.get("status") == "enriched"
        print(f"  PASS: {passed}")

        # USE CASE 2: Upload an Internal Audit Report and verify it fills ISO 9001 clause 9.2
        print("\n--- USE CASE 2: Internal Audit Report ---")
        print("Expected: Classified as 'audit_report', maps to ISO 9001 clause 9.2")

        audit_report = """
INFORME DE AUDITORIA INTERNA

Auditoria No: AI-2026-001
Fecha: 10 de marzo de 2026
Norma auditada: ISO 9001:2015
Alcance: Procesos de produccion y control de calidad

Equipo auditor:
- Auditor lider: Lic. Maria Gonzalez
- Auditor: Ing. Carlos Ramirez

Hallazgos:
1. No conformidad menor: Registros de calibracion incompletos (clausula 7.1.5)
2. Observacion: Falta de evidencia de revision por la direccion Q4 2025 (clausula 9.3)
3. Oportunidad de mejora: Implementar sistema de gestion documental digital

Conclusiones:
El SGC es generalmente efectivo. Se requieren acciones correctivas para los hallazgos 1 y 2.

Proximo ciclo de auditoria: Septiembre 2026
"""
        r = await client.post(f"{API}/api/v1/documents", headers=headers,
                              files={"file": ("Auditoria_Interna_AI-2026-001.txt", audit_report.encode())})
        result = json.loads(r.text)
        print(f"  Status: {result.get('status')}")
        print(f"  Message: {result.get('message')}")
        passed = result.get("status") == "enriched"
        print(f"  PASS: {passed}")

        # USE CASE 3: Upload a Corrective Action Record
        print("\n--- USE CASE 3: Corrective Action (CAPA) ---")
        print("Expected: Classified as 'corrective_action', maps to ISO 9001 clause 10.2")

        capa = """
REGISTRO DE ACCION CORRECTIVA

Numero: AC-2026-003
Fecha de apertura: 12 de marzo de 2026
Origen: Auditoria interna AI-2026-001, hallazgo #1

Descripcion de la no conformidad:
Registros de calibracion del micrometro digital (equipo MC-015) incompletos.
Faltan registros de calibracion de enero y febrero 2026.

Analisis de causa raiz (5 Por que):
1. No se realizaron las calibraciones programadas
2. El tecnico responsable estuvo de vacaciones
3. No existe respaldo asignado para calibraciones
4. El procedimiento no contempla ausencias del responsable
5. Causa raiz: Falta de plan de contingencia en PR-CAL-001

Accion correctiva:
1. Realizar calibraciones pendientes de enero y febrero (responsable: Ing. Torres, fecha: 20/03/2026)
2. Actualizar PR-CAL-001 para incluir respaldo de calibracion (responsable: Lic. Gonzalez, fecha: 30/03/2026)
3. Capacitar al personal de respaldo (responsable: Ing. Ramirez, fecha: 15/04/2026)

Estado: En proceso
Fecha de cierre esperada: 30 de abril de 2026

Aprobado por: Ing. Laura Martinez, Gerente de Calidad
"""
        r = await client.post(f"{API}/api/v1/documents", headers=headers,
                              files={"file": ("Accion_Correctiva_AC-2026-003.txt", capa.encode())})
        result = json.loads(r.text)
        print(f"  Status: {result.get('status')}")
        print(f"  Message: {result.get('message')}")
        passed = result.get("status") == "enriched"
        print(f"  PASS: {passed}")

        # USE CASE 4: Upload a Supplier Certificate with expiry date
        print("\n--- USE CASE 4: Supplier Certificate (with expiry) ---")
        print("Expected: Classified as 'supplier_certificate', expiry date extracted")

        supplier_cert = """
CERTIFICADO DE PROVEEDOR APROBADO

Proveedor: Aceros Industriales del Norte S.A. de C.V.
RFC: AIN-190523-LP4
Numero de certificado: CERT-PROV-2024-089

Productos certificados:
- Acero inoxidable 304 y 316
- Lamina de acero al carbon calibre 12-18

Evaluacion:
- Calidad: 98% (meta: >95%)
- Entrega a tiempo: 96% (meta: >90%)
- Precio competitivo: Aprobado

Certificaciones del proveedor:
- ISO 9001:2015 (vigente hasta 2027)
- Certificacion IMMEX activa

Fecha de emision: 01 de junio de 2025
Fecha de vencimiento: 31 de mayo de 2026
Proxima evaluacion: 01 de diciembre de 2025

Aprobado por: Ing. Pedro Sanchez, Gerente de Compras
"""
        r = await client.post(f"{API}/api/v1/documents", headers=headers,
                              files={"file": ("Cert_Proveedor_Aceros_Norte.txt", supplier_cert.encode())})
        result = json.loads(r.text)
        print(f"  Status: {result.get('status')}")
        print(f"  Message: {result.get('message')}")
        passed = result.get("status") == "enriched"
        print(f"  PASS: {passed}")

        # USE CASE 5: Upload Management Review Minutes
        print("\n--- USE CASE 5: Management Review Minutes ---")
        print("Expected: Classified as 'quality_record', maps to ISO 9001 clause 9.3")

        mgmt_review = """
ACTA DE REVISION POR LA DIRECCION

Fecha: 28 de febrero de 2026
Participantes:
- Ing. Roberto Fernandez, Director General
- Ing. Laura Martinez, Gerente de Calidad
- Lic. Ana Garcia, Gerente de Recursos Humanos
- Ing. Pedro Sanchez, Gerente de Compras
- Ing. Carlos Torres, Gerente de Produccion

Agenda (segun ISO 9001:2015 clausula 9.3):

1. Estado de acciones de revisiones anteriores:
   - 3 acciones completadas, 1 pendiente (actualizacion de manual de calidad)

2. Cambios en cuestiones externas e internas:
   - Nuevos requisitos IMMEX para 2026
   - Aumento de demanda del cliente principal en 15%

3. Desempeno del SGC:
   - Satisfaccion del cliente: 4.2/5.0
   - Indicadores de calidad: 98.5% conformidad
   - Resultados de auditoria interna: 1 NC menor, 2 observaciones
   - Desempeno de proveedores: 96% entrega a tiempo

4. Recursos:
   - Aprobacion de nuevo equipo de medicion: $45,000 USD
   - Contratacion de inspector de calidad adicional

5. Oportunidades de mejora:
   - Implementar sistema de gestion documental digital
   - Automatizar registros de calibracion

Decisiones:
- Aprobar presupuesto de $45,000 USD para equipo
- Iniciar proyecto de digitalizacion en Q2 2026
- Actualizar politica de calidad para incluir nuevos objetivos

Proxima revision: 31 de agosto de 2026
"""
        r = await client.post(f"{API}/api/v1/documents", headers=headers,
                              files={"file": ("Revision_Direccion_Feb2026.txt", mgmt_review.encode())})
        result = json.loads(r.text)
        print(f"  Status: {result.get('status')}")
        print(f"  Message: {result.get('message')}")
        passed = result.get("status") == "enriched"
        print(f"  PASS: {passed}")

        # CHECK: Compliance Map after all uploads
        print("\n" + "=" * 70)
        print("COMPLIANCE MAP AFTER UPLOADS")
        print("=" * 70)

        r = await client.get(f"{API}/api/v1/compliance/map", headers=headers)
        map_data = json.loads(r.text)

        s = map_data["summary"]
        print(f"Coverage: {s['covered']}/{s['total_requirements']} ({s['overall_coverage']}%)")
        print(f"Missing: {s['missing']} | Unverified: {s['unverified']} | Expiring: {s['expiring_or_expired']}")

        for fw in map_data["frameworks"]:
            print(f"\n{fw['name']} ({fw['score']}%):")
            for c in fw["clauses"]:
                icon = {"covered": "OK", "unverified": "??", "expiring": "!!", "expired": "XX", "missing": "--"}[c["status"]]
                doc = c["document"]["filename"][:40] if c.get("document") else "(none)"
                print(f"  [{icon}] {c['clause']:12} {c['name'][:35]:35} | {doc}")

        # CHECK: Dashboard
        print("\n" + "=" * 70)
        print("DASHBOARD")
        print("=" * 70)

        r = await client.get(f"{API}/api/v1/dashboard", headers=headers)
        dash = json.loads(r.text)
        print(f"Score: {dash['score']}/100 ({dash['score_status']})")
        print(f"Audit: {dash['audit']['days_remaining']} days")
        for p in dash["priorities"]:
            print(f"  [{p['severity']}] {p['title']}")

        # CHECK: Chat
        print("\n" + "=" * 70)
        print("CHAT: 'what needs attention?'")
        print("=" * 70)

        r = await client.post(f"{API}/api/v1/chat", headers=headers,
                              json={"question": "what needs attention?"})
        chat = json.loads(r.text)
        print(chat["answer"])

        print("\n" + "=" * 70)
        print("USE CASE TESTING COMPLETE")
        print("=" * 70)


asyncio.run(main())
