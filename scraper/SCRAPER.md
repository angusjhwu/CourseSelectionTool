# Scraper for UofT ECE Undergrad Courses

Website: https://engineering.calendar.utoronto.ca/section/Electrical-and-Computer-Engineering

## Goal
- Scrape the website, gather all courses and their course information from each course page
- Build a database of these courses, such that it can be fed into later programs

## Plan
1. Build a web scraper that gathers all course names (strings ending in H1). For each course, find the following fields:
    - Get the URL
    - Collect all course information as strings
    - Note down which semester they are offered (fall or winter), this can be found by looking at the table section
    - Gather which group each course belongs to (A, B, C, Math, etc)
2. Create one file called ./data/course_db with the most appropriate file format and extension.

## Environment Specifications
- MacOS
- Python3.13 and C/C++ available
