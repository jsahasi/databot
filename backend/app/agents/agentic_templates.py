"""Agentic event creation template map.

Maps decision tree paths to ON24 template event IDs (client_id=65000)
and their publicly accessible console thumbnail URLs.

Two platform types: Elite and Vonage. A client is one or the other,
determined by the `elite-account-type` client property.
Each platform has 54 templates (9 use cases x 6 layout variants).

Thumbnail URL pattern:
  https://wcc.on24.com/event/{id_split}/rt/1/{ThumbnailName}.png
  where id_split = event_id split into 2-char groups joined by /
"""

# ── Platform detection ──


def get_platform_type(client_properties: dict) -> str:
    """Determine platform type from client properties.
    Returns 'elite' or 'vonage'.

    Uses `enable_VCU_option_vonage` property — 'Yes' means Vonage-powered.
    """
    vonage_flag = (client_properties.get("enable_VCU_option_vonage", {}).get("value") or "").strip()
    if vonage_flag.lower() == "yes":
        return "vonage"
    return "elite"


# ── Vonage templates (client_id=65000) ──
# Template event IDs by (use_case, layout_variant)
# Layout variants: LOCKED_SLIDES, EDITABLE_SLIDES, LOCKED_NO_SLIDES,
#   EDITABLE_NO_SLIDES, EDITABLE_MENU_DOCK, OTHER_TYPE

VONAGE_TEMPLATES: dict[tuple[str, str], dict] = {
    # ── Demand Generation ──
    ("DEMAND_GEN", "LOCKED_SLIDES"): {"event_id": 4835925, "thumb": "DemandGenLockedSlides"},
    ("DEMAND_GEN", "EDITABLE_SLIDES"): {"event_id": 4831659, "thumb": "DemandGenEditableSlides"},
    ("DEMAND_GEN", "LOCKED_NO_SLIDES"): {"event_id": 4867681, "thumb": "DemandGenLockedNoSlides"},
    ("DEMAND_GEN", "EDITABLE_NO_SLIDES"): {"event_id": 4860249, "thumb": "DemandGenEditableNoSlides"},
    ("DEMAND_GEN", "EDITABLE_MENU_DOCK"): {"event_id": 4860283, "thumb": "DemandGenEditableMenuDock"},
    ("DEMAND_GEN", "OTHER_TYPE"): {"event_id": 4860334, "thumb": "DemandGenOtherType"},
    # ── Partner Enablement ──
    ("PARTNER_ENABLEMENT", "LOCKED_SLIDES"): {"event_id": 4836047, "thumb": "PartnerEnablementLockedSlides"},
    ("PARTNER_ENABLEMENT", "EDITABLE_SLIDES"): {"event_id": 4836063, "thumb": "PartnerEnablementEditableSlides"},
    ("PARTNER_ENABLEMENT", "LOCKED_NO_SLIDES"): {"event_id": 4867686, "thumb": "PartnerEnablementLockedNoSlides"},
    ("PARTNER_ENABLEMENT", "EDITABLE_NO_SLIDES"): {"event_id": 4860346, "thumb": "PartnerEnablementEditableNoSlides"},
    ("PARTNER_ENABLEMENT", "EDITABLE_MENU_DOCK"): {"event_id": 4860358, "thumb": "PartnerEnablementEditableMenuDock"},
    ("PARTNER_ENABLEMENT", "OTHER_TYPE"): {"event_id": 4860360, "thumb": "PartnerEnablementOtherType"},
    # ── Member Enrollment ──
    ("MEMBER_ENROLLMENT", "LOCKED_SLIDES"): {"event_id": 4836347, "thumb": "MemberEnrollmentLockedSlides"},
    ("MEMBER_ENROLLMENT", "EDITABLE_SLIDES"): {"event_id": 4836357, "thumb": "MemberEnrollmentEditableSlides"},
    ("MEMBER_ENROLLMENT", "LOCKED_NO_SLIDES"): {"event_id": 4867688, "thumb": "MemberEnrollmentLockedNoSlides"},
    ("MEMBER_ENROLLMENT", "EDITABLE_NO_SLIDES"): {"event_id": 4860369, "thumb": "MemberEnrollmentEditableNoSlides"},
    ("MEMBER_ENROLLMENT", "EDITABLE_MENU_DOCK"): {"event_id": 4860374, "thumb": "MemberEnrollmentEditableMenuDock"},
    ("MEMBER_ENROLLMENT", "OTHER_TYPE"): {"event_id": 4860381, "thumb": "MemberEnrollmentOtherType"},
    # ── Product Feedback ──
    ("PRODUCT_FEEDBACK", "LOCKED_SLIDES"): {"event_id": 4836361, "thumb": "ProductFeedbackLockedSlides"},
    ("PRODUCT_FEEDBACK", "EDITABLE_SLIDES"): {"event_id": 4836363, "thumb": "ProductFeedbackEditableSlides"},
    ("PRODUCT_FEEDBACK", "LOCKED_NO_SLIDES"): {"event_id": 4867689, "thumb": "ProductFeedbackLockedNoSlides"},
    ("PRODUCT_FEEDBACK", "EDITABLE_NO_SLIDES"): {"event_id": 4860384, "thumb": "ProductFeedbackEditableNoSlides"},
    ("PRODUCT_FEEDBACK", "EDITABLE_MENU_DOCK"): {"event_id": 4860391, "thumb": "ProductFeedbackEditableMenuDock"},
    ("PRODUCT_FEEDBACK", "OTHER_TYPE"): {"event_id": 4860400, "thumb": "ProductFeedbackOtherType"},
    # ── HCP Engagement ──
    ("HCP_ENGAGEMENT", "LOCKED_SLIDES"): {"event_id": 4836378, "thumb": "HCPLockedSlides"},
    ("HCP_ENGAGEMENT", "EDITABLE_SLIDES"): {"event_id": 4836391, "thumb": "HCPEditableSlides"},
    ("HCP_ENGAGEMENT", "LOCKED_NO_SLIDES"): {"event_id": 4867692, "thumb": "HCPLockedNoSlides"},
    ("HCP_ENGAGEMENT", "EDITABLE_NO_SLIDES"): {"event_id": 4860421, "thumb": "HCPEditableNoSlides"},
    ("HCP_ENGAGEMENT", "EDITABLE_MENU_DOCK"): {"event_id": 4860440, "thumb": "HCPEditableMenuDock"},
    ("HCP_ENGAGEMENT", "OTHER_TYPE"): {"event_id": 4860456, "thumb": "HCPOtherType"},
    # ── KOL Engagement ──
    ("KOL_ENGAGEMENT", "LOCKED_SLIDES"): {"event_id": 4836395, "thumb": "KOLLockedSlides"},
    ("KOL_ENGAGEMENT", "EDITABLE_SLIDES"): {"event_id": 4836396, "thumb": "KOLEditableSlides"},
    ("KOL_ENGAGEMENT", "LOCKED_NO_SLIDES"): {"event_id": 4867696, "thumb": "KOLLockedNoSlides"},
    ("KOL_ENGAGEMENT", "EDITABLE_NO_SLIDES"): {"event_id": 4860464, "thumb": "KOLEditableNoSlides"},
    ("KOL_ENGAGEMENT", "EDITABLE_MENU_DOCK"): {"event_id": 4860475, "thumb": "KOLEditableMenuDock"},
    ("KOL_ENGAGEMENT", "OTHER_TYPE"): {"event_id": 4860482, "thumb": "KOLOtherType"},
    # ── Certification / Training ──
    ("CERTIFICATION_TRAINING", "LOCKED_SLIDES"): {"event_id": 4836398, "thumb": "CertificationLockedSlides"},
    ("CERTIFICATION_TRAINING", "EDITABLE_SLIDES"): {"event_id": 4836408, "thumb": "CertificationEditableSlides"},
    ("CERTIFICATION_TRAINING", "LOCKED_NO_SLIDES"): {"event_id": 4867702, "thumb": "CertificationLockedNoSlides"},
    ("CERTIFICATION_TRAINING", "EDITABLE_NO_SLIDES"): {"event_id": 4860492, "thumb": "CertificationEditableNoSlides"},
    ("CERTIFICATION_TRAINING", "EDITABLE_MENU_DOCK"): {"event_id": 4860496, "thumb": "CertificationEditableMenuDock"},
    ("CERTIFICATION_TRAINING", "OTHER_TYPE"): {"event_id": 4860501, "thumb": "CertificationOtherType"},
    # ── Asset Management / Financial Services ──
    ("ASSET_SERVICES", "LOCKED_SLIDES"): {"event_id": 4837350, "thumb": "AssetManagementLockedSlides"},
    ("ASSET_SERVICES", "EDITABLE_SLIDES"): {"event_id": 4837351, "thumb": "AssetManagementEditableSlides"},
    ("ASSET_SERVICES", "LOCKED_NO_SLIDES"): {"event_id": 4867725, "thumb": "AssetManagementLockedNoSlides"},
    ("ASSET_SERVICES", "EDITABLE_NO_SLIDES"): {"event_id": 4860505, "thumb": "AssetManagementEditableNoSlides"},
    ("ASSET_SERVICES", "EDITABLE_MENU_DOCK"): {"event_id": 4860511, "thumb": "AssetManagementEditableMenuDock"},
    ("ASSET_SERVICES", "OTHER_TYPE"): {"event_id": 4860516, "thumb": "AssetManagementOtherType"},
    # ── Insurance ──
    ("INSURANCE", "LOCKED_SLIDES"): {"event_id": 4837353, "thumb": "InsuranceLockedSlides"},
    ("INSURANCE", "EDITABLE_SLIDES"): {"event_id": 4837356, "thumb": "InsuranceEditableSlides"},
    ("INSURANCE", "LOCKED_NO_SLIDES"): {"event_id": 4867710, "thumb": "InsuranceLockedNoSlides"},
    ("INSURANCE", "EDITABLE_NO_SLIDES"): {"event_id": 4860522, "thumb": "InsuranceEditableNoSlides"},
    ("INSURANCE", "EDITABLE_MENU_DOCK"): {"event_id": 4860524, "thumb": "InsuranceEditableMenuDock"},
    ("INSURANCE", "OTHER_TYPE"): {"event_id": 4860532, "thumb": "InsuranceOtherType"},
}

# Locked "Other Type" templates (On Demand / Simulive — no layout questions)
VONAGE_LOCKED_OTHER_TEMPLATES: dict[str, dict] = {
    "DEMAND_GEN": {"event_id": 5075079, "thumb": "DemandGenOtherType"},
    "PARTNER_ENABLEMENT": {"event_id": 5075080, "thumb": "PartnerEnablementOtherType"},
    "MEMBER_ENROLLMENT": {"event_id": 5075081, "thumb": "MemberEnrollmentOtherType"},
    "PRODUCT_FEEDBACK": {"event_id": 5075084, "thumb": "ProductFeedbackOtherType"},
    "HCP_ENGAGEMENT": {"event_id": 5075085, "thumb": "HCPOtherType"},
    "KOL_ENGAGEMENT": {"event_id": 5075086, "thumb": "KOLOtherType"},
    "CERTIFICATION_TRAINING": {"event_id": 5075087, "thumb": "CertificationOtherType"},
    "ASSET_SERVICES": {"event_id": 5075088, "thumb": "AssetManagementOtherType"},
    "INSURANCE": {"event_id": 5075089, "thumb": "InsuranceOtherType"},
}


def _event_id_to_path(eid: int) -> str:
    """Split event ID into 2-char groups for thumbnail URL."""
    s = str(eid)
    return "/".join(s[i : i + 2] for i in range(0, len(s), 2))


def get_console_thumbnail_url(event_id: int, thumb_name: str) -> str:
    return f"https://wcc.on24.com/event/{_event_id_to_path(event_id)}/rt/1/{thumb_name}.png"


def get_reg_thumbnail_url(event_id: int, thumb_name: str) -> str:
    # Registration thumbnails use the use-case name + "Reg"
    # e.g., PartnerEnablementReg.png
    base = thumb_name.split("Locked")[0].split("Editable")[0].split("Other")[0]
    return f"https://wcc.on24.com/event/{_event_id_to_path(event_id)}/rt/1/{base}Reg.png"


# Decision tree answer → use case key mapping
USE_CASE_MAP = {
    "Demand Generation": "DEMAND_GEN",
    "Partner Enablement": "PARTNER_ENABLEMENT",
    "Member Enrollment": "MEMBER_ENROLLMENT",
    "Product Feedback": "PRODUCT_FEEDBACK",
    "Health Care Provider Engagement": "HCP_ENGAGEMENT",
    "Key Opinion Leader Engagement": "KOL_ENGAGEMENT",
    "Certification / Training": "CERTIFICATION_TRAINING",
    "Asset Management / Financial Services": "ASSET_SERVICES",
    "Insurance": "INSURANCE",
}


# Decision tree answers → layout variant mapping
def get_layout_variant(event_type: str, slides: str | None, nav: str | None, layout: str | None) -> str:
    """Map decision tree answers to a layout variant key."""
    if event_type != "Live Video":
        return "OTHER_TYPE"
    if slides == "Screen Share":
        return "LOCKED_NO_SLIDES" if layout == "Intelligent Layout" else "EDITABLE_NO_SLIDES"
    if slides == "Slides":
        if nav == "Bottom Tools Dock":
            return "EDITABLE_MENU_DOCK"
        return "LOCKED_SLIDES" if layout == "Intelligent Layout" else "EDITABLE_SLIDES"
    return "EDITABLE_SLIDES"  # fallback


# ── Elite templates (client_id=66000) ──

ELITE_TEMPLATES: dict[tuple[str, str], dict] = {
    # ── Demand Generation ──
    ("DEMAND_GEN", "LOCKED_SLIDES"): {"event_id": 4883291, "thumb": "DemandGenLockedSlides"},
    ("DEMAND_GEN", "EDITABLE_SLIDES"): {"event_id": 4891470, "thumb": "DemandGenEditableSlides"},
    ("DEMAND_GEN", "LOCKED_NO_SLIDES"): {"event_id": 4894419, "thumb": "DemandGenLockedNoSlides"},
    ("DEMAND_GEN", "EDITABLE_NO_SLIDES"): {"event_id": 4891469, "thumb": "DemandGenEditableNoSlides"},
    ("DEMAND_GEN", "EDITABLE_MENU_DOCK"): {"event_id": 4883233, "thumb": "DemandGenEditableMenuDock"},
    ("DEMAND_GEN", "OTHER_TYPE"): {"event_id": 4891474, "thumb": "DemandGenOtherType"},
    # ── Partner Enablement ──
    ("PARTNER_ENABLEMENT", "LOCKED_SLIDES"): {"event_id": 4891462, "thumb": "PartnerEnablementLockedSlides"},
    ("PARTNER_ENABLEMENT", "EDITABLE_SLIDES"): {"event_id": 4891422, "thumb": "PartnerEnablementEditableSlides"},
    ("PARTNER_ENABLEMENT", "LOCKED_NO_SLIDES"): {"event_id": 4893203, "thumb": "PartnerEnablementLockedNoSlides"},
    ("PARTNER_ENABLEMENT", "EDITABLE_NO_SLIDES"): {"event_id": 4891421, "thumb": "PartnerEnablementEditableNoSlides"},
    ("PARTNER_ENABLEMENT", "EDITABLE_MENU_DOCK"): {"event_id": 4891424, "thumb": "PartnerEnablementEditableMenuDock"},
    ("PARTNER_ENABLEMENT", "OTHER_TYPE"): {"event_id": 4891464, "thumb": "PartnerEnablementOtherType"},
    # ── Member Enrollment ──
    ("MEMBER_ENROLLMENT", "LOCKED_SLIDES"): {"event_id": 4891414, "thumb": "MemberEnrollmentLockedSlides"},
    ("MEMBER_ENROLLMENT", "EDITABLE_SLIDES"): {"event_id": 4891403, "thumb": "MemberEnrollmentEditableSlides"},
    ("MEMBER_ENROLLMENT", "LOCKED_NO_SLIDES"): {"event_id": 4893196, "thumb": "MemberEnrollmentLockedNoSlides"},
    ("MEMBER_ENROLLMENT", "EDITABLE_NO_SLIDES"): {"event_id": 4891395, "thumb": "MemberEnrollmentEditableNoSlides"},
    ("MEMBER_ENROLLMENT", "EDITABLE_MENU_DOCK"): {"event_id": 4891408, "thumb": "MemberEnrollmentEditableMenuDock"},
    ("MEMBER_ENROLLMENT", "OTHER_TYPE"): {"event_id": 4891415, "thumb": "MemberEnrollmentOtherType"},
    # ── Product Feedback ──
    ("PRODUCT_FEEDBACK", "LOCKED_SLIDES"): {"event_id": 4891388, "thumb": "ProductFeedbackLockedSlides"},
    ("PRODUCT_FEEDBACK", "EDITABLE_SLIDES"): {"event_id": 4891379, "thumb": "ProductFeedbackEditableSlides"},
    ("PRODUCT_FEEDBACK", "LOCKED_NO_SLIDES"): {"event_id": 4893195, "thumb": "ProductFeedbackLockedNoSlides"},
    ("PRODUCT_FEEDBACK", "EDITABLE_NO_SLIDES"): {"event_id": 4891376, "thumb": "ProductFeedbackEditableNoSlides"},
    ("PRODUCT_FEEDBACK", "EDITABLE_MENU_DOCK"): {"event_id": 4891385, "thumb": "ProductFeedbackEditableMenuDock"},
    ("PRODUCT_FEEDBACK", "OTHER_TYPE"): {"event_id": 4891390, "thumb": "ProductFeedbackOtherType"},
    # ── HCP Engagement ──
    ("HCP_ENGAGEMENT", "LOCKED_SLIDES"): {"event_id": 4891351, "thumb": "HCPLockedSlides"},
    ("HCP_ENGAGEMENT", "EDITABLE_SLIDES"): {"event_id": 4891332, "thumb": "HCPEditableSlides"},
    ("HCP_ENGAGEMENT", "LOCKED_NO_SLIDES"): {"event_id": 4893193, "thumb": "HCPLockedNoSlides"},
    ("HCP_ENGAGEMENT", "EDITABLE_NO_SLIDES"): {"event_id": 4891330, "thumb": "HCPEditableNoSlides"},
    ("HCP_ENGAGEMENT", "EDITABLE_MENU_DOCK"): {"event_id": 4891346, "thumb": "HCPEditableMenuDock"},
    ("HCP_ENGAGEMENT", "OTHER_TYPE"): {"event_id": 4891353, "thumb": "HCPOtherType"},
    # ── KOL Engagement ──
    ("KOL_ENGAGEMENT", "LOCKED_SLIDES"): {"event_id": 4891315, "thumb": "KOLLockedSlides"},
    ("KOL_ENGAGEMENT", "EDITABLE_SLIDES"): {"event_id": 4891306, "thumb": "KOLEditableSlides"},
    ("KOL_ENGAGEMENT", "LOCKED_NO_SLIDES"): {"event_id": 4893190, "thumb": "KOLLockedNoSlides"},
    ("KOL_ENGAGEMENT", "EDITABLE_NO_SLIDES"): {"event_id": 4891305, "thumb": "KOLEditableNoSlides"},
    ("KOL_ENGAGEMENT", "EDITABLE_MENU_DOCK"): {"event_id": 4891309, "thumb": "KOLEditableMenuDock"},
    ("KOL_ENGAGEMENT", "OTHER_TYPE"): {"event_id": 4891317, "thumb": "KOLOtherType"},
    # ── Certification / Training ──
    ("CERTIFICATION_TRAINING", "LOCKED_SLIDES"): {"event_id": 4891300, "thumb": "CertificationLockedSlides"},
    ("CERTIFICATION_TRAINING", "EDITABLE_SLIDES"): {"event_id": 4891294, "thumb": "CertificationEditableSlides"},
    ("CERTIFICATION_TRAINING", "LOCKED_NO_SLIDES"): {"event_id": 4893188, "thumb": "CertificationLockedNoSlides"},
    ("CERTIFICATION_TRAINING", "EDITABLE_NO_SLIDES"): {"event_id": 4891275, "thumb": "CertificationEditableNoSlides"},
    ("CERTIFICATION_TRAINING", "EDITABLE_MENU_DOCK"): {"event_id": 4891295, "thumb": "CertificationEditableMenuDock"},
    ("CERTIFICATION_TRAINING", "OTHER_TYPE"): {"event_id": 4891303, "thumb": "CertificationOtherType"},
    # ── Asset Management / Financial Services ──
    ("ASSET_SERVICES", "LOCKED_SLIDES"): {"event_id": 4891234, "thumb": "AssetManagementLockedSlides"},
    ("ASSET_SERVICES", "EDITABLE_SLIDES"): {"event_id": 4891219, "thumb": "AssetManagementEditableSlides"},
    ("ASSET_SERVICES", "LOCKED_NO_SLIDES"): {"event_id": 4893183, "thumb": "AssetManagementLockedNoSlides"},
    ("ASSET_SERVICES", "EDITABLE_NO_SLIDES"): {"event_id": 4891215, "thumb": "AssetManagementEditableNoSlides"},
    ("ASSET_SERVICES", "EDITABLE_MENU_DOCK"): {"event_id": 4891229, "thumb": "AssetManagementEditableMenuDock"},
    ("ASSET_SERVICES", "OTHER_TYPE"): {"event_id": 4891237, "thumb": "AssetManagementOtherType"},
    # ── Insurance ──
    ("INSURANCE", "LOCKED_SLIDES"): {"event_id": 4891206, "thumb": "InsuranceLockedSlides"},
    ("INSURANCE", "EDITABLE_SLIDES"): {"event_id": 4891188, "thumb": "InsuranceEditableSlides"},
    ("INSURANCE", "LOCKED_NO_SLIDES"): {"event_id": 4893181, "thumb": "InsuranceLockedNoSlides"},
    ("INSURANCE", "EDITABLE_NO_SLIDES"): {"event_id": 4891185, "thumb": "InsuranceEditableNoSlides"},
    ("INSURANCE", "EDITABLE_MENU_DOCK"): {"event_id": 4891193, "thumb": "InsuranceEditableMenuDock"},
    ("INSURANCE", "OTHER_TYPE"): {"event_id": 4891211, "thumb": "InsuranceOtherType"},
}

ELITE_LOCKED_OTHER_TEMPLATES: dict[str, dict] = {}


# ── Unified lookup ──


def get_template(
    platform: str,
    use_case: str,
    layout_variant: str,
) -> dict | None:
    """Look up the template for a given platform + use case + layout.

    Args:
        platform: 'elite' or 'vonage'
        use_case: key from USE_CASE_MAP values (e.g. 'DEMAND_GEN')
        layout_variant: from get_layout_variant() (e.g. 'LOCKED_SLIDES')

    Returns:
        {'event_id': int, 'thumb': str} or None
    """
    templates = VONAGE_TEMPLATES if platform == "vonage" else ELITE_TEMPLATES
    tmpl = templates.get((use_case, layout_variant))
    if tmpl:
        return {
            **tmpl,
            "console_thumbnail": get_console_thumbnail_url(tmpl["event_id"], tmpl["thumb"]),
            "reg_thumbnail": get_reg_thumbnail_url(tmpl["event_id"], tmpl["thumb"]),
        }
    return None
