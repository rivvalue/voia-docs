"""
Industry-Specific Topic Hints Configuration

This module defines platform-wide default hints for conversational survey questions,
mapped by industry and survey topic. These hints customize AI prompts to ask more
relevant, industry-specific questions.

Architecture:
- Platform admin maintains this file (default hints library)
- BusinessAccount.industry_topic_hints JSON can override specific hints
- Campaign inherits from BusinessAccount or uses platform defaults

Usage in PromptTemplateService:
- Inject hints into topic descriptions to guide GPT-4o question generation
- Example: "Product Quality (focus on: defects, throughput, line reliability)"
"""

INDUSTRY_TOPIC_HINTS = {
    "EMS": {
        "Product Quality": "defects, throughput, line reliability, quality control, yield rates",
        "Support Experience": "technical support, troubleshooting response, equipment downtime, spare parts availability",
        "Service Rating": "on-time delivery, order accuracy, supply chain reliability",
        "NPS Score": "recommendation likelihood, overall satisfaction, partnership value",
        "Pricing Value": "cost competitiveness, volume pricing, contract terms",
        "User Experience": "order process, communication, documentation quality",
        "Feature Requests": "new capabilities, process improvements, technology upgrades",
        "Improvement Suggestions": "efficiency gains, quality enhancements, delivery optimization"
    },
    
    "Healthcare": {
        "Product Quality": "workflow reliability, data accuracy, patient safety, regulatory compliance, system uptime",
        "Support Experience": "clinical support, issue resolution, training resources, technical responsiveness",
        "Service Rating": "implementation support, system integration, ongoing maintenance",
        "NPS Score": "recommendation to peers, overall satisfaction, trust in solution",
        "Pricing Value": "ROI, total cost of ownership, value for investment",
        "User Experience": "interface usability, workflow integration, ease of use, learning curve",
        "Feature Requests": "clinical workflow needs, reporting capabilities, integration requirements",
        "Improvement Suggestions": "efficiency improvements, user interface enhancements, training resources"
    },
    
    "Software": {
        "Product Quality": "bug frequency, performance, reliability, feature completeness, stability",
        "Support Experience": "technical support quality, documentation, response time, issue resolution",
        "Service Rating": "implementation support, onboarding, training, account management",
        "NPS Score": "recommendation likelihood, overall satisfaction, product-market fit",
        "Pricing Value": "pricing competitiveness, feature value, subscription model",
        "User Experience": "interface design, ease of use, workflow efficiency, mobile experience",
        "Feature Requests": "missing features, integrations, workflow improvements, scalability",
        "Improvement Suggestions": "performance optimization, UI/UX enhancements, feature prioritization"
    },
    
    "Financial Services": {
        "Product Quality": "accuracy, security, compliance, transaction reliability, data integrity",
        "Support Experience": "account support, dispute resolution, regulatory guidance, responsiveness",
        "Service Rating": "account management, advisory services, reporting quality, compliance support",
        "NPS Score": "recommendation likelihood, trust level, relationship satisfaction",
        "Pricing Value": "fee structure, cost transparency, value for services",
        "User Experience": "platform usability, statement clarity, mobile banking, self-service tools",
        "Feature Requests": "new financial products, digital capabilities, reporting tools, integration needs",
        "Improvement Suggestions": "process streamlining, transparency, communication, digital experience"
    },
    
    "Professional Services": {
        "Product Quality": "deliverable quality, expertise, methodology, timeliness, results achieved",
        "Support Experience": "responsiveness, communication, flexibility, problem-solving",
        "Service Rating": "project management, team collaboration, knowledge transfer, follow-up",
        "NPS Score": "recommendation likelihood, overall satisfaction, partnership value",
        "Pricing Value": "pricing transparency, ROI, value delivered, cost-effectiveness",
        "User Experience": "engagement process, communication style, collaboration tools, reporting",
        "Feature Requests": "service offerings, delivery methods, expertise areas, tools",
        "Improvement Suggestions": "process improvements, communication enhancements, delivery optimization"
    },
    
    "Retail": {
        "Product Quality": "product quality, inventory availability, freshness, selection, brand variety",
        "Support Experience": "customer service, returns process, issue resolution, store staff helpfulness",
        "Service Rating": "checkout speed, store cleanliness, product displays, stock availability",
        "NPS Score": "recommendation likelihood, shopping experience, loyalty",
        "Pricing Value": "price competitiveness, promotions, value for money, pricing transparency",
        "User Experience": "store layout, online ordering, mobile app, payment options, convenience",
        "Feature Requests": "product requests, services, delivery options, store features",
        "Improvement Suggestions": "shopping experience, product selection, convenience, service quality"
    },
    
    "Telecommunications": {
        "Product Quality": "network reliability, call quality, data speed, coverage, service uptime",
        "Support Experience": "technical support, billing support, issue resolution, wait times",
        "Service Rating": "installation, account management, service activation, network maintenance",
        "NPS Score": "recommendation likelihood, overall satisfaction, loyalty",
        "Pricing Value": "plan pricing, contract terms, hidden fees, value for features",
        "User Experience": "account portal, mobile app, self-service tools, billing clarity",
        "Feature Requests": "plan options, coverage expansion, feature additions, bundle offerings",
        "Improvement Suggestions": "network quality, billing transparency, support efficiency, pricing flexibility"
    },
    
    "Education": {
        "Product Quality": "content quality, curriculum relevance, learning outcomes, resource availability",
        "Support Experience": "instructor support, technical assistance, administrative help, responsiveness",
        "Service Rating": "course delivery, platform reliability, assessment fairness, feedback quality",
        "NPS Score": "recommendation to others, overall satisfaction, value received",
        "Pricing Value": "tuition value, financial aid, cost transparency, ROI on education",
        "User Experience": "platform usability, course navigation, mobile access, learning tools",
        "Feature Requests": "course offerings, learning formats, technology tools, support services",
        "Improvement Suggestions": "teaching methods, platform improvements, support enhancements, course content"
    },
    
    "Hospitality": {
        "Product Quality": "cleanliness, amenities, room quality, facility maintenance, comfort",
        "Support Experience": "staff friendliness, concierge service, issue resolution, responsiveness",
        "Service Rating": "check-in/out process, housekeeping, dining quality, facility services",
        "NPS Score": "recommendation likelihood, overall experience, return intent",
        "Pricing Value": "rate fairness, value for money, pricing transparency, package deals",
        "User Experience": "booking process, amenity access, mobile app, loyalty program",
        "Feature Requests": "amenity additions, service offerings, facility improvements, dining options",
        "Improvement Suggestions": "service quality, facility updates, staff training, convenience features"
    },
    
    "Generic": {
        "Product Quality": "quality, reliability, performance, features, value delivered",
        "Support Experience": "customer service, responsiveness, problem resolution, support quality",
        "Service Rating": "overall service, delivery, implementation, follow-up",
        "NPS Score": "recommendation likelihood, overall satisfaction, loyalty",
        "Pricing Value": "pricing fairness, value for money, cost transparency",
        "User Experience": "ease of use, convenience, accessibility, overall experience",
        "Feature Requests": "desired features, improvements, additions, enhancements",
        "Improvement Suggestions": "general improvements, quality enhancements, service optimization"
    }
}


def get_available_industries():
    """
    Get list of available industries for UI selection
    
    Returns:
        list: Industry names sorted alphabetically, with Generic last
    """
    industries = sorted([k for k in INDUSTRY_TOPIC_HINTS.keys() if k != "Generic"])
    industries.append("Generic")
    return industries


def get_industry_hints(industry):
    """
    Get topic hints for a specific industry
    
    Args:
        industry (str): Industry name
    
    Returns:
        dict: Topic hints mapping, or Generic hints if industry not found
    """
    return INDUSTRY_TOPIC_HINTS.get(industry, INDUSTRY_TOPIC_HINTS["Generic"])


def get_topic_hint(industry, topic):
    """
    Get hint for a specific industry and topic
    
    Args:
        industry (str): Industry name
        topic (str): Survey topic name
    
    Returns:
        str: Hint keywords or empty string if not found
    """
    hints = get_industry_hints(industry)
    return hints.get(topic, "")


def merge_custom_hints(industry, custom_hints):
    """
    Merge custom business account hints with platform defaults
    
    Args:
        industry (str): Industry name
        custom_hints (dict): Custom hints from BusinessAccount.industry_topic_hints
    
    Returns:
        dict: Merged hints (custom overrides platform defaults)
    """
    platform_hints = get_industry_hints(industry).copy()
    
    if custom_hints and isinstance(custom_hints, dict):
        platform_hints.update(custom_hints)
    
    return platform_hints
