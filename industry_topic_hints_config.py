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
        "Satisfaction": "overall satisfaction rating, experience quality, expectations met",
        "Improvement Suggestions": "efficiency gains, quality enhancements, delivery optimization",
        "Additional Comments": "open feedback, general remarks, anything else, free-form comments",
        "Competitor Comparison": "alternative solutions considered, competitor strengths, switching intent, market comparison",
        "Usage Frequency": "how often used, adoption rate, daily vs occasional use, engagement level",
        "Referral Likelihood": "word of mouth, peer recommendations, advocacy, likelihood to refer colleagues"
    },
    "Healthcare": {
        "Product Quality": "workflow reliability, data accuracy, patient safety, regulatory compliance, system uptime",
        "Support Experience": "clinical support, issue resolution, training resources, technical responsiveness",
        "Service Rating": "implementation support, system integration, ongoing maintenance",
        "NPS Score": "recommendation to peers, overall satisfaction, trust in solution",
        "Pricing Value": "ROI, total cost of ownership, value for investment",
        "User Experience": "interface usability, workflow integration, ease of use, learning curve",
        "Satisfaction": "overall satisfaction rating, clinical value, expectations met",
        "Improvement Suggestions": "efficiency improvements, user interface enhancements, training resources",
        "Additional Comments": "open feedback, general remarks, anything else, free-form comments",
        "Competitor Comparison": "alternative solutions considered, competitor strengths, switching intent, market comparison",
        "Usage Frequency": "how often used, adoption rate, daily vs occasional use, engagement level",
        "Referral Likelihood": "word of mouth, peer recommendations, advocacy, likelihood to refer colleagues"
    },
    "Software": {
        "Product Quality": "bug frequency, performance, reliability, feature completeness, stability",
        "Support Experience": "technical support quality, documentation, response time, issue resolution",
        "Service Rating": "implementation support, onboarding, training, account management",
        "NPS Score": "recommendation likelihood, overall satisfaction, product-market fit",
        "Pricing Value": "pricing competitiveness, feature value, subscription model",
        "User Experience": "interface design, ease of use, workflow efficiency, mobile experience",
        "Satisfaction": "overall satisfaction rating, product value, expectations met",
        "Improvement Suggestions": "performance optimization, UI/UX enhancements, feature prioritization",
        "Additional Comments": "open feedback, general remarks, anything else, free-form comments",
        "Competitor Comparison": "alternative solutions considered, competitor strengths, switching intent, market comparison",
        "Usage Frequency": "how often used, adoption rate, daily vs occasional use, engagement level",
        "Referral Likelihood": "word of mouth, peer recommendations, advocacy, likelihood to refer colleagues"
    },
    "Financial Services": {
        "Product Quality": "accuracy, security, compliance, transaction reliability, data integrity",
        "Support Experience": "account support, dispute resolution, regulatory guidance, responsiveness",
        "Service Rating": "account management, advisory services, reporting quality, compliance support",
        "NPS Score": "recommendation likelihood, trust level, relationship satisfaction",
        "Pricing Value": "fee structure, cost transparency, value for services",
        "User Experience": "platform usability, statement clarity, mobile banking, self-service tools",
        "Satisfaction": "overall satisfaction rating, service quality, expectations met",
        "Improvement Suggestions": "process streamlining, transparency, communication, digital experience",
        "Additional Comments": "open feedback, general remarks, anything else, free-form comments",
        "Competitor Comparison": "alternative solutions considered, competitor strengths, switching intent, market comparison",
        "Usage Frequency": "how often used, adoption rate, daily vs occasional use, engagement level",
        "Referral Likelihood": "word of mouth, peer recommendations, advocacy, likelihood to refer colleagues"
    },
    "Professional Services": {
        "Product Quality": "deliverable quality, expertise, methodology, timeliness, results achieved",
        "Support Experience": "responsiveness, communication, flexibility, problem-solving",
        "Service Rating": "project management, team collaboration, knowledge transfer, follow-up",
        "NPS Score": "recommendation likelihood, overall satisfaction, partnership value",
        "Pricing Value": "pricing transparency, ROI, value delivered, cost-effectiveness",
        "User Experience": "engagement process, communication style, collaboration tools, reporting",
        "Satisfaction": "overall satisfaction rating, value delivered, expectations met",
        "Improvement Suggestions": "process improvements, communication enhancements, delivery optimization",
        "Additional Comments": "open feedback, general remarks, anything else, free-form comments",
        "Competitor Comparison": "alternative solutions considered, competitor strengths, switching intent, market comparison",
        "Usage Frequency": "how often used, adoption rate, daily vs occasional use, engagement level",
        "Referral Likelihood": "word of mouth, peer recommendations, advocacy, likelihood to refer colleagues"
    },
    "Retail": {
        "Product Quality": "product quality, inventory availability, freshness, selection, brand variety",
        "Support Experience": "customer service, returns process, issue resolution, store staff helpfulness",
        "Service Rating": "checkout speed, store cleanliness, product displays, stock availability",
        "NPS Score": "recommendation likelihood, shopping experience, loyalty",
        "Pricing Value": "price competitiveness, promotions, value for money, pricing transparency",
        "User Experience": "store layout, online ordering, mobile app, payment options, convenience",
        "Satisfaction": "overall satisfaction rating, shopping experience, expectations met",
        "Improvement Suggestions": "shopping experience, product selection, convenience, service quality",
        "Additional Comments": "open feedback, general remarks, anything else, free-form comments",
        "Competitor Comparison": "alternative solutions considered, competitor strengths, switching intent, market comparison",
        "Usage Frequency": "how often used, adoption rate, daily vs occasional use, engagement level",
        "Referral Likelihood": "word of mouth, peer recommendations, advocacy, likelihood to refer colleagues"
    },
    "Telecommunications": {
        "Product Quality": "network reliability, call quality, data speed, coverage, service uptime",
        "Support Experience": "technical support, billing support, issue resolution, wait times",
        "Service Rating": "installation, account management, service activation, network maintenance",
        "NPS Score": "recommendation likelihood, overall satisfaction, loyalty",
        "Pricing Value": "plan pricing, contract terms, hidden fees, value for features",
        "User Experience": "account portal, mobile app, self-service tools, billing clarity",
        "Satisfaction": "overall satisfaction rating, service quality, expectations met",
        "Improvement Suggestions": "network quality, billing transparency, support efficiency, pricing flexibility",
        "Additional Comments": "open feedback, general remarks, anything else, free-form comments",
        "Competitor Comparison": "alternative solutions considered, competitor strengths, switching intent, market comparison",
        "Usage Frequency": "how often used, adoption rate, daily vs occasional use, engagement level",
        "Referral Likelihood": "word of mouth, peer recommendations, advocacy, likelihood to refer colleagues"
    },
    "Education": {
        "Product Quality": "content quality, curriculum relevance, learning outcomes, resource availability",
        "Support Experience": "instructor support, technical assistance, administrative help, responsiveness",
        "Service Rating": "course delivery, platform reliability, assessment fairness, feedback quality",
        "NPS Score": "recommendation to others, overall satisfaction, value received",
        "Pricing Value": "tuition value, financial aid, cost transparency, ROI on education",
        "User Experience": "platform usability, course navigation, mobile access, learning tools",
        "Satisfaction": "overall satisfaction rating, learning value, expectations met",
        "Improvement Suggestions": "teaching methods, platform improvements, support enhancements, course content",
        "Additional Comments": "open feedback, general remarks, anything else, free-form comments",
        "Competitor Comparison": "alternative solutions considered, competitor strengths, switching intent, market comparison",
        "Usage Frequency": "how often used, adoption rate, daily vs occasional use, engagement level",
        "Referral Likelihood": "word of mouth, peer recommendations, advocacy, likelihood to refer colleagues"
    },
    "Hospitality": {
        "Product Quality": "cleanliness, amenities, room quality, facility maintenance, comfort",
        "Support Experience": "staff friendliness, concierge service, issue resolution, responsiveness",
        "Service Rating": "check-in/out process, housekeeping, dining quality, facility services",
        "NPS Score": "recommendation likelihood, overall experience, return intent",
        "Pricing Value": "rate fairness, value for money, pricing transparency, package deals",
        "User Experience": "booking process, amenity access, mobile app, loyalty program",
        "Satisfaction": "overall satisfaction rating, stay experience, expectations met",
        "Improvement Suggestions": "service quality, facility updates, staff training, convenience features",
        "Additional Comments": "open feedback, general remarks, anything else, free-form comments",
        "Competitor Comparison": "alternative solutions considered, competitor strengths, switching intent, market comparison",
        "Usage Frequency": "how often used, adoption rate, daily vs occasional use, engagement level",
        "Referral Likelihood": "word of mouth, peer recommendations, advocacy, likelihood to refer colleagues"
    },
    "Generic": {
        "Product Quality": "quality, reliability, performance, features, value delivered",
        "Support Experience": "customer service, responsiveness, problem resolution, support quality",
        "Service Rating": "overall service, delivery, implementation, follow-up",
        "NPS Score": "recommendation likelihood, overall satisfaction, loyalty",
        "Pricing Value": "pricing fairness, value for money, cost transparency",
        "User Experience": "ease of use, convenience, accessibility, overall experience",
        "Satisfaction": "overall satisfaction rating, experience quality, expectations met",
        "Improvement Suggestions": "general improvements, quality enhancements, service optimization",
        "Additional Comments": "open feedback, general remarks, anything else, free-form comments",
        "Competitor Comparison": "alternative solutions considered, competitor strengths, switching intent, market comparison",
        "Usage Frequency": "how often used, adoption rate, daily vs occasional use, engagement level",
        "Referral Likelihood": "word of mouth, peer recommendations, advocacy, likelihood to refer colleagues"
    },
    "Events and Tradeshows": {
        "Product Quality": "registration systems, badging reliability, mobile app performance, lead capture accuracy, floorplan tools",
        "Support Experience": "onsite assistance, responsiveness, issue resolution, AV and booth support",
        "Service Rating": "event execution, logistics coordination, exhibitor services, setup/teardown management",
        "NPS Score": "likelihood to recommend the event, exhibitor success, attendee experience",
        "Pricing Value": "ROI for exhibitors, value for participation, traffic generated vs cost",
        "User Experience": "ease of registration, app usability, navigation, session booking, signage clarity",
        "Satisfaction": "overall event satisfaction, exhibitor and attendee experience, expectations met",
        "Improvement Suggestions": "better communication, smoother logistics, app enhancements, clearer guidelines",
        "Additional Comments": "open feedback, general remarks, anything else, free-form comments",
        "Competitor Comparison": "alternative solutions considered, competitor strengths, switching intent, market comparison",
        "Usage Frequency": "how often used, adoption rate, daily vs occasional use, engagement level",
        "Referral Likelihood": "word of mouth, peer recommendations, advocacy, likelihood to refer colleagues"
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
