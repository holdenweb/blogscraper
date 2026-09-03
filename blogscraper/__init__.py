"""Blogger-to-MongoDB migration pipeline for holdenweb.com.

raw_posts / raw_comments hold feed entries verbatim (ADR-0004); posts /
comments are typed documents rebuilt from raw by the table-driven
transform (ADR-0005). See docs/adr/ for the reasoning.
"""
