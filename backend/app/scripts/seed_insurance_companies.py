"""
Seed script for Indian insurance companies.

Run with: python -m app.scripts.seed_insurance_companies
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.insurance import InsuranceCompany


# Top 20 Indian Health Insurance Companies and TPAs
INSURANCE_COMPANIES = [
    {
        "name": "Star Health and Allied Insurance Company Ltd",
        "code": "STAR",
        "contact_email": "customercare@starhealth.in",
        "contact_phone": "1800-425-2255",
        "tpa_name": "Star Health Insurance",
        "tpa_email": "claims@starhealth.in",
        "claim_submission_email": "claims@starhealth.in",
        "claim_submission_url": "https://www.starhealth.in/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("50000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "Star Health has one of the largest cashless hospital networks in India. Pre-auth required for procedures above 50k.",
    },
    {
        "name": "HDFC ERGO General Insurance Company Ltd",
        "code": "HDFC",
        "contact_email": "customerservice@hdfcergo.com",
        "contact_phone": "1800-2575-757",
        "tpa_name": "Medi Assist",
        "tpa_email": "claims@mediassist.in",
        "claim_submission_email": "health.claims@hdfcergo.com",
        "claim_submission_url": "https://www.hdfcergo.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("75000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "TPA: Medi Assist. Quick claim settlement. Pre-auth mandatory for planned procedures.",
    },
    {
        "name": "ICICI Lombard General Insurance Company Ltd",
        "code": "ICICI",
        "contact_email": "customersupport@icicilombard.com",
        "contact_phone": "1800-2666",
        "tpa_name": "ICICI Lombard",
        "tpa_email": "claims@icicilombard.com",
        "claim_submission_email": "healthclaims@icicilombard.com",
        "claim_submission_url": "https://www.icicilombard.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("50000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "Large network. Online pre-auth facility available.",
    },
    {
        "name": "Care Health Insurance Ltd (Formerly Religare Health)",
        "code": "CARE",
        "contact_email": "customercare@careinsurance.com",
        "contact_phone": "1800-102-4488",
        "tpa_name": "Care Health Insurance",
        "tpa_email": "claims@careinsurance.com",
        "claim_submission_email": "claims@careinsurance.com",
        "claim_submission_url": "https://www.careinsurance.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("40000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "Fast cashless approvals. Pre-auth required above 40k.",
    },
    {
        "name": "Bajaj Allianz General Insurance Company Ltd",
        "code": "BAJAJ",
        "contact_email": "bagichelp@bajajallianz.co.in",
        "contact_phone": "1800-209-5858",
        "tpa_name": "Medi Assist",
        "tpa_email": "claims@mediassist.in",
        "claim_submission_email": "health.claims@bajajallianz.co.in",
        "claim_submission_url": "https://www.bajajallianz.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("50000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "TPA: Medi Assist. Wide network coverage.",
    },
    {
        "name": "Max Bupa Health Insurance Company Ltd",
        "code": "MAXBUPA",
        "contact_email": "contactus@maxbupa.com",
        "contact_phone": "1800-102-1010",
        "tpa_name": "Max Bupa",
        "tpa_email": "claims@maxbupa.com",
        "claim_submission_email": "claims@maxbupa.com",
        "claim_submission_url": "https://www.maxbupa.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("60000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "Premium network hospitals. Pre-auth through online portal.",
    },
    {
        "name": "Aditya Birla Health Insurance Company Ltd",
        "code": "ABHICL",
        "contact_email": "care.health@adityabirlacapital.com",
        "contact_phone": "1800-270-7000",
        "tpa_name": "Aditya Birla Health",
        "tpa_email": "claims@adityabirlacapital.com",
        "claim_submission_email": "health.claims@adityabirlacapital.com",
        "claim_submission_url": "https://health.adityabirlacapital.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("50000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "Digital-first approach. Quick pre-auth approvals.",
    },
    {
        "name": "Niva Bupa Health Insurance Company Ltd",
        "code": "NIVA",
        "contact_email": "customersupport@nivabupa.com",
        "contact_phone": "1800-266-4242",
        "tpa_name": "Niva Bupa",
        "tpa_email": "claims@nivabupa.com",
        "claim_submission_email": "claims@nivabupa.com",
        "claim_submission_url": "https://www.nivabupa.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("50000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "Comprehensive coverage. 24/7 claim support.",
    },
    {
        "name": "The New India Assurance Company Ltd",
        "code": "NIACL",
        "contact_email": "customercare@newindia.co.in",
        "contact_phone": "1800-209-1415",
        "tpa_name": "Medi Assist / Heritage TPA",
        "tpa_email": "claims@mediassist.in",
        "claim_submission_email": "healthclaims@newindia.co.in",
        "claim_submission_url": "https://www.newindia.co.in/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("30000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "PSU insurer. Multiple TPAs. Good rural coverage.",
    },
    {
        "name": "United India Insurance Company Ltd",
        "code": "UIICL",
        "contact_email": "customercare@uiic.co.in",
        "contact_phone": "1800-425-5499",
        "tpa_name": "MD India / Paramount TPA",
        "tpa_email": "claims@mdindia.in",
        "claim_submission_email": "healthclaims@uiic.co.in",
        "claim_submission_url": "https://www.uiic.co.in/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("25000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "PSU insurer. Affordable premiums. Pre-auth at low threshold.",
    },
    {
        "name": "Oriental Insurance Company Ltd",
        "code": "OICL",
        "contact_email": "customercare@orientalinsurance.co.in",
        "contact_phone": "1800-118-485",
        "tpa_name": "Good Health TPA / Paramount TPA",
        "tpa_email": "claims@goodhealthtpa.com",
        "claim_submission_email": "healthclaims@orientalinsurance.co.in",
        "claim_submission_url": "https://www.orientalinsurance.org.in/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("30000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "PSU insurer. Multiple TPAs. Good government tie-ups.",
    },
    {
        "name": "Cholamandalam MS General Insurance Company Ltd",
        "code": "CHOLA",
        "contact_email": "customercare@cholainsurance.com",
        "contact_phone": "1800-200-5544",
        "tpa_name": "Medi Assist",
        "tpa_email": "claims@mediassist.in",
        "claim_submission_email": "healthclaims@cholainsurance.com",
        "claim_submission_url": "https://www.cholainsurance.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("50000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "TPA: Medi Assist. Growing network.",
    },
    {
        "name": "Manipal Cigna Health Insurance Company Ltd",
        "code": "MCHI",
        "contact_email": "customerservice@manipalcigna.com",
        "contact_phone": "1800-102-4488",
        "tpa_name": "Manipal Cigna",
        "tpa_email": "claims@manipalcigna.com",
        "claim_submission_email": "claims@manipalcigna.com",
        "claim_submission_url": "https://www.manipalcigna.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("75000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "Premium healthcare focus. Wellness benefits included.",
    },
    {
        "name": "SBI General Insurance Company Ltd",
        "code": "SBI",
        "contact_email": "customercare@sbigeneral.in",
        "contact_phone": "1800-22-1111",
        "tpa_name": "Medi Assist / Paramount TPA",
        "tpa_email": "claims@mediassist.in",
        "claim_submission_email": "healthclaims@sbigeneral.in",
        "claim_submission_url": "https://www.sbigeneral.in/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("50000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "SBI group company. Wide branch network for assistance.",
    },
    {
        "name": "Raheja QBE General Insurance Company Ltd",
        "code": "RAHEJA",
        "contact_email": "customerservice@qbe.com",
        "contact_phone": "1800-22-9090",
        "tpa_name": "Good Health TPA",
        "tpa_email": "claims@goodhealthtpa.com",
        "claim_submission_email": "health@qbe.com",
        "claim_submission_url": "https://www.qbe.com/in/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("60000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "TPA: Good Health. Niche segments focus.",
    },
    # Major TPAs (Third Party Administrators)
    {
        "name": "Medi Assist Insurance TPA Pvt Ltd",
        "code": "MEDI",
        "contact_email": "customercare@mediassist.in",
        "contact_phone": "1800-102-9655",
        "tpa_name": "Medi Assist",
        "tpa_email": "claims@mediassist.in",
        "claim_submission_email": "claims@mediassist.in",
        "claim_submission_url": "https://www.mediassist.in/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("25000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "India's largest TPA. Handles claims for multiple insurers.",
    },
    {
        "name": "MD India Healthcare Services (TPA) Pvt Ltd",
        "code": "MDINDIA",
        "contact_email": "info@mdindia.in",
        "contact_phone": "1800-425-5070",
        "tpa_name": "MD India",
        "tpa_email": "claims@mdindia.in",
        "claim_submission_email": "claims@mdindia.in",
        "claim_submission_url": "https://www.mdindia.in/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("30000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "Major TPA. Quick turnaround times.",
    },
    {
        "name": "Paramount Health Services & Insurance TPA Pvt Ltd",
        "code": "PARAM",
        "contact_email": "customercare@paramounttpa.com",
        "contact_phone": "1800-425-0000",
        "tpa_name": "Paramount TPA",
        "tpa_email": "claims@paramounttpa.com",
        "claim_submission_email": "claims@paramounttpa.com",
        "claim_submission_url": "https://www.paramounttpa.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("30000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "Well-established TPA. Good network in tier-2 cities.",
    },
    {
        "name": "Good Health TPA Services Ltd",
        "code": "GOOD",
        "contact_email": "info@goodhealthtpa.com",
        "contact_phone": "1800-123-2255",
        "tpa_name": "Good Health TPA",
        "tpa_email": "claims@goodhealthtpa.com",
        "claim_submission_email": "claims@goodhealthtpa.com",
        "claim_submission_url": "https://www.goodhealthtpa.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("25000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "Handles multiple insurer portfolios.",
    },
    {
        "name": "Heritage Health TPA Pvt Ltd",
        "code": "HERITAGE",
        "contact_email": "customercare@heritagetpa.com",
        "contact_phone": "1800-102-4488",
        "tpa_name": "Heritage TPA",
        "tpa_email": "claims@heritagetpa.com",
        "claim_submission_email": "claims@heritagetpa.com",
        "claim_submission_url": "https://www.heritagetpa.com/claims",
        "cashless_available": True,
        "preauth_required": True,
        "preauth_threshold": Decimal("30000.00"),
        "network_type": "PPO",
        "is_active": True,
        "claim_process_notes": "Experienced TPA with pan-India presence.",
    },
]


async def seed_insurance_companies():
    """Seed insurance companies data."""
    async for session in get_async_session():
        try:
            print("Seeding insurance companies...")

            for company_data in INSURANCE_COMPANIES:
                # Check if company already exists
                result = await session.execute(
                    select(InsuranceCompany).where(
                        InsuranceCompany.code == company_data["code"]
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"  ✓ {company_data['name']} already exists, skipping")
                    continue

                # Create new company
                company = InsuranceCompany(**company_data)
                session.add(company)
                print(f"  + Added {company_data['name']}")

            await session.commit()
            print(f"\n✅ Successfully seeded {len(INSURANCE_COMPANIES)} insurance companies!")

        except Exception as e:
            print(f"❌ Error seeding insurance companies: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_insurance_companies())
