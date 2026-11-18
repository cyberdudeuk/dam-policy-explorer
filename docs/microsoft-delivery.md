# Delivering the DAM Policy Explorer on the Microsoft stack

**Now (18 Nov 2026):** hosted on GitHub Pages (GitHub is part of Microsoft, and the GDS Way default) at https://cyberdudeuk.github.io/dam-policy-explorer/, published only when every check passes, and delivered through the Microsoft 365 app package (Teams, Outlook, Microsoft 365 app, Copilot agent). **Next:** move hosting to Azure Static Web Apps once DSIT provides a subscription (the DSIT directory has none today); nothing else changes.

## Target architecture

| Layer | Microsoft service | What it does | Status |
|---|---|---|---|
| Front door | Microsoft 365 app (one package) | Personal app in Teams (desktop, web, mobile), Outlook and the Microsoft 365 app | Package ready: `tools/package_teams.py` |
| AI | Microsoft 365 Copilot declarative agent, "DAM Policy assistant" | Conversational answers grounded on GOV.UK, the explorer and the GDS FAQs, with citations | In the same package |
| Hosting | Azure Static Web Apps | Serves the explorer over HTTPS with the headers in `staticwebapp.config.json` | Needs a subscription and resource |
| Content source | SharePoint Online lists and library | FAQ, question register, return log as the single source; the explorer rebuilt from them | Next: Graph export into `tools/content.py` |
| Workflow | Power Automate | Returns into the shared mailbox, saved to the DAM Policy Library, appended to the master workbook | Existing operating model |
| Insight | Power BI or the analytics dashboard | Return status and needs heat map | Roadmap |
| Contact | Microsoft Forms (proposed) | Replace the GitHub issue form for people without GitHub | Decision needed |
| Channels | Teams channel "Website" tab, SharePoint Embed web part | Pin the explorer for a team or on an intranet page | Works once hosted |

## Steps to go live
1. Create an Azure Static Web App (free plan is enough). Deploy the contents of `out/` (for example `swa deploy ./out --env production`). The config file sets the security headers, including which Microsoft hosts may embed it.
2. Run `python3 -I tools/package_teams.py https://<your-static-web-app-host>`. It refuses a non-https host and checks the manifest limits.
3. In Teams Developer Portal, open the existing app **DAM Policy Explorer** (ID 62391348-f59f-420b-a834-0e2bcc33d2fc), choose **Import app** and upload the zip. The app ID is reused so it updates the registration you already have.
4. Validate in **App validation**, then **Preview in Teams**. Test in Teams desktop, web and mobile, Outlook and the Microsoft 365 app, in light, dark and high contrast.
5. Ask your Teams administrator to publish it to the organisation (Publish to org), and to allow the Copilot agent where Copilot licences exist.

## Notes
- The Copilot agent's SharePoint knowledge is permission-trimmed: it uses the FAQ only for people who can open it. People in other departments get GOV.UK, the explorer and the playbooks.
- Web search in a declarative agent allows up to four sites with at most two path segments, so GOV.UK is given as `www.gov.uk/government`. The instructions keep it to the DAM Policy pages.
- The explorer stores nothing on a server. Progress, settings and tested assets stay in the user's browser.
