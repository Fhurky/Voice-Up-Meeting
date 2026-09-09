# Product documentation

Put public, product-specific end-user documentation here. Engineering rules remain in `rules/`;
accepted requirements, delivery plans and tasks remain under `specs/<domain>/PRDs/`. Do not copy
those sources into a second contract.

Recommended structure:

- `README.md`: audience, product purpose and navigation;
- `getting-started.md`: first sign-in and the smallest useful user journey;
- `capabilities/`: behavior organized by accepted business capability;
- `operations/`: user-visible support and recovery procedures;
- `release-notes/`: changes users can observe.

Every behavioral claim links to its accepted PRD and uses language suitable for the product's
users. Internal secrets, infrastructure addresses, agent transcripts and unaccepted roadmap items
do not belong here. Keep this English tree aligned with `../tr/` where the product publishes both
locales.

Repository workflow: [specifications](../../specs/README.md). Platform first run:
[root README](../../README.md).
