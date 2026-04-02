"""
Shared utilities for classic survey configuration.
Normalization helpers used by both public survey render and campaign management.
"""

import copy
import re

PLATFORM_DEFAULT_FEATURES = [
    {'key': 'feature_a', 'name_en': 'Feature A', 'name_fr': 'Fonctionnalité A'},
    {'key': 'feature_b', 'name_en': 'Feature B', 'name_fr': 'Fonctionnalité B'},
    {'key': 'feature_c', 'name_en': 'Feature C', 'name_fr': 'Fonctionnalité C'},
    {'key': 'feature_d', 'name_en': 'Feature D', 'name_fr': 'Fonctionnalité D'},
    {'key': 'feature_e', 'name_en': 'Feature E', 'name_fr': 'Fonctionnalité E'},
]

PLATFORM_DEFAULT_DRIVERS = [
    {'key': 'product_features', 'label_en': 'Product features & functionality', 'label_fr': 'Fonctionnalités du produit'},
    {'key': 'value_pricing', 'label_en': 'Product value/pricing', 'label_fr': 'Rapport qualité/prix'},
    {'key': 'professional_services', 'label_en': 'Professional services & support team', 'label_fr': 'Services professionnels et équipe de support'},
    {'key': 'customer_support', 'label_en': 'Customer support & after-sales service', 'label_fr': 'Support client et service après-vente'},
    {'key': 'communication', 'label_en': 'Communication & transparency', 'label_fr': 'Communication et transparence'},
    {'key': 'onboarding', 'label_en': 'Onboarding & implementation experience', 'label_fr': "Expérience d'intégration et de mise en œuvre"},
    {'key': 'ease_of_use', 'label_en': 'Ease of use', 'label_fr': "Facilité d'utilisation"},
    {'key': 'reliability', 'label_en': 'Reliability & performance', 'label_fr': 'Fiabilité et performance'},
    {'key': 'integration', 'label_en': 'Integration capabilities', 'label_fr': "Capacités d'intégration"},
]


def normalize_driver_labels(raw):
    """
    Normalize driver_labels JSON to [{key, label_en, label_fr}] format.
    Handles multiple legacy formats:
      - List of dicts: [{key, label_en, label_fr}, ...]  (current/canonical)
      - NPS category-map: {detractor: {key: label, ...}, promoter: {...}, passive: {...}}
        (older format where driver display text was category-specific)
      - Flat dict of {key: label_string}
    Returns platform defaults on unrecognised or empty input.
    """
    if not raw:
        return copy.deepcopy(PLATFORM_DEFAULT_DRIVERS)

    if isinstance(raw, list):
        normalized = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            key = str(item.get('key') or item.get('id') or '').strip()
            label_en = str(item.get('label_en') or item.get('name_en') or item.get('label') or '').strip()
            label_fr = str(item.get('label_fr') or item.get('name_fr') or label_en).strip()
            if not key or not label_en:
                continue
            normalized.append({'key': key, 'label_en': label_en, 'label_fr': label_fr})
        return normalized if normalized else copy.deepcopy(PLATFORM_DEFAULT_DRIVERS)

    if isinstance(raw, dict):
        NPS_CATEGORIES = {'detractor', 'promoter', 'passive', 'detractors', 'promoters', 'passives'}
        top_keys = set(str(k).lower() for k in raw.keys())
        if top_keys & NPS_CATEGORIES:
            combined = {}
            for cat_key, cat_drivers in raw.items():
                if not isinstance(cat_drivers, dict):
                    continue
                for driver_key, label in cat_drivers.items():
                    if driver_key not in combined:
                        label_str = str(label).strip() if label else driver_key.replace('_', ' ').title()
                        combined[driver_key] = {
                            'key': driver_key,
                            'label_en': label_str,
                            'label_fr': label_str,
                        }
            result = list(combined.values())
            return result if result else copy.deepcopy(PLATFORM_DEFAULT_DRIVERS)
        else:
            result = []
            for k, v in raw.items():
                key = str(k).strip()
                label_en = str(v).strip() if v else key.replace('_', ' ').title()
                result.append({'key': key, 'label_en': label_en, 'label_fr': label_en})
            return result if result else copy.deepcopy(PLATFORM_DEFAULT_DRIVERS)

    return copy.deepcopy(PLATFORM_DEFAULT_DRIVERS)


def normalize_features(raw):
    """
    Normalize features JSON to [{key, name_en, name_fr}] format.
    Returns platform defaults on unrecognised or empty input.
    """
    if not raw or not isinstance(raw, list):
        return copy.deepcopy(PLATFORM_DEFAULT_FEATURES)
    normalized = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = str(item.get('key') or item.get('id') or '').strip()
        name_en = str(item.get('name_en') or item.get('label_en') or item.get('name') or '').strip()
        name_fr = str(item.get('name_fr') or item.get('label_fr') or name_en).strip()
        if not key or not name_en:
            continue
        normalized.append({'key': key, 'name_en': name_en, 'name_fr': name_fr})
    return normalized if normalized else copy.deepcopy(PLATFORM_DEFAULT_FEATURES)


def slugify_key(text, max_length=40):
    """Generate a stable slug key from a label string."""
    slug = text.lower().strip()
    slug = re.sub(r'[\s\-]+', '_', slug)
    slug = re.sub(r'[^a-z0-9_]', '', slug)
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug[:max_length] or 'item'


def unique_key(base, existing_keys, suffix_start=2):
    """Return base key or base_N if base already exists in existing_keys set."""
    if base not in existing_keys:
        return base
    n = suffix_start
    while f'{base}_{n}' in existing_keys:
        n += 1
    return f'{base}_{n}'
