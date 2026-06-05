<!--
ATS-friendly markdown resume template.
- No tables, no columns, no images, no fancy unicode — markdown parses cleanly into ATS pipelines.
- Convert to PDF via: pandoc resume.md -o resume.pdf --pdf-engine=xelatex -V geometry:margin=0.6in
- Or to DOCX via: pandoc resume.md -o resume.docx --reference-doc=reference.docx
- Placeholders use {{double-braces}}. The tailoring skill replaces all of them.
- DO NOT introduce new placeholders without updating the skill.
-->

# {{NAME}}

{{LOCATION}} · {{PHONE}} · {{EMAIL}}
{{LINKS_LINE}}

---

## {{HEADLINE}}

{{PROFESSIONAL_SUMMARY}}

---

## Core Competencies

{{CORE_COMPETENCIES_BULLETS}}

---

## Professional Experience

### {{ROLE_1_TITLE}} — {{ROLE_1_COMPANY}}
*{{ROLE_1_LOCATION}} · {{ROLE_1_DATES}}*

{{ROLE_1_BULLETS}}

### {{ROLE_2_TITLE}} — {{ROLE_2_COMPANY}}
*{{ROLE_2_LOCATION}} · {{ROLE_2_DATES}}*

{{ROLE_2_BULLETS}}

### {{ROLE_3_TITLE}} — {{ROLE_3_COMPANY}}
*{{ROLE_3_LOCATION}} · {{ROLE_3_DATES}}*

{{ROLE_3_BULLETS}}

### {{ROLE_4_TITLE}} — {{ROLE_4_COMPANY}}
*{{ROLE_4_LOCATION}} · {{ROLE_4_DATES}}*

{{ROLE_4_BULLETS}}

---

## Education

{{EDUCATION_BLOCK}}

---

## Recognition

{{RECOGNITION_BLOCK}}

<!--
Optional sections — include ONLY if the skill determines they're relevant to the JD:

## Selected Frameworks
{{FRAMEWORKS_BLOCK}}

## Technical Stack
{{TECH_STACK_BLOCK}}
-->
