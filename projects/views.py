"""
EcoIQ Projects — no views.

The public /projects/ and /projects/<slug>/ pages are React
(frontend/web/src/pages/Projects.tsx and ProjectConcept.tsx), served through
core.spa. The five programme concepts they render come from projects/data.py,
which is still the single source of truth for them and is read by
api/v2_projects.py.

The module is kept rather than deleted so projects/ stays an installed app with
its data module intact; `projects.data` is imported by the API and by
core.spa.project_concept_spa_view.
"""
