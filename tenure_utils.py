def map_tenure_years_to_category(tenure_years):
    """
    Convert numeric tenure_years (float) to categorical tenure string.

    Args:
        tenure_years: Float representing years (e.g., 2.5)

    Returns:
        str: Categorical tenure range (e.g., "2-3 years")
    """
    if tenure_years is None:
        return "Less than 6 months"
    if tenure_years < 0.5:
        return "Less than 6 months"
    elif tenure_years < 1:
        return "6 months - 1 year"
    elif tenure_years < 2:
        return "1-2 years"
    elif tenure_years < 3:
        return "2-3 years"
    elif tenure_years < 5:
        return "3-5 years"
    elif tenure_years < 10:
        return "5-10 years"
    else:
        return "More than 10 years"
