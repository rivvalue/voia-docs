/**
 * Color Override Utility
 * 
 * Handles forced color overrides for Bootstrap warning classes (yellow/orange)
 * to match VOÏA brand colors (red/gray). This utility eliminates duplicate
 * color override logic across multiple files.
 * 
 * Phase 1 Frontend Refactoring - Extracted from dashboard.js
 */

/**
 * Force override Bootstrap warning colors (yellow) with VOÏA brand colors
 * 
 * @param {HTMLElement|null} container - Optional container to limit scope. If null, applies to entire document.
 * @param {number} delay - Optional delay in milliseconds before applying overrides (default: 0)
 */
function applyColorOverrides(container = null, delay = 0) {
    const applyOverrides = () => {
        const scope = container || document;
        
        // Target ALL possible warning elements
        const yellowSelectors = [
            '.text-warning', '.bg-warning', '.border-warning', '.badge.bg-warning',
            '.btn-warning', '.btn-outline-warning', '.alert-warning',
            '.fa-exclamation-triangle', '.fas.fa-exclamation-triangle',
            '[class*="warning"]'
        ];
        
        yellowSelectors.forEach(selector => {
            const elements = scope.querySelectorAll(selector);
            elements.forEach(el => {
                // Force inline styles that override everything
                if (el.classList.contains('fa-exclamation-triangle') || el.classList.contains('fas')) {
                    el.style.setProperty('color', '#E13A44', 'important');
                } else if (el.classList.contains('bg-warning') || el.classList.contains('badge')) {
                    el.style.setProperty('background-color', '#BDBDBD', 'important');
                    el.style.setProperty('color', '#000000', 'important');
                    el.style.setProperty('border-color', '#BDBDBD', 'important');
                } else if (el.classList.contains('text-warning')) {
                    el.style.setProperty('color', '#E13A44', 'important');
                } else if (el.classList.contains('border-warning')) {
                    el.style.setProperty('border-color', '#BDBDBD', 'important');
                } else {
                    // Generic warning class
                    el.style.setProperty('color', '#E13A44', 'important');
                    el.style.setProperty('background-color', '#BDBDBD', 'important');
                    el.style.setProperty('border-color', '#BDBDBD', 'important');
                }
            });
        });
        
        // Also check for any hardcoded yellow colors (RGB values)
        const allElements = scope.querySelectorAll('*');
        allElements.forEach(el => {
            const computedStyle = window.getComputedStyle(el);
            const color = computedStyle.color;
            const backgroundColor = computedStyle.backgroundColor;
            const borderColor = computedStyle.borderColor;
            
            // If any yellow colors are detected, force change them
            if (color.includes('rgb(255, 193, 7)') || color.includes('#ffc107') || color.includes('#FFC107')) {
                el.style.color = '#E13A44';
            }
            if (backgroundColor.includes('rgb(255, 193, 7)') || backgroundColor.includes('#ffc107') || backgroundColor.includes('#FFC107')) {
                el.style.backgroundColor = '#BDBDBD';
            }
            if (borderColor.includes('rgb(255, 193, 7)') || borderColor.includes('#ffc107') || borderColor.includes('#FFC107')) {
                el.style.borderColor = '#BDBDBD';
            }
        });
    };
    
    if (delay > 0) {
        setTimeout(applyOverrides, delay);
    } else {
        applyOverrides();
    }
}

/**
 * Legacy function name for backward compatibility
 * @deprecated Use applyColorOverrides instead
 */
function forceRemoveYellowColors() {
    applyColorOverrides(document, 0);
}
