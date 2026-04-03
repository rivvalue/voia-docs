# SEO Action Plan — rivvalue.com
**Prepared for:** Rivvalue Marketing Team
**Date:** April 3, 2026
**Based on:** Full technical and content SEO audit of www.rivvalue.com

---

## Executive Summary

A full SEO audit of rivvalue.com has identified a set of critical issues, quick wins, and longer-term opportunities that are currently preventing the site from ranking in Google search results for its target keywords ("SaaS strategy consultancy," "NPS optimization," "vendor selection B2B," etc.).

The most urgent problem is **sitemap pollution**: over 50 pages are submitted to Google's sitemap, but only 1 is currently indexed. The root causes are a mix of placeholder content, internal design pages, and thin tag/category pages that signal low content quality to Google. These issues, combined with a missing homepage heading and incorrect article dates (showing 2019 instead of current dates), are actively suppressing the site's search visibility.

The good news: most of these issues are fixable within one to two weeks and will have an immediate positive effect. This document outlines every action item, who should own it, how quickly it should be done, and what impact to expect.

---

## Critical Issues — Fix Within 1 Week

These issues are directly harming search indexation and must be resolved first.

---

### 1. Add an H1 Heading to the Homepage

**What it is:** The homepage currently has no H1 tag — the most important on-page signal Google uses to understand what a page is about. Only an H2 and H4 are present.

**What to do:** Add a clear, keyword-rich H1 heading near the top of the homepage. A suggested example: *"SaaS Strategy Consultancy for B2B Companies"* — or whatever best reflects Rivvalue's core positioning in plain language.

**Owner:** Marketing / Web Editor
**Expected impact:** High. Google uses the H1 to understand the page topic. Without it, the homepage is essentially untagged for search.

---

### 2. Remove or Replace the 4 Placeholder Blog Pages

**What it is:** Four blog posts titled "Blog Post Title One," "Blog Post Title Two," "Blog Post Title Three," and "Blog Post Title Four" are currently live, indexed, and listed in the sitemap. Each has the description "It all begins with an idea." These are Squarespace starter placeholders that were never replaced.

**What to do:** Delete all four placeholder pages immediately, or replace them with real published content. Also remove them from the sitemap.

**Owner:** Marketing / Content Team
**Expected impact:** High. Placeholder pages signal to Google that the site has low-quality content. Removing them will improve the overall quality signal of the entire site.

---

### 3. Remove the /site-styles Page from the Sitemap and Block from Indexing

**What it is:** A page at /site-styles — an internal Squarespace design configuration page — is currently indexed by Google and included in the sitemap. This page has no value for visitors or search engines.

**What to do:** Add a "noindex" instruction to /site-styles and remove it from the sitemap.

**Owner:** Web Editor / Squarespace Admin
**Expected impact:** Medium. Removes a low-quality page from Google's index, which improves the overall content quality signal for the site.

---

### 4. Remove Tag and Category Pages from the Sitemap

**What it is:** 10 tag pages and 2 category pages generated automatically by Squarespace's blogging system are currently listed in the sitemap as indexable pages. These pages contain very little unique content (they are just lists of articles filtered by tag), and Google treats them as thin or duplicate content.

**What to do:** Configure Squarespace to exclude these tag and category archive pages from the sitemap and set them to noindex.

**Owner:** Web Editor / Squarespace Admin
**Expected impact:** Medium-High. Reduces sitemap pollution and concentrates Google's attention on the pages that actually matter.

---

### 5. Fix Article Publication Dates

**What it is:** All insight articles on the site show a publication date of March 11, 2019 — a Squarespace platform default date that was never updated. This makes every article appear to be over 7 years old, which reduces their credibility and ranking potential for time-sensitive topics.

**What to do:** Update the datePublished field in each article's settings to reflect the actual date the article was published or last meaningfully updated.

**Owner:** Content Team
**Expected impact:** High. Correct dates are a trust signal for both Google and readers, especially for B2B insight content where recency matters.

---

### 6. Allow Beneficial AI Bots in robots.txt

**What it is:** The robots.txt file on rivvalue.com is currently blocking all AI bots — including Google-Extended, GPTBot (OpenAI), and ClaudeBot. This prevents Rivvalue's content from appearing in AI-generated search summaries (Google AI Overviews) and from being surfaced by AI assistants like ChatGPT.

**What to do:** Selectively re-allow the bots that drive search visibility while keeping data-harvesting scrapers blocked. See the AI & Future-Proofing section below for the specific bot list.

**Owner:** Web Editor / Squarespace Admin (requires robots.txt access)
**Expected impact:** High over time. AI Overviews are an increasingly important traffic source, and blocking Google-Extended means Rivvalue cannot appear in them.

---

## High-Impact Improvements — Fix Within 2 Weeks

These issues are not as urgent as the critical items above, but they are meaningfully reducing the site's effectiveness and should be addressed in the second week.

---

### 7. Add hreflang Tags Between English and French Page Pairs

**What it is:** The site has both English and French versions of several pages, but there are no hreflang tags telling Google which page is for which language/region. Without these tags, Google may show English visitors the French page (and vice versa), or may treat the two versions as duplicate content.

**What to do:** Add hreflang link tags connecting each English page to its French equivalent. For example: /voice-of-client should link to /exprience-client (or its corrected URL), and vice versa.

**Owner:** Web Editor / Developer
**Expected impact:** High for bilingual SEO. This is a prerequisite to unlocking the French-language Quebec B2B market.

---

### 8. Fix the French URL Typo (/exprience-client)

**What it is:** The French version of the Voice of Client page has a URL with a typo: /exprience-client instead of /experience-client. This typo appears in the sitemap and in any internal links.

**What to do:** Rename the page URL to /experience-client and set up a redirect from the old URL.

**Owner:** Web Editor
**Expected impact:** Low-Medium on its own, but important for the professionalism of the French-language experience and for correctly implementing hreflang.

---

### 9. Add a Meta Description to the French Homepage (/francais-home)

**What it is:** The French-language homepage has a completely blank meta description. The meta description is the short paragraph that appears under the page title in Google search results — it is a key driver of click-through rate.

**What to do:** Write a compelling, 150–160 character meta description in French for the homepage. It should describe who Rivvalue helps and what they do, with a soft call to action.

**Owner:** Marketing / Content Team
**Expected impact:** Medium. Will not affect ranking directly, but will significantly improve click-through rate once the French homepage appears in search results.

---

### 10. Update the Article Author Name to Amine Ati

**What it is:** All insight articles on the site list the author in the page's structured data as "Glass Ink" (a design agency) instead of Amine Ati (the actual expert author). Google uses author information as part of its E-E-A-T evaluation — Expertise, Experience, Authoritativeness, and Trustworthiness. A named expert author carries more credibility than an agency name.

**What to do:** Update the author field on all insight articles to display "Amine Ati" and reflect this in the article schema markup.

**Owner:** Content Team / Web Editor
**Expected impact:** Medium-High. Correct author attribution strengthens Rivvalue's content credibility signals over time, especially important for B2B thought leadership content.

---

### 11. Fix the Homepage OG Image Dimensions

**What it is:** The Open Graph (OG) image — the image that appears when the homepage is shared on LinkedIn, Twitter/X, Slack, etc. — is currently 1500×300 pixels. The correct ratio for social sharing previews is 1200×630 pixels. The current image will display incorrectly or be cropped on most social platforms.

**What to do:** Replace the homepage OG image with one sized at 1200×630 pixels (or any image with a roughly 1.91:1 ratio).

**Owner:** Design / Marketing
**Expected impact:** Medium. Every time a team member or client shares the Rivvalue homepage, it will now display a properly formatted preview image instead of a distorted crop.

---

### 12. Fix Blog OG Image URLs (HTTP → HTTPS)

**What it is:** The Open Graph image URLs on blog/insight pages use HTTP instead of HTTPS. This is a mixed content issue — the page loads securely over HTTPS, but the referenced image is served over an unencrypted connection. Some browsers and platforms will block or flag these images.

**What to do:** Update all blog OG image URLs to use HTTPS.

**Owner:** Web Editor
**Expected impact:** Low-Medium. Prevents image display failures on platforms that enforce secure content policies.

---

### 13. Fix the Malformed Business Hours in LocalBusiness Schema

**What it is:** The LocalBusiness structured data on the site contains a malformed openingHours field that reads: `", , , , , , "` — essentially empty placeholders. This is invalid structured data that Google may flag as an error in Search Console.

**What to do:** Either remove the openingHours field entirely (if Rivvalue does not operate on a fixed schedule), or fill it in with correct values in the standard format (e.g., "Mo-Fr 09:00-17:00").

**Owner:** Web Editor / Developer
**Expected impact:** Low-Medium. Fixes a structured data error and removes a potential negative signal in Google Search Console.

---

### 14. Standardize Page Title Separators

**What it is:** Some page titles use a pipe character ( | ) as a separator between the page title and the brand name, while others use an em dash ( — ) or a hyphen ( - ). This inconsistency looks unprofessional in search results.

**What to do:** Pick one separator style (the pipe | is most conventional for SEO) and apply it consistently across all page titles.

**Owner:** Web Editor / Marketing
**Expected impact:** Low on rankings, but improves brand presentation in search results.

---

## Quick Wins — Items That Can Be Done Immediately

These are small, fast actions that combine to produce meaningful improvements with minimal effort.

| Action | Owner | Effort |
|---|---|---|
| Add keyword-rich H1 to homepage (e.g., "SaaS Strategy Consultancy") | Marketing | 15 min |
| Delete the 4 placeholder blog posts | Content Team | 10 min |
| Set /site-styles to noindex and remove from sitemap | Web Admin | 10 min |
| Exclude tag/category pages from sitemap | Web Admin | 15 min |
| Update article publication dates to accurate dates | Content Team | 30 min |
| Allow Google-Extended bot in robots.txt | Web Admin | 15 min |
| Fix the /exprience-client URL typo to /experience-client | Web Admin | 10 min |
| Update author field on all articles to Amine Ati | Content Team | 20 min |

---

## AI & Future-Proofing — Do Within 1 Month

As AI-powered search becomes a primary discovery channel for B2B buyers, these steps will ensure Rivvalue's content appears in AI Overviews and AI assistant responses.

---

### 15. Selectively Allow AI Search Bots in robots.txt

**What it is:** Currently all AI bots are blocked. The recommended approach is to allow the bots that drive search appearances, while continuing to block scrapers that harvest content for model training without providing traffic in return.

**What to do:**

**Allow these bots (they drive search visibility):**
- Google-Extended (powers Google AI Overviews)
- OAI-SearchBot (powers ChatGPT search)
- PerplexityBot

**Keep blocked (these harvest training data without returning traffic):**
- CCBot
- Bytespider
- img2dataset
- GPTBot (OpenAI's training crawler — distinct from OAI-SearchBot)
- ClaudeBot (Anthropic's training crawler)

**Owner:** Web Admin
**Expected impact:** High over 3–6 months. AI Overviews are appearing at the top of Google results for many B2B queries and can drive significant qualified traffic.

---

### 16. Add FAQ Schema to Insight Articles

**What it is:** Several of Rivvalue's insight articles are structured in a Q&A format (e.g., "What is an SLA?" / "How do you measure NPS?"). Adding FAQPage structured data markup to these articles makes them eligible to appear in Google's AI Overview answers and featured snippets.

**What to do:** Work with the web developer to add FAQPage schema markup to any insight article that contains a question-and-answer structure.

**Owner:** Developer / Content Team
**Expected impact:** High. FAQ schema is one of the strongest signals for AI Overview citations.

---

### 17. Ensure All Articles Have Correct Article Schema

**What it is:** Each insight article should have Article structured data that includes the correct datePublished, dateModified, and author fields. Currently these are either missing or incorrect (wrong date, wrong author name).

**What to do:** After correcting the publication dates (action item #5) and author name (action item #10), verify that the Article schema on each page reflects those correct values.

**Owner:** Developer / Content Team
**Expected impact:** Medium-High. Correct Article schema strengthens the content's credibility signals for both Google and AI systems.

---

## Long-Term Content Strategy — Ongoing

These are not one-time fixes but ongoing strategic priorities that will build Rivvalue's organic search presence over the next 6–12 months.

---

### 18. Build Topical Authority Through Deeper Content

**What it is:** Rivvalue does not currently appear in Google for its own target keywords — "SaaS strategy consultancy," "NPS optimization," "vendor selection B2B." Competitors such as Sortlist, Go Nimbly, and various RevOps agencies dominate these search results.

**What to do:** Develop a structured content calendar focused on Rivvalue's core topic areas: NPS and customer feedback, Total Cost of Ownership (TCO), SLAs for software products, and B2B vendor selection. Each topic should have a foundational "pillar" article (1,500–2,500 words) supported by shorter related posts. The existing insight articles are a strong start — they need to be expanded and augmented.

**Owner:** Marketing / Content Team
**Expected impact:** High over 6–12 months. Consistent, well-structured publishing on a focused set of topics is the primary driver of long-term organic traffic for B2B consulting sites.

---

### 19. Fully Activate the Bilingual French Strategy

**What it is:** The French-language pages are a significant competitive differentiator in the Canadian B2B market, particularly for the Quebec market. However, the French pages are currently not benefiting from SEO because hreflang is missing, a URL has a typo, and the French homepage has no meta description.

**What to do:** After completing actions #7, #8, and #9 (hreflang, URL fix, French meta description), continue expanding French-language content and ensure that all new insight articles have French equivalents where relevant.

**Owner:** Marketing / Content Team
**Expected impact:** High over 3–6 months. A properly configured bilingual site targeting Quebec B2B decision-makers is rare and provides a meaningful competitive advantage.

---

## Appendix: Page-by-Page Notes

### Homepage (/)
- **Title:** Only 31 characters long and does not include a primary keyword. Suggested: "Rivvalue | SaaS Strategy Consultancy for B2B Companies"
- **H1:** Missing entirely — only an H2 and H4 are present. Add an H1 immediately.
- **Meta description:** At 276 characters, it is too long and will be truncated by Google at around 160 characters. Shorten to 150–160 characters.
- **OG image:** Incorrect dimensions (1500×300px). Replace with 1200×630px.

---

### /voice-of-client
- **Title:** Uses a double separator (both | and —). Standardize to one format.
- **Meta description:** Good length and content, but "NPS" is not spelled out on first use. Consider spelling it out ("Net Promoter Score (NPS)") for clarity.

---

### /service-levels
- **Meta description:** Good.
- **Title:** Separator inconsistency — standardize with the rest of the site.

---

### /insights/rethinking-slas-for-ai-based-software
- **Status:** Currently the only article indexed by Google — this is Rivvalue's best-performing content.
- **H1:** Good.
- **Title:** At 82 characters, it is slightly long. Consider trimming to under 60 characters.
- **datePublished:** Shows 2019 — must be corrected to the actual publication date.
- **Author:** Shows "Glass Ink" — must be updated to "Amine Ati."

---

### /structured-insights/blog-post-title-one through blog-post-title-four
- **Status:** All 4 pages must be deleted or replaced with real content immediately.
- **Content:** Placeholder text only ("It all begins with an idea.") — no value for visitors or search engines.
- **Action:** Delete pages and remove from sitemap.

---

### /voia
- **H1:** Currently just "VOÏA" (the brand name alone, with no descriptive keyword context for Google). Suggested H1: "AI-Powered Voice of Client Platform."
- **Title:** Contains a double space ("VOÏA -  AI-powered") and uses a hyphen ( - ) instead of a pipe ( | ), inconsistent with the rest of the site. Suggested title: "VOÏA | AI-Powered Voice of Client Platform for B2B | Rivvalue."
- **Meta description:** Currently reads only as the page title restated ("VOÏA – AI-Powered Voice of Client Platform by Rivvalue") with no value proposition or call to action. Write a 150-character description explaining what VOÏA does, who it is for, and ending with a call to action.
- **Twitter card:** Set to `summary` instead of `summary_large_image`. Update to `summary_large_image` to display a full-width preview image when shared on Twitter/X.
- **hreflang:** No link between /voia and /fr/voia despite both pages existing. Add hreflang tags connecting the two.

---

*End of SEO Action Plan. Questions or clarifications: contact the team that prepared this audit.*
