# The Government Data portal pages

The Government Data portal (the GDS SharePoint site) carries two pages that mirror this repository:

- **DAM Policy Explorer** (`DAM-Policy-Explorer.aspx`): what the explorer is, links into it, and the Power App embedded with a Power Apps web part.
- **DAM capability playbooks** (`DAM-capability-playbooks.aspx`): every main page, sector supplement and learning module of the playbooks, each with one line and a link.

## Why mirror rather than move

The portal is a site in one department's Microsoft 365 tenant. People in other departments and arm's length bodies mostly cannot open it, so it cannot be the cross-government home of anything. It is GDS's own front door. The authority stays where it is: the policy and its guidance on GOV.UK. The explorer and the playbooks stay public so everyone can use them, and the portal pages link to them rather than holding a second copy.

A durable organisational home for the public sites themselves is a separate decision: moving both repositories from a personal GitHub account to a government GitHub organisation, after clearance (playbooks backlog BL-22).

## How the pages are kept in step

1. The build writes the two page bodies to `out/portal/` from `tools/content.py` and the pinned playbooks snapshot (`tools/portal_pages.py`), so they are published with the site.
2. `s22_portal_pages` checks them: only headings, paragraphs, lists, links and emphasis; https or portal links; no addresses; the versions they were made from.
3. After a release, a site owner opens any portal page, pastes `tools/portal_refresh.js` into the browser console and runs it. It fetches both bodies, checks them again, puts each in its page's text web part, saves and publishes. It changes nothing else on the page, so the Power Apps web part stays.

There is no automatic sync: a scheduled flow would need either a premium Power Automate connector or stored credentials, and this estate uses neither.

## Effort

About 5 minutes after each explorer release or playbooks snapshot refresh.
