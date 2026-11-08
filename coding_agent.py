"""
coding_agent.py — JARVIS UNIVERSAL WEBSITE BUILDER + LOCAL RUNNER
"""

from datetime import datetime
from pathlib import Path
import json
import os
import re
import shutil
import socket
import subprocess
import time
import threading
import urllib.request
import webbrowser
import html as pyhtml

import ollama

MODEL = "qwen3:4b-instruct"
OLLAMA_CLIENT = ollama.Client(timeout=180)
NUM_PREDICT_CREATE = 0
NUM_PREDICT_EDIT = 3000
START_PORTS = (5173, 5174, 4173, 4174, 8000, 8080)
RUNTIME_FILE = ".jarvis_runtime.json"


def _desktop_root():
    candidates = []
    onedrive = os.environ.get("OneDrive")
    if onedrive:
        candidates.append(Path(onedrive) / "Desktop")
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        candidates.append(Path(userprofile) / "OneDrive" / "Desktop")
        candidates.append(Path(userprofile) / "Desktop")
    candidates.append(Path.home() / "OneDrive" / "Desktop")
    candidates.append(Path.home() / "Desktop")
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except OSError:
            pass
    return candidates[0] if candidates else Path.home()


ROOT = _desktop_root() / "JarvisWebProjects"
FILE_MARKER = re.compile(r"^###\s*FILE:\s*(.+?)\s*$", re.MULTILINE)
PROJECT_NAME_MARKER = re.compile(r"^PROJECT_NAME:\s*(.+?)\s*$", re.MULTILINE)

# Filled verbatim from the user's uploaded Universal Website Builder specification.
MASTER_WEBSITE_PROMPT = '# JARVIS — UNIVERSAL WEBSITE BUILDER AGENT\n\nYou are JARVIS, an expert autonomous website development agent.\n\nYour job is to transform ANY website idea, description, screenshot, reference, or rough instruction into a complete, modern, responsive, production-quality website.\n\nYou are not just a code generator.\n\nYou are a:\n\n- Senior UI/UX Designer\n- Frontend Engineer\n- Full-Stack Engineer\n- Web Architect\n- Responsive Design Expert\n- Accessibility Engineer\n- Performance Engineer\n- SEO Engineer\n- Debugging Agent\n- QA Engineer\n\nYour goal is to build websites that look professionally designed, work correctly, and are ready to run.\n\n---\n\n## 1. UNIVERSAL WEBSITE CAPABILITY\n\nYou must be capable of creating any common website category, including:\n\n- Landing pages\n- Portfolio websites\n- Personal websites\n- Business websites\n- Corporate websites\n- SaaS websites\n- AI websites\n- E-commerce stores\n- Product pages\n- Admin dashboards\n- Analytics dashboards\n- Education websites\n- College/university websites\n- Course platforms\n- Blog websites\n- News websites\n- Documentation websites\n- Community websites\n- Social-media-style interfaces\n- Chat applications\n- AI chat interfaces\n- Booking websites\n- Restaurant websites\n- Hotel websites\n- Real-estate websites\n- Job portals\n- Freelancing platforms\n- Finance dashboards\n- Crypto dashboards\n- Gaming websites\n- Event websites\n- Agency websites\n- Marketing websites\n- Startup websites\n- Authentication pages\n- Pricing pages\n- Documentation portals\n- Internal tools\n- Developer tools\n- Mobile-app landing pages\n- Web applications\n- Management systems\n- College projects\n- Experimental interfaces\n- Futuristic interfaces\n- JARVIS/HUD interfaces\n\nIf the requested website doesn\'t fit a known category, intelligently create an appropriate architecture.\n\n---\n\n# 2. FIRST UNDERSTAND THE REQUEST\n\nBefore writing code, internally determine:\n\n1. Website purpose\n2. Target users\n3. Required pages\n4. Required features\n5. Content structure\n6. Visual style\n7. Navigation structure\n8. Responsive requirements\n9. Interactive elements\n10. Data requirements\n11. Authentication requirements\n12. Backend requirements\n13. API requirements\n14. Performance requirements\n15. Accessibility requirements\n16. SEO requirements\n\nDo NOT blindly start coding.\n\nIf the request is sufficiently clear, start building immediately.\n\nDo not ask unnecessary questions.\n\nIf something is missing but can reasonably be inferred, make a professional decision and continue.\n\nOnly ask a question when the missing information is absolutely necessary.\n\n---\n\n# 3. DESIGN INTELLIGENCE\n\nNever create a generic-looking website unless explicitly requested.\n\nChoose a visual system appropriate to the project.\n\nExamples:\n\nLuxury:\n\n- Elegant typography\n- Large spacing\n- Minimal UI\n- Premium visual hierarchy\n\nTechnology:\n\n- Dark interface\n- Glass effects\n- Subtle gradients\n- Technical typography\n- Animated elements\n\nCorporate:\n\n- Clean layout\n- Strong hierarchy\n- Professional colors\n- Clear CTAs\n\nE-commerce:\n\n- Product-focused layout\n- Strong imagery\n- Clear pricing\n- Filters\n- Cart interactions\n\nAI:\n\n- Futuristic but usable\n- Conversational UI\n- Clean cards\n- Intelligent animations\n\nEducation:\n\n- Clear navigation\n- Readable typography\n- Structured content\n- Accessible controls\n\nDo not force the same design onto every website.\n\n---\n\n# 4. DESIGN SYSTEM\n\nBefore implementing UI, establish a consistent design system.\n\nDefine:\n\n- Primary color\n- Secondary color\n- Accent color\n- Background colors\n- Text colors\n- Border colors\n- Typography\n- Font sizes\n- Font weights\n- Spacing scale\n- Border radius\n- Shadows\n- Button styles\n- Card styles\n- Input styles\n- Navigation styles\n- Modal styles\n\nUse CSS variables or an equivalent centralized system.\n\nAvoid random colors and inconsistent spacing.\n\n---\n\n# 5. TECHNOLOGY STACK\n\nDefault to a modern web stack unless the user specifies otherwise.\n\nPreferred stack:\n\nFrontend:\n\n- React\n- Vite\n- JavaScript or TypeScript\n- HTML5\n- CSS3\n\nUI:\n\n- Tailwind CSS when appropriate\n- Custom CSS when better\n- Framer Motion for animations when appropriate\n\n3D:\n\n- Three.js\n- React Three Fiber when appropriate\n\nIcons:\n\n- Lucide React or another consistent icon library\n\nBackend when required:\n\n- Node.js\n- Express or an appropriate framework\n- REST APIs or other appropriate architecture\n\nDatabase when required:\n\n- PostgreSQL\n- SQLite for simple local projects\n- Supabase/Firebase when appropriate\n\nDo not introduce unnecessary dependencies.\n\n---\n\n# 6. PROJECT ARCHITECTURE\n\nCreate a clean and maintainable project structure.\n\nPrefer:\n\nsrc/\ncomponents/\npages/\nlayouts/\nhooks/\nservices/\nutils/\nassets/\nstyles/\ndata/\n\nKeep components modular.\n\nAvoid putting the entire website into one huge component.\n\nAvoid duplicated code.\n\nUse reusable components for:\n\n- Navbar\n- Footer\n- Buttons\n- Cards\n- Forms\n- Modals\n- Tables\n- Dropdowns\n- Tabs\n- Toasts\n- Loading states\n- Error states\n\n---\n\n# 7. RESPONSIVE DESIGN\n\nEvery website MUST work on:\n\n- Mobile\n- Tablet\n- Laptop\n- Desktop\n- Large desktop screens\n\nDo not simply shrink the desktop design.\n\nAdapt the layout intelligently.\n\nCheck:\n\n- Navigation\n- Typography\n- Grid layouts\n- Images\n- Buttons\n- Forms\n- Tables\n- Cards\n- Modals\n- Spacing\n\nNothing should overflow horizontally.\n\n---\n\n# 8. UI/UX QUALITY\n\nEvery page should have:\n\n- Clear visual hierarchy\n- Logical navigation\n- Obvious primary action\n- Consistent spacing\n- Readable typography\n- Proper contrast\n- Useful feedback\n- Loading states\n- Empty states\n- Error states\n- Hover states\n- Focus states\n- Active states\n\nNever create buttons that do nothing unless explicitly intended.\n\nNever create fake functionality and present it as real functionality.\n\nIf backend functionality is unavailable, clearly structure the frontend so the backend can be connected later.\n\n---\n\n# 9. ANIMATIONS\n\nAnimations should improve the experience, not slow the website down.\n\nUse:\n\n- Smooth transitions\n- Micro-interactions\n- Hover effects\n- Scroll animations\n- Page transitions\n- Subtle entrance animations\n\nAvoid:\n\n- Excessive bouncing\n- Unnecessary animation\n- Long loading animations\n- Distracting effects\n\nRespect `prefers-reduced-motion`.\n\n---\n\n# 10. ACCESSIBILITY\n\nFollow accessibility best practices.\n\nInclude:\n\n- Semantic HTML\n- Proper headings\n- Labels for inputs\n- Keyboard navigation\n- Visible focus states\n- Alt text\n- Accessible buttons\n- Accessible modals\n- Proper ARIA only when necessary\n- Sufficient color contrast\n\nDo not rely only on color to communicate information.\n\n---\n\n# 11. PERFORMANCE\n\nOptimize the website.\n\nUse:\n\n- Lazy loading\n- Code splitting when useful\n- Optimized images\n- Efficient rendering\n- Minimal dependencies\n- Memoization only where useful\n- Avoid unnecessary re-renders\n\nDo not sacrifice usability for theoretical optimization.\n\n---\n\n# 12. SEO\n\nFor public websites include:\n\n- Proper title\n- Meta description\n- Semantic structure\n- Open Graph metadata\n- Proper heading hierarchy\n- Descriptive URLs\n- Image alt text\n- Structured data when appropriate\n\n---\n\n# 13. FUNCTIONALITY\n\nWhen the user asks for functionality, implement the actual interaction.\n\nExamples:\n\nIf asked for:\n"search"\n\nBuild:\n\n- Search input\n- Search state\n- Filtering/search logic\n- Results\n- Empty state\n\nIf asked for:\n"shopping cart"\n\nBuild:\n\n- Add to cart\n- Remove\n- Quantity controls\n- Cart total\n- Empty cart state\n\nIf asked for:\n"login"\n\nBuild:\n\n- Form\n- Validation\n- Error state\n- Loading state\n- Success state\n- Authentication integration point\n\nIf asked for:\n"dashboard"\n\nBuild:\n\n- Navigation\n- Cards\n- Tables\n- Filters\n- Charts when appropriate\n- Responsive layout\n\n---\n\n# 14. FORMS\n\nForms must include:\n\n- Labels\n- Validation\n- Required fields\n- Error messages\n- Loading state\n- Success state\n- Disabled state\n\nNever allow invalid data to silently pass.\n\n---\n\n# 15. DATA VISUALIZATION\n\nFor dashboards:\n\nUse appropriate charts such as:\n\n- Line charts\n- Bar charts\n- Area charts\n- Pie/donut charts\n- KPI cards\n\nCharts must be readable and responsive.\n\nDo not add charts simply for decoration.\n\n---\n\n# 16. E-COMMERCE MODE\n\nWhen building an e-commerce website, support:\n\n- Product grid\n- Product details\n- Categories\n- Search\n- Filters\n- Sorting\n- Cart\n- Quantity management\n- Wishlist\n- Checkout UI\n- Order summary\n- Responsive product cards\n\nUse realistic placeholder data when actual data isn\'t provided.\n\n---\n\n# 17. SAAS MODE\n\nFor SaaS websites support:\n\n- Hero\n- Features\n- Product showcase\n- Pricing\n- Testimonials\n- FAQ\n- CTA\n- Login\n- Signup\n- Dashboard\n- Billing UI\n- Settings\n\n---\n\n# 18. DASHBOARD MODE\n\nFor dashboards support:\n\n- Sidebar\n- Top navigation\n- KPI cards\n- Charts\n- Tables\n- Filters\n- Search\n- Notifications\n- User profile\n- Settings\n- Responsive mobile navigation\n\n---\n\n# 19. AI WEBSITE MODE\n\nFor AI products support:\n\n- Chat interface\n- Message history\n- Prompt input\n- Model selector\n- Loading state\n- Streaming-style UI when appropriate\n- File upload UI\n- Tool status\n- Settings\n- Conversation management\n\nThe interface should feel intelligent without becoming visually cluttered.\n\n---\n\n# 20. JARVIS / FUTURISTIC MODE\n\nWhen the request is related to JARVIS, AI assistants, HUDs, robotics, or futuristic technology:\n\nUse:\n\n- Dark futuristic interface\n- HUD-inspired elements\n- Glowing accents\n- Circular/technical elements\n- Data visualization\n- System status indicators\n- Smooth motion\n- Voice interaction indicators\n- Real-time telemetry panels\n\nHowever:\n\nPrioritize readability and performance over visual effects.\n\nThe interface should look futuristic while remaining usable.\n\n---\n\n# 21. CODE QUALITY\n\nWrite production-quality code.\n\nRules:\n\n- No unnecessary duplication\n- No dead code\n- No unused imports\n- No broken references\n- No undefined variables\n- No console errors\n- No missing dependencies\n- No hardcoded secrets\n- No insecure API keys in frontend\n- No massive monolithic components\n\nUse meaningful names.\n\n---\n\n# 22. ERROR HANDLING\n\nWhen something fails:\n\n1. Identify the actual cause.\n2. Explain the cause briefly.\n3. Fix the root problem.\n4. Re-check dependent components.\n5. Verify that the fix did not break another feature.\n\nDo not randomly rewrite working code.\n\nDo not repeatedly apply blind patches.\n\n---\n\n# 23. DEBUGGING MODE\n\nIf the user reports an error:\n\nDo NOT immediately rewrite the entire project.\n\nFirst determine:\n\n- Exact error\n- File\n- Line\n- Root cause\n- Dependency issue\n- Runtime issue\n- Browser issue\n- API issue\n- State issue\n- CSS/layout issue\n\nThen apply the smallest reliable fix.\n\nAfter fixing, check for related issues.\n\n---\n\n# 24. SELF-TESTING\n\nBefore declaring the website complete, mentally verify:\n\n- Does it compile?\n- Are imports correct?\n- Are components connected?\n- Are routes valid?\n- Do buttons work?\n- Do forms work?\n- Does navigation work?\n- Is mobile responsive?\n- Are there console errors?\n- Are assets correctly referenced?\n- Are animations functional?\n- Are loading/error/empty states handled?\n\nIf tools are available, actually run the project and inspect errors instead of assuming it works.\n\n---\n\n# 25. USER REQUEST INTERPRETATION\n\nThe user may give incomplete instructions such as:\n\n"Make a modern portfolio."\n\nInterpret it intelligently.\n\nCreate:\n\n- Hero\n- About\n- Skills\n- Projects\n- Experience\n- Contact\n- Responsive navigation\n- Footer\n\nThe user may say:\n\n"Make it premium."\n\nInterpret that as:\n\n- Better typography\n- Better spacing\n- Better hierarchy\n- More refined colors\n- Better animations\n- More polished interactions\n\nDo not simply add random gradients.\n\n---\n\n# 26. SCREENSHOT / REFERENCE MODE\n\nIf the user provides a screenshot or visual reference:\n\nAnalyze:\n\n- Layout\n- Spacing\n- Typography\n- Colors\n- Components\n- Navigation\n- Visual hierarchy\n- Interactions\n\nThen recreate the design as accurately as practical.\n\nDo not copy copyrighted logos, proprietary assets, or protected content unnecessarily.\n\n---\n\n# 27. "MAKE IT BETTER" MODE\n\nIf the user says:\n\n"Make it better."\n\nDo not ask what they mean immediately.\n\nInspect the current implementation and improve:\n\n1. Visual hierarchy\n2. Spacing\n3. Typography\n4. Responsiveness\n5. UX\n6. Accessibility\n7. Performance\n8. Interactions\n9. Consistency\n\nPreserve functionality that already works.\n\n---\n\n# 28. NO FAKE COMPLETION\n\nNever say:\n\n"Done."\n\nunless the requested work is actually completed.\n\nNever claim:\n\n- Tested\n- Working\n- Production ready\n- API connected\n- Database connected\n\nunless it has actually been verified.\n\n---\n\n# 29. FILE EDITING RULE\n\nWhen modifying an existing project:\n\n- Inspect the relevant files first.\n- Preserve working functionality.\n- Make targeted changes.\n- Do not unnecessarily replace the entire project.\n- Maintain existing architecture unless there is a strong reason to change it.\n\n---\n\n# 30. OUTPUT BEHAVIOR\n\nWhen asked to create a website:\n\n1. Understand the requirement.\n2. Decide architecture.\n3. Build the UI.\n4. Implement functionality.\n5. Make it responsive.\n6. Check for errors.\n7. Improve visual polish.\n8. Verify the final result.\n\nIf the user asks for code, provide complete usable code rather than fragments whenever practical.\n\nIf working directly inside a project environment, modify the project files instead of merely describing what the user should do.\n\n---\n\n# 31. ABSOLUTE RULE\n\nYour standard is NOT:\n\n"Does this code technically work?"\n\nYour standard is:\n\n"Would a professional developer confidently show this website to a real user?"\n\nEvery website should aim for:\n\nFUNCTIONAL + RESPONSIVE + ACCESSIBLE + FAST + CLEAN + MODERN + MAINTAINABLE.\n\nYou are JARVIS.\n\nBuild the website, not just the code.'

EXECUTION_CONTRACT = r'''

============================================================
JARVIS EXECUTION CONTRACT — ACTUAL WEBSITE, NOT JUST CODE
============================================================

1. Treat every concrete detail in the user's request as a hard requirement.
2. If the user gives a screenshot/reference, reproduce composition, spacing, typography,
   hierarchy and interactions as accurately as practical while using original/properly
   licensed assets.
3. Choose the simplest reliable stack that can deliver the requested quality. Use static
   HTML/CSS/JS for simple sites. Use React/Vite for complex web apps, dashboards and
   component-heavy projects when it genuinely helps.
4. The generated project MUST be runnable locally.
5. Never output only a plan, pseudo-code, explanation or partial snippet. Output complete files.
6. Validate generated files before claiming success. If validation or build/runtime testing
   finds a concrete problem, make one targeted repair pass and test again.
7. Build for a real user goal: buy, book, contact, sign up, browse, compare, read, use a tool,
   or manage information. Make primary interactions actually work locally when backend access
   is not provided.
8. Do not invent real-world claims, customer names, awards, addresses, phone numbers, metrics,
   partnerships, credentials or prices. Use generic/demo data when the user did not supply facts.
9. Never place API keys, passwords or secrets in frontend source.
10. Do not create fake connected functionality. Clearly structure integration points where a real
    backend/API is required.
11. Keep dependencies purposeful. Avoid bloating simple projects.
12. Preserve existing working functionality when editing a project.
13. The final result should be good enough for a real client demo: polished, coherent, responsive,
    accessible and maintainable — not an AI code sample.

OUTPUT FORMAT
First line:
PROJECT_NAME: short-kebab-case-name
Then one or more blocks:
### FILE: relative/path.ext
<complete raw file contents>
No markdown fences, explanations, diffs or omitted files.
'''


UNIVERSAL_INDUSTRY_EXTENSION = """\nUNIVERSAL INDUSTRY BLUEPRINT EXTENSION:
You must intelligently specialize the UI, information architecture, content, navigation, and interactions for the requested industry. Never force a restaurant/ecommerce layout onto another industry.

Supported blueprint families include:
- Airline / flight booking: origin, destination, dates, passengers, cabin, fare comparison, filters, flight cards, baggage, seat selection, booking, check-in, manage booking.
- Railway / train booking: from/to stations, date, quota, class, train list, timing, duration, availability, fare, PNR, booking flow.
- Bus booking: route, date, operator, boarding/drop points, seat map, filters, fares, booking.
- Travel / tourism: destinations, packages, itinerary, stays, activities, search, filters, booking.
- Hotel / resort: rooms, dates, guests, availability, amenities, gallery, booking.
- PG / hostel: room type, occupancy, rent, amenities, location, availability, rules, enquiry, resident login.
- College / university: admissions, programs, departments, faculty, campus, notices, events, fees, student portal.
- Government / citizen portal: services, applications, certificates, status tracking, payments, grievance/help.
- Jobs / recruitment: search, filters, job cards, companies, profile, resume, saved jobs, applications.
- Healthcare: doctors, departments, appointment slots, patient portal, reports, pharmacy.
- Banking / fintech: accounts, cards, transfers, bills, statements, security, support.
- Marketplace / ecommerce: search, categories, filters, product detail, cart, wishlist, checkout.
- SaaS / dashboard: product value proposition, feature architecture, pricing, auth, workspace, metrics, settings.
- News / magazine: sections, headlines, article cards, search, topic filters, article reading.
- Social/community: feed, profiles, explore, messaging, notifications, moderation.
- Automotive: vehicle search, comparison, specs, financing, dealers, test drive.
- Salon / spa / gym: services/classes, staff/trainers, schedule, booking, memberships.
- Cinema / events: movies/events, showtimes/schedule, venue, seat selection, ticket booking.
- Portal / internal tools: dashboard, navigation, tasks, documents, users, permissions, settings.

VISUAL INTELLIGENCE:
Choose a design language appropriate to the product. A premium cinematic black-glass style is available when requested, but is NOT mandatory for every website. For finance/health/government/education, prioritize clarity and trust; for travel/restaurant/hotel, prioritize imagery and discovery; for SaaS/dashboard/portal, prioritize hierarchy and density; for ecommerce, prioritize products and conversion.

FUNCTIONALITY:
Build realistic frontend interactions for the category: search, filters, tabs, sorting, forms, modals, drawers, booking/checkout flows, saved items, validation, loading/success/error states. Never leave important buttons dead.

QUALITY:
The website should feel like a real product, not a category mockup. Use category-specific labels, realistic sample data, responsive layouts, accessible controls, and coherent design tokens.
\n"""

CAPABILITIES_PROMPT = (MASTER_WEBSITE_PROMPT + EXECUTION_CONTRACT + "\n\n" + UNIVERSAL_INDUSTRY_EXTENSION).strip()


def _extract_files(raw_text):
    text = str(raw_text or "").strip()
    project_name = None
    m = PROJECT_NAME_MARKER.search(text)
    if m:
        project_name = m.group(1).strip()
    matches = list(FILE_MARKER.finditer(text))
    if not matches:
        return project_name, {}
    files = {}
    for i, m in enumerate(matches):
        path = m.group(1).strip().strip('"').strip("'")
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip("\n")
        content = re.sub(r"^```[a-zA-Z0-9_+-]*\s*\n", "", content)
        content = re.sub(r"\n```\s*$", "", content)
        if path:
            files[path] = content
    return project_name, files


def _safe_join(folder, relative_path):
    raw = str(relative_path or "").replace("\\", "/").strip()
    if not raw or raw.startswith("/") or re.match(r"^[A-Za-z]:/", raw):
        return None
    target = (folder / raw).resolve()
    base = folder.resolve()
    if base not in target.parents and target != base:
        return None
    return target


def ai_files(system, prompt, tokens, require_index=True, attempts=1):
    """Bounded Ollama helper used only for existing-site edits."""
    response = OLLAMA_CLIENT.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0.20, "num_predict": min(int(tokens), 3000), "num_ctx": 16384},
        think=False,
    )
    raw = str(response["message"]["content"]).strip()
    project_name, files = _extract_files(raw)
    has_index = any(Path(name).name.lower() == "index.html" for name in files)
    if files and ((not require_index) or has_index):
        return project_name, files
    raise ValueError("Model did not return a valid project-file response.")


def backup(folder):
    if not folder.exists():
        return None
    backup_root = ROOT / ".jarvis_backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    dest = backup_root / f"{folder.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    dest.mkdir(parents=True, exist_ok=True)
    for item in folder.iterdir():
        if item.name == ".jarvis_backups":
            continue
        dst = dest / item.name
        try:
            if item.is_dir():
                shutil.copytree(item, dst)
            else:
                shutil.copy2(item, dst)
        except OSError as error:
            print(f"Coding Agent backup warning: {item} -> {error}", flush=True)
    return dest


def open_vscode(folder):
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "Code.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft VS Code" / "Code.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft VS Code" / "Code.exe",
    ]
    exe = next((p for p in candidates if p.exists()), None)
    try:
        if exe:
            subprocess.Popen([str(exe), str(folder)], close_fds=True)
        else:
            subprocess.Popen(["code", str(folder)], shell=True)
        return True
    except Exception as error:
        print(f"Coding Agent VS Code launch failed: {error}", flush=True)
        return False


def _write_files(folder, files):
    count = 0
    for relative_path, content in files.items():
        target = _safe_join(folder, relative_path)
        if target is None:
            print(f"Coding Agent skipped unsafe path: {relative_path}", flush=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content), encoding="utf-8")
        count += 1
    return count


def latest_project():
    if not ROOT.exists():
        return None
    folders = [p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith(".")]
    if not folders:
        return None
    def newest(folder):
        value = folder.stat().st_mtime
        for item in folder.rglob("*"):
            if ".jarvis_backups" in item.parts:
                continue
            try:
                value = max(value, item.stat().st_mtime)
            except OSError:
                pass
        return value
    return max(folders, key=newest)


def read_project(folder):
    index = folder / "index.html"
    if not index.exists():
        htmls = sorted(folder.glob("*.html"))
        index = htmls[0] if htmls else None
    css = [p for p in folder.rglob("*.css") if ".jarvis_backups" not in p.parts]
    js = [p for p in folder.rglob("*.js") if ".jarvis_backups" not in p.parts]
    js += [p for p in folder.rglob("*.mjs") if ".jarvis_backups" not in p.parts]
    js += [p for p in folder.rglob("*.cjs") if ".jarvis_backups" not in p.parts]
    return index, sorted(css), sorted(js)


def _dump_files(files):
    return "\n\n".join(f"--- {name} ---\n{content}" for name, content in files.items())


def _local_refs(html_text):
    refs = []
    for attr in ("src", "href"):
        refs.extend(re.findall(rf'{attr}\s*=\s*[\"\']([^\"\']+)', html_text, flags=re.I))
    result = []
    for ref in refs:
        value = ref.split("#", 1)[0].split("?", 1)[0].strip()
        lower = value.lower()
        if not value or lower.startswith(("http://", "https://", "mailto:", "tel:", "data:", "javascript:", "blob:")):
            continue
        result.append(value)
    return result


def validate_project(folder):
    issues = []
    index = folder / "index.html"
    package = folder / "package.json"
    if not index.exists() and not package.exists():
        return False, ["Missing index.html and package.json"]

    if index.exists():
        try:
            html = index.read_text(encoding="utf-8", errors="strict")
        except Exception as error:
            html = ""
            issues.append(f"index.html read error: {error}")
        low = html.lower()
        if not re.search(r'<meta[^>]+name=[\"\']viewport[\"\']', html, flags=re.I | re.S):
            issues.append("index.html is missing viewport metadata")
        if not re.search(r"<title>\s*.+?\s*</title>", html, flags=re.I | re.S):
            issues.append("index.html is missing a meaningful title")
        if not re.search(r'<meta[^>]+name=[\"\']description[\"\']', html, flags=re.I | re.S):
            issues.append("index.html is missing a meta description")
        if len(html) < 700:
            issues.append("index.html is suspiciously small")
        for token in ("lorem ipsum", "fixme"):
            if token in low:
                issues.append(f"unfinished placeholder detected: {token}")
        for ref in _local_refs(html):
            if ref.startswith("/"):
                target = (folder / ref.lstrip("/")).resolve()
                base = folder.resolve()
                safe = base in target.parents or target == base
            else:
                target = _safe_join(folder, ref)
                safe = target is not None
            if not safe:
                issues.append(f"unsafe local reference: {ref}")
            elif not target.exists():
                issues.append(f"missing local asset/file: {ref}")

    if package.exists():
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                issues.append("package.json root must be an object")
        except Exception as error:
            issues.append(f"package.json invalid: {error}")

    for css in folder.rglob("*.css"):
        if ".jarvis_backups" in css.parts:
            continue
        try:
            value = css.read_text(encoding="utf-8", errors="strict")
            if value.count("{") != value.count("}"):
                issues.append(f"unbalanced CSS braces: {css.relative_to(folder)}")
        except Exception as error:
            issues.append(f"CSS read error in {css.name}: {error}")

    node = shutil.which("node")
    if node:
        for js in list(folder.rglob("*.js")) + list(folder.rglob("*.mjs")) + list(folder.rglob("*.cjs")):
            if ".jarvis_backups" in js.parts:
                continue
            try:
                result = subprocess.run([node, "--check", str(js)], capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    lines = (result.stderr or result.stdout).strip().splitlines()
                    issues.append(f"JavaScript syntax error in {js.relative_to(folder)}: {lines[-1] if lines else 'node --check failed'}")
            except subprocess.TimeoutExpired:
                issues.append(f"JavaScript syntax check timed out: {js.relative_to(folder)}")
            except Exception as error:
                issues.append(f"JavaScript validation error in {js.name}: {error}")
    return not issues, issues


def _npm_exe():
    return "npm.cmd" if os.name == "nt" else "npm"


def _run_npm(folder, args, timeout=240):
    try:
        result = subprocess.run([_npm_exe()] + list(args), cwd=str(folder), capture_output=True, text=True, timeout=timeout)
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        return result.returncode == 0, output[-12000:]
    except FileNotFoundError:
        return False, "npm was not found on this machine."
    except subprocess.TimeoutExpired:
        return False, "npm command timed out."
    except Exception as error:
        return False, f"npm command failed: {error}"


def _choose_port():
    for port in START_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_http(url, timeout=35):
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.5) as response:
                return True, int(response.status), ""
        except Exception as error:
            last = str(error)
            time.sleep(0.5)
    return False, 0, last


def _runtime_path(folder):
    return folder / RUNTIME_FILE


def _stop_previous_runtime(folder):
    path = _runtime_path(folder)
    if not path.exists():
        return
    try:
        info = json.loads(path.read_text(encoding="utf-8"))
        pid = int(info.get("pid", 0))
    except Exception:
        pid = 0
    if pid:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=10)
            else:
                os.kill(pid, 15)
        except Exception:
            pass
    try:
        path.unlink()
    except OSError:
        pass


def _chrome_path():
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    return next((p for p in candidates if p.exists()), None)


def _focus_chrome_window(title_hint=""):
    """Best-effort Windows foreground focus for the newly opened Chrome page."""
    if os.name != "nt":
        return
    try:
        import ctypes
        import time as _time
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        EnumWindows = user32.EnumWindows
        IsWindowVisible = user32.IsWindowVisible
        GetWindowTextLengthW = user32.GetWindowTextLengthW
        GetWindowTextW = user32.GetWindowTextW
        GetWindowThreadProcessId = user32.GetWindowThreadProcessId
        SetForegroundWindow = user32.SetForegroundWindow
        GetCurrentProcessId = kernel32.GetCurrentProcessId

        wanted = str(title_hint or "").lower()
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def enum_proc(hwnd, lparam):
            if not IsWindowVisible(hwnd):
                return True
            length = GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            if not title:
                return True
            if "chrome" not in title.lower() and wanted and wanted not in title.lower():
                return True
            pid = ctypes.c_ulong()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            found.append((hwnd, title, pid.value))
            return True

        for _ in range(8):
            found.clear()
            EnumWindows(enum_proc, 0)
            if found:
                # Prefer the window whose title contains the current page title.
                target = next((x for x in found if wanted and wanted in x[1].lower()), found[0])
                SetForegroundWindow(target[0])
                return
            _time.sleep(0.25)
    except Exception:
        pass


def open_chrome(url):
    try:
        chrome = _chrome_path()
        if chrome:
            subprocess.Popen([str(chrome), "--new-window", "--start-maximized", url], close_fds=True)
            # Give Chrome a moment to create the window, then explicitly foreground it.
            title_hint = ""
            try:
                with urllib.request.urlopen(url, timeout=2.5) as response:
                    text = response.read(12000).decode("utf-8", errors="ignore")
                    m = re.search(r"<title>\s*(.*?)\s*</title>", text, flags=re.I | re.S)
                    title_hint = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
            except Exception:
                pass
            threading.Thread(target=lambda: (time.sleep(0.8), _focus_chrome_window(title_hint)), daemon=True).start()
            return True, "Chrome opened and foreground focus requested."
        webbrowser.open_new_tab(url)
        return True, "Default browser opened."
    except Exception as error:
        return False, f"Browser launch failed: {error}"


def _start_static_server(folder, port):
    python_exe = shutil.which("py") or shutil.which("python") or shutil.which("python3")
    if not python_exe:
        return None, "Python launcher not found."
    log_path = folder / ".jarvis_server.log"
    try:
        log = log_path.open("a", encoding="utf-8")
        command = [python_exe, "-m", "http.server", str(port), "--bind", "127.0.0.1"]
        kwargs = dict(cwd=str(folder), stdout=log, stderr=subprocess.STDOUT, close_fds=True)
        if os.name == "nt":
            kwargs["creationflags"] = 0x00000200 | 0x00000008
        process = subprocess.Popen(command, **kwargs)
        log.close()
        return process, str(log_path)
    except Exception as error:
        try:
            log.close()
        except Exception:
            pass
        return None, f"Static server launch failed: {error}"


def _start_npm_server(folder, port):
    package_path = folder / "package.json"
    try:
        data = json.loads(package_path.read_text(encoding="utf-8"))
    except Exception as error:
        return None, f"package.json read failed: {error}"
    scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
    if not isinstance(scripts, dict):
        scripts = {}

    if "dev" in scripts:
        cmd = f"npm.cmd run dev -- --host 127.0.0.1 --port {port}" if os.name == "nt" else f"npm run dev -- --host 127.0.0.1 --port {port}"
    elif "start" in scripts:
        cmd = f"npm.cmd run start -- --host 127.0.0.1 --port {port}" if os.name == "nt" else f"npm run start -- --host 127.0.0.1 --port {port}"
    elif (folder / "index.html").exists():
        return _start_static_server(folder, port)
    else:
        return None, "package.json has no dev/start script and no index.html."

    log_path = folder / ".jarvis_server.log"
    try:
        log = log_path.open("a", encoding="utf-8")
        if os.name == "nt":
            command = ["cmd.exe", "/c", cmd]
            kwargs = dict(cwd=str(folder), stdout=log, stderr=subprocess.STDOUT, close_fds=True, creationflags=0x00000200 | 0x00000008)
        else:
            command = ["sh", "-lc", cmd]
            kwargs = dict(cwd=str(folder), stdout=log, stderr=subprocess.STDOUT, close_fds=True, start_new_session=True)
        process = subprocess.Popen(command, **kwargs)
        log.close()
        return process, str(log_path)
    except Exception as error:
        try:
            log.close()
        except Exception:
            pass
        return None, f"Project server launch failed: {error}"


def _playwright_smoke(url, folder):
    """Run a real browser smoke test when Playwright is already installed."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return True, ["Browser smoke test skipped: Playwright not installed."]

    errors = []
    desktop_shot = folder / "jarvis-preview.png"
    mobile_shot = folder / "jarvis-preview-mobile.png"
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome", headless=True)
            except Exception as chrome_error:
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as browser_error:
                    combined = f"{chrome_error} {browser_error}".lower()
                    if "executable" in combined and ("doesn't exist" in combined or "not found" in combined or "missing" in combined):
                        return True, ["Browser smoke test skipped: Playwright browser executable is not installed."]
                    return False, [f"Browser launch failed: {browser_error}"]
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda msg: errors.append(f"console {msg.type}: {msg.text}") if msg.type == "error" else None)
            page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
            response = page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(900)
            if response and response.status >= 400:
                errors.append(f"HTTP status {response.status}")
            body_text = page.locator("body").inner_text(timeout=5000)
            if len(body_text.strip()) < 20:
                errors.append("Rendered page has very little visible content.")
            # Detect the exact failure mode where HTML loads but CSS is missing/invalid.
            body_bg = page.locator("body").evaluate("(el) => getComputedStyle(el).backgroundColor")
            h1_size = page.locator("h1").first.evaluate("(el) => getComputedStyle(el).fontSize") if page.locator("h1").count() else ""
            if body_bg in ("rgba(0, 0, 0, 0)", "transparent") or h1_size in ("2em", "32px", ""):
                errors.append("Stylesheet appears not to be applied.")
            page.screenshot(path=str(desktop_shot), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(300)
            page.screenshot(path=str(mobile_shot), full_page=True)
            browser.close()
    except Exception as error:
        return False, [f"Browser smoke test failed: {error}"]
    return not errors, errors


def launch_project(folder):
    _stop_previous_runtime(folder)
    package = folder / "package.json"
    port = _choose_port()

    if package.exists() and shutil.which(_npm_exe()):
        # Keep dependencies synchronized with package.json/package-lock.json so an edited
        # project really runs the version JARVIS just wrote. npm is usually fast when cached.
        ok, output = _run_npm(folder, ["install", "--no-audit", "--no-fund"], 120)
        if not ok:
            return False, "npm install failed: " + output[-5000:]
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
        if isinstance(scripts, dict) and "build" in scripts:
            ok, output = _run_npm(folder, ["run", "build"], 120)
            if not ok:
                return False, "npm run build failed: " + output[-7000:]
        process, log_note = _start_npm_server(folder, port)
    else:
        process, log_note = _start_static_server(folder, port)

    if process is None:
        return False, str(log_note)

    url = f"http://127.0.0.1:{port}/"
    ready, status, error = _wait_http(url)
    if not ready:
        try:
            process.terminate()
        except Exception:
            pass
        return False, f"Local server did not become ready: {error}"

    smoke_ok, smoke_notes = _playwright_smoke(url, folder)
    if not smoke_ok:
        try:
            process.terminate()
        except Exception:
            pass
        return False, "Browser smoke test found runtime problems: " + "; ".join(smoke_notes[:8])

    _runtime_path(folder).write_text(json.dumps({
        "pid": process.pid,
        "url": url,
        "port": port,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "http_status": status,
    }, indent=2), encoding="utf-8")

    vscode_ok = open_vscode(folder)
    chrome_ok, browser_message = open_chrome(url)
    message = f"Live website: {url}"
    message += " VS Code opened." if vscode_ok else " VS Code could not be opened automatically."
    message += " " + browser_message
    if smoke_notes:
        message += " " + " ".join(smoke_notes[:1])
    return True, message


def _repair(folder, request, issues):
    index, css, js = read_project(folder)
    paths = []
    if index:
        paths.append(index)
    paths += css + js
    if (folder / "package.json").exists():
        paths.append(folder / "package.json")
    current = {}
    for path in paths:
        try:
            current[str(path.relative_to(folder)).replace("\\", "/")] = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    system = CAPABILITIES_PROMPT + "\n\nYou are the FINAL QA + REPAIR pass. Fix only the concrete issues below. Preserve the user's requested design and functionality. Return the complete corrected project files."
    prompt = f"""
USER REQUEST:
{request}

CONCRETE ISSUES:
- {chr(10).join(issues)}

CURRENT PROJECT:
{_dump_files(current)}

Return complete files using PROJECT_NAME + ### FILE blocks.
"""
    try:
        _, files = ai_files(system, prompt, NUM_PREDICT_EDIT)
    except Exception as error:
        return False, str(error)
    backup(folder)
    _write_files(folder, files)
    return True, "repair applied"



def _site_kind(request):
    text = str(request or "").lower()
    checks = [
        ("restaurant", ("restaurant", "cafe", "coffee shop", "dining", "food")),
        ("ecommerce", ("ecommerce", "e-commerce", "online store", "shopping", "shop", "grocery")),
        ("education", ("education", "college", "university", "course", "learning", "school", "academy")),
        ("saas", ("saas", "software", "startup", "platform")),
        ("portfolio", ("portfolio", "developer portfolio", "personal website", "resume")),
        ("dashboard", ("dashboard", "analytics", "admin panel", "admin dashboard")),
        ("hotel", ("hotel", "resort", "stay", "hospitality")),
        ("realestate", ("real estate", "property", "properties", "realty")),
        ("agency", ("agency", "marketing agency", "creative agency")),
        ("event", ("event", "conference", "wedding", "festival")),
        ("ai", ("ai ", "artificial intelligence", "assistant", "copilot", "jarvis")),
        ("flight", ("flight", "airline", "airport", "air ticket", "flight booking")),
        ("train", ("train", "railway", "irctc", "rail ticket", "train booking")),
        ("bus", ("bus booking", "bus ticket", "bus travel")),
        ("travel", ("travel", "tour", "trip", "holiday", "vacation")),
        ("portal", ("portal", "customer portal", "service portal", "user portal")),
        ("pg", ("pg", "paying guest", "pg accommodation", "pg room")),
        ("hostel", ("hostel", "hostel room", "student hostel")),
        ("college", ("college website", "college portal", "university portal", "campus")),
        ("jobs", ("job portal", "jobs", "recruitment", "careers", "hiring")),
        ("healthcare", ("hospital", "clinic", "healthcare", "doctor", "medical")),
        ("banking", ("banking", "bank website", "net banking", "bank portal")),
        ("fintech", ("fintech", "payments", "payment app", "wallet")),
        ("booking", ("booking", "appointment", "reservation platform")),
        ("government", ("government", "gov portal", "citizen portal", "municipal")),
        ("news", ("news website", "news portal", "magazine")),
        ("social", ("social network", "community platform", "social app")),
        ("automotive", ("car dealership", "automotive", "cars", "vehicle")),
        ("salon", ("salon", "spa", "beauty")),
        ("gym", ("gym", "fitness", "workout")),
        ("cinema", ("cinema", "movie theatre", "movies", "theater")),
    ]
    for kind, words in checks:
        if any(w in text for w in words):
            return kind
    return "business"


def _site_copy(kind):
    names = {
        "restaurant": ("Aurelia", "Modern dining, crafted with intention."),
        "ecommerce": ("NOVA Market", "Curated products. Simple shopping."),
        "saas": ("Vertex", "Move your work forward with less friction."),
        "portfolio": ("Alex Morgan", "Designer, developer, and digital builder."),
        "dashboard": ("Pulse", "A clear view of what matters."),
        "education": ("Northstar Academy", "Learn practical skills with confidence."),
        "hotel": ("Aurelia House", "A refined stay, designed for slow moments."),
        "realestate": ("Cedar & Stone", "Find spaces that feel like yours."),
        "agency": ("Northline Studio", "Strategy, design, and digital experiences."),
        "event": ("Future Forward", "One room. Big ideas. Real connections."),
        "ai": ("NOVA AI", "An intelligent workspace for getting things done."),
        "business": ("Northstar", "A modern digital experience built around your goals."),
    }
    return names.get(kind, names["business"])


def _render_static_site(request, folder):
    """Create a fast, category-aware, genuinely functional local website."""
    kind = _site_kind(request)
    req = str(request or '').strip()
    esc = pyhtml.escape
    cinematic_glass = kind == 'restaurant' and any(k in req.lower() for k in ('black glass', 'glass gate', 'glass portal', '3d glass', 'cinematic entrance', 'welcome gate'))

    brand_map = {
        'restaurant': ('Aurelia Kitchen', 'Seasonal dining, handcrafted for the table.'),
        'ecommerce': ('NOVA Market', 'Curated everyday essentials, delivered simply.'),
        'saas': ('Vertex', 'Move your work forward with one focused workspace.'),
        'portfolio': ('Alex Morgan', 'Product designer and developer crafting digital experiences.'),
        'dashboard': ('Pulse', 'A live operational view of the numbers that matter.'),
        'education': ('Northstar Academy', 'Practical learning for ambitious people.'),
        'hotel': ('Aurelia House', 'A considered stay with thoughtful rooms and warm hospitality.'),
        'realestate': ('Cedar & Stone', 'Find distinctive spaces with confidence.'),
        'agency': ('Northline Studio', 'Strategy, design and technology for ambitious brands.'),
        'event': ('Future Forward', 'Ideas, people and conversations worth gathering for.'),
        'ai': ('NOVA AI', 'A focused AI workspace for thinking, writing and getting things done.'),
        'business': ('Northstar', 'A modern business experience built around your goals.'),
        'flight': ('Skyline Air', 'Search flights, compare fares and plan your journey.'),
        'train': ('RailConnect', 'Find trains, compare schedules and plan your route.'),
        'bus': ('RouteGo', 'Simple intercity bus discovery and booking.'),
        'travel': ('Wander', 'Trips, stays and experiences in one place.'),
        'portal': ('OnePortal', 'A secure, focused service portal for everyday tasks.'),
        'pg': ('NestPG', 'Comfortable rooms, verified stays and simple living.'),
        'hostel': ('CampusStay', 'Student rooms, facilities and resident services.'),
        'college': ('Northstar University', 'A modern digital campus for students and faculty.'),
        'jobs': ('CareerGrid', 'Discover jobs, build your profile and apply with confidence.'),
        'healthcare': ('CarePoint', 'Appointments, doctors and patient services in one place.'),
        'banking': ('Northstar Bank', 'Secure everyday banking with a clear digital experience.'),
        'fintech': ('PayFlow', 'Fast, simple digital payments and money tools.'),
        'booking': ('Bookly', 'Search availability and reserve what you need.'),
        'government': ('CitizenOne', 'Public services, applications and citizen information.'),
        'news': ('Signal Daily', 'Clear stories, live updates and focused reading.'),
        'social': ('Circle', 'A thoughtful community space for people and ideas.'),
        'automotive': ('DriveHaus', 'Explore vehicles, compare models and book a test drive.'),
        'salon': ('Luma Studio', 'Appointments, treatments and a calm beauty experience.'),
        'gym': ('Forge Fitness', 'Training plans, classes and progress in one place.'),
        'cinema': ('Framehouse', 'Discover films, showtimes and seats near you.'),
    }
    brand, tagline = brand_map.get(kind, brand_map['business'])
    if kind == 'restaurant' and 'farhan' in req.lower() and 'chatgpt' in req.lower():
        brand = 'Farhan & ChatGPT Co. Restaurant'
        tagline = 'A cinematic dining experience, crafted for the table.'

    theme_map = {
        'restaurant': ('#f7efe4', '#17130f', '#b96f3f', '#fffaf3'),
        'ecommerce': ('#f5f6f8', '#111318', '#635bff', '#ffffff'),
        'saas': ('#eef3ff', '#101522', '#4f7cff', '#ffffff'),
        'portfolio': ('#f5f1ec', '#151515', '#8b5cf6', '#ffffff'),
        'dashboard': ('#f2f6f7', '#101418', '#0ea5a4', '#ffffff'),
        'education': ('#f2f7f2', '#102014', '#3f7d4d', '#ffffff'),
        'hotel': ('#f4f0ea', '#171512', '#9b7653', '#fffdf9'),
        'realestate': ('#f1f4f0', '#111712', '#55735d', '#ffffff'),
        'agency': ('#f2f1f3', '#111114', '#e05b3f', '#ffffff'),
        'event': ('#f4f0ff', '#14101d', '#7c3aed', '#ffffff'),
        'ai': ('#eaf1ff', '#0b1020', '#3b82f6', '#ffffff'),
        'business': ('#f3f5f7', '#11151a', '#2563eb', '#ffffff'),
        'flight': ('#eef6ff', '#0c1b2a', '#1976d2', '#ffffff'),
        'train': ('#f1f4f0', '#132018', '#2f7d4a', '#ffffff'),
        'bus': ('#fff5e9', '#24170d', '#d97706', '#ffffff'),
        'travel': ('#edf7f4', '#10211d', '#0f766e', '#ffffff'),
        'portal': ('#f1f4f8', '#111827', '#475569', '#ffffff'),
        'pg': ('#fff5ed', '#21150f', '#ea580c', '#ffffff'),
        'hostel': ('#f4f2ff', '#17152a', '#6d5bd0', '#ffffff'),
        'college': ('#eef4ff', '#12203a', '#2563eb', '#ffffff'),
        'jobs': ('#f3f7ff', '#101b30', '#2563eb', '#ffffff'),
        'healthcare': ('#effaf8', '#0d2420', '#0d9488', '#ffffff'),
        'banking': ('#f2f5f9', '#101827', '#1d4ed8', '#ffffff'),
        'fintech': ('#eefdf6', '#092118', '#059669', '#ffffff'),
        'booking': ('#f8f4ff', '#1d152d', '#8b5cf6', '#ffffff'),
        'government': ('#f4f6f8', '#18202a', '#1f5f9b', '#ffffff'),
        'news': ('#f7f5f1', '#171513', '#9a3412', '#ffffff'),
        'social': ('#f2f5ff', '#12162b', '#6366f1', '#ffffff'),
        'automotive': ('#f3f3f3', '#111111', '#dc2626', '#ffffff'),
        'salon': ('#fff2f6', '#26151c', '#db2777', '#ffffff'),
        'gym': ('#f2f3f4', '#111315', '#ef4444', '#ffffff'),
        'cinema': ('#f5f1ff', '#17121f', '#7c3aed', '#ffffff'),
    }
    bg, ink, accent, surface = theme_map.get(kind, theme_map['business'])

    data = {
        'restaurant': {
            'nav': ['Menu', 'Reserve', 'About', 'Contact'],
            'hero_kicker': 'Open today · 12:00–23:00',
            'hero_cta': 'View menu',
            'hero_alt': 'Reserve a table',
            'section': "Tonight's menu",
            'items': [
                ('Truffle tagliolini', 'Hand-cut pasta, parmesan, black truffle', '₹620', 'Pasta'),
                ('Charred paneer', 'Smoked paneer, romesco, herbs, lemon', '₹480', 'Small plates'),
                ('Burrata & tomato', 'Creamy burrata, heirloom tomato, basil oil', '₹540', 'Small plates'),
                ('Miso sea bass', 'Miso glaze, greens, sesame, ginger', '₹780', 'Mains'),
                ('Wild mushroom risotto', 'Porcini, parmesan, thyme', '₹680', 'Mains'),
                ('Tiramisu', 'Espresso, mascarpone, cocoa', '₹320', 'Dessert'),
            ],
            'features': ['Chef-led tasting', 'Seasonal produce', 'Warm intimate room'],
        },
        'ecommerce': {
            'nav': ['Shop', 'Categories', 'Wishlist', 'Cart'],
            'hero_kicker': 'Free delivery over ₹999',
            'hero_cta': 'Shop products',
            'hero_alt': 'View cart',
            'section': 'Popular this week',
            'items': [
                ('Avocado Hass', 'Creamy ripe avocados · 2 pcs', '₹199', 'Produce'),
                ('Almond Milk', 'Unsweetened · 1L', '₹149', 'Dairy'),
                ('Sourdough Loaf', 'Naturally fermented artisan bread', '₹179', 'Bakery'),
                ('Greek Yogurt', 'High-protein · 400g', '₹129', 'Dairy'),
                ('Cold Brew', 'Smooth roasted coffee · 250ml', '₹169', 'Beverages'),
                ('Dark Chocolate', '72% cocoa · 100g', '₹109', 'Snacks'),
                ('Cherry Tomatoes', 'Sweet vine tomatoes · 250g', '₹89', 'Produce'),
                ('Pasta Fusilli', 'Durum wheat · 500g', '₹119', 'Pantry'),
            ],
            'features': ['Same-day delivery', 'Freshness promise', 'Easy returns'],
        },
        'saas': {
            'nav': ['Product', 'Solutions', 'Pricing', 'Sign in'],
            'hero_kicker': 'Built for modern teams',
            'hero_cta': 'Start free',
            'hero_alt': 'See pricing',
            'section': 'Everything your team needs',
            'items': [
                ('Unified workspace', 'Projects, notes and decisions in one place', 'WORK', 'Feature'),
                ('Automations', 'Connect repeatable tasks and workflows', 'FLOW', 'Feature'),
                ('Live insights', 'Turn activity into clear operational signals', 'DATA', 'Feature'),
            ],
            'features': ['Unlimited collaborators', 'Powerful automations', 'Role-based access'],
        },
        'portfolio': {
            'nav': ['Work', 'About', 'Experience', 'Contact'],
            'hero_kicker': 'Selected work · 2022–2026',
            'hero_cta': 'View projects',
            'hero_alt': 'Contact me',
            'section': 'Selected projects',
            'items': [
                ('Noma Finance', 'A calmer way to understand personal finance', '01', 'Product'),
                ('Arc Health', 'Patient experience redesign for a growing clinic', '02', 'UX'),
                ('Studio Grid', 'A modular brand system for a digital studio', '03', 'Brand'),
                ('Orbit Notes', 'A focused writing tool for deep work', '04', 'Product'),
            ],
            'features': ['Product strategy', 'Interface design', 'Frontend engineering'],
        },
        'dashboard': {
            'nav': ['Overview', 'Analytics', 'Customers', 'Settings'],
            'hero_kicker': 'Monday · Live data',
            'hero_cta': 'View analytics',
            'hero_alt': 'Export report',
            'section': 'Performance overview',
            'items': [
                ('Revenue', '₹8.42L', '+12.8%', 'up'),
                ('Orders', '1,284', '+8.4%', 'up'),
                ('Customers', '18,942', '+5.2%', 'up'),
                ('Conversion', '4.82%', '+0.7%', 'up'),
            ],
            'features': ['Realtime metrics', 'Smart filters', 'Exportable reports'],
        },
        'education': {
            'nav': ['Courses', 'Learning paths', 'Mentors', 'Sign in'],
            'hero_kicker': 'Learn at your own pace',
            'hero_cta': 'Explore courses',
            'hero_alt': 'View learning paths',
            'section': 'Popular courses',
            'items': [
                ('Python Foundations', 'Build a strong programming base', '12 weeks', 'Programming'),
                ('Data Analytics', 'From spreadsheets to real dashboards', '10 weeks', 'Data'),
                ('Web Development', 'HTML, CSS, JavaScript and projects', '14 weeks', 'Development'),
                ('UI/UX Design', 'Research, systems and polished interfaces', '8 weeks', 'Design'),
                ('DSA Essentials', 'Patterns and problem-solving practice', '12 weeks', 'Computer Science'),
                ('Career Launch', 'Portfolio, interviews and job strategy', '6 weeks', 'Career'),
            ],
            'features': ['Project-based learning', 'Mentor support', 'Certificates'],
        },
        'hotel': {
            'nav': ['Rooms', 'Experiences', 'Dining', 'Contact'],
            'hero_kicker': 'Check-in from 14:00 · Check-out 11:00',
            'hero_cta': 'Explore rooms',
            'hero_alt': 'Check availability',
            'section': 'Stay your way',
            'items': [
                ('Garden King', 'Quiet room · King bed · Breakfast included', '₹8,900', 'Room'),
                ('Terrace Suite', 'Private terrace · Living room · City view', '₹14,500', 'Suite'),
                ('Heritage Room', 'Original details · Queen bed · Courtyard', '₹10,800', 'Room'),
            ],
            'features': ['Breakfast included', '24h concierge', 'Airport transfer'],
        },
        'realestate': {
            'nav': ['Buy', 'Rent', 'Projects', 'Agents'],
            'hero_kicker': 'Curated properties · New listings weekly',
            'hero_cta': 'Explore homes',
            'hero_alt': 'Talk to an agent',
            'section': 'Featured properties',
            'items': [
                ('Palm Grove Residence', '3 bed · 2 bath · 1,850 sq ft', '₹2.45 Cr', 'Bengaluru'),
                ('Lakeview House', '4 bed · 3 bath · 2,420 sq ft', '₹3.10 Cr', 'Bengaluru'),
                ('Olive Courtyard', '2 bed · 2 bath · 1,120 sq ft', '₹92 L', 'Pune'),
                ('Skyline Loft', '2 bed · 2 bath · 1,040 sq ft', '₹1.35 Cr', 'Mumbai'),
            ],
            'features': ['Verified listings', 'Local experts', 'Private viewings'],
        },
        'agency': {
            'nav': ['Services', 'Work', 'Studio', 'Contact'],
            'hero_kicker': 'Independent design & technology studio',
            'hero_cta': 'See our work',
            'hero_alt': 'Start a project',
            'section': 'What we do',
            'items': [
                ('Brand systems', 'Identity, voice and flexible visual systems', '01', 'Brand'),
                ('Digital products', 'Strategy, UX and polished interfaces', '02', 'Product'),
                ('Web experiences', 'Fast, responsive sites that convert', '03', 'Web'),
                ('Launch campaigns', 'Creative that gives products momentum', '04', 'Campaign'),
            ],
            'features': ['Strategy first', 'Design + engineering', 'Senior team'],
        },
        'event': {
            'nav': ['Speakers', 'Schedule', 'Venue', 'Tickets'],
            'hero_kicker': '18–20 October · Bengaluru',
            'hero_cta': 'Get tickets',
            'hero_alt': 'View schedule',
            'section': 'Featured sessions',
            'items': [
                ('Designing for trust', 'How teams build products people believe in', '10:00', 'Main stage'),
                ('AI in the real world', 'From demos to useful systems', '12:15', 'Main stage'),
                ('Future of work', 'What changes when tools become collaborators', '15:00', 'Studio room'),
                ('Build night', 'A hands-on session for shipping small ideas', '18:30', 'Workshop'),
            ],
            'features': ['Live talks', 'Hands-on workshops', 'Community dinner'],
        },
        'ai': {
            'nav': ['Workspace', 'Models', 'Automations', 'Settings'],
            'hero_kicker': 'AI workspace · Ready when you are',
            'hero_cta': 'Open workspace',
            'hero_alt': 'See automations',
            'section': 'Workspace tools',
            'items': [
                ('Ask anything', 'Chat with your local AI assistant', 'CHAT', 'Tool'),
                ('Build & review', 'Generate, inspect and improve project files', 'CODE', 'Tool'),
                ('Automate routines', 'Turn repeated actions into one command', 'FLOW', 'Tool'),
                ('Memory', 'Keep useful preferences and project context nearby', 'MEM', 'Tool'),
            ],
            'features': ['Local-first', 'Fast responses', 'Project aware'],
        },
        'flight': {
            'nav': ['Flights', 'Deals', 'Manage booking', 'Check-in'],
            'hero_kicker': 'Domestic & international · Live search',
            'hero_cta': 'Search flights', 'hero_alt': 'View deals',
            'section': 'Popular routes',
            'items': [('Bengaluru → Delhi', 'Non-stop · Multiple airlines', '₹4,899', 'Flights'), ('Mumbai → Bengaluru', 'Daily departures · Flexible fares', '₹3,799', 'Flights'), ('Delhi → Kolkata', 'Morning and evening options', '₹4,299', 'Flights'), ('Chennai → Bengaluru', 'Short-haul · Frequent service', '₹2,199', 'Flights')],
            'features': ['Fare comparison', 'Seat selection', 'Easy check-in'],
        },
        'train': {
            'nav': ['Search trains', 'PNR', 'My bookings', 'Stations'],
            'hero_kicker': 'Rail travel · Timetable & availability',
            'hero_cta': 'Search trains', 'hero_alt': 'Check PNR',
            'section': 'Popular journeys',
            'items': [('Bengaluru → Howrah', 'Overnight options · Multiple classes', 'From ₹1,245', 'Rail'), ('Tata Nagar → Kolkata', 'Multiple daily services', 'From ₹650', 'Rail'), ('Delhi → Mumbai', 'Fast and overnight services', 'From ₹1,100', 'Rail'), ('Chennai → Bengaluru', 'Frequent daily trains', 'From ₹450', 'Rail')],
            'features': ['Train availability', 'PNR lookup', 'Class selection'],
        },
        'bus': {
            'nav': ['Search buses', 'Routes', 'Offers', 'Bookings'],
            'hero_kicker': 'Intercity travel · Compare operators',
            'hero_cta': 'Search buses', 'hero_alt': 'View offers',
            'section': 'Popular bus routes',
            'items': [('Bengaluru → Chennai', 'AC sleeper · Multiple operators', '₹699', 'Bus'), ('Bengaluru → Hyderabad', 'Sleeper and seater options', '₹899', 'Bus'), ('Mumbai → Pune', 'Frequent departures', '₹399', 'Bus'), ('Delhi → Jaipur', 'AC seater · Flexible timing', '₹549', 'Bus')],
            'features': ['Seat map', 'Operator comparison', 'Mobile ticket'],
        },
        'travel': {
            'nav': ['Destinations', 'Stays', 'Experiences', 'Trips'],
            'hero_kicker': 'Plan better journeys',
            'hero_cta': 'Explore destinations', 'hero_alt': 'Plan a trip',
            'section': 'Trending destinations',
            'items': [('Goa', 'Beaches, stays and weekend escapes', 'From ₹5,999', 'Destination'), ('Kashmir', 'Mountains, lakes and curated stays', 'From ₹12,499', 'Destination'), ('Rajasthan', 'Heritage, culture and road trips', 'From ₹8,999', 'Destination'), ('Kerala', 'Backwaters, food and slow travel', 'From ₹7,499', 'Destination')],
            'features': ['Curated itineraries', 'Verified stays', 'Local experiences'],
        },
        'portal': {
            'nav': ['Dashboard', 'Services', 'Requests', 'Profile'],
            'hero_kicker': 'Secure digital services',
            'hero_cta': 'Open dashboard', 'hero_alt': 'Browse services',
            'section': 'Common services',
            'items': [('Account overview', 'View profile, status and recent activity', 'OPEN', 'Service'), ('Applications', 'Start, save and track applications', 'NEW', 'Service'), ('Documents', 'Upload and manage your documents', 'FILES', 'Service'), ('Support', 'Create and track support requests', 'HELP', 'Service')],
            'features': ['Secure access', 'Status tracking', 'Document center'],
        },
        'pg': {
            'nav': ['Rooms', 'Amenities', 'Rules', 'Contact'],
            'hero_kicker': 'Verified PG accommodation',
            'hero_cta': 'Find a room', 'hero_alt': 'View amenities',
            'section': 'Available rooms',
            'items': [('Single room', 'Furnished · Wi-Fi · Power backup', '₹12,500/mo', 'Single'), ('Twin sharing', 'AC · Housekeeping · Laundry', '₹8,500/mo', 'Twin'), ('Triple sharing', 'Furnished · Meals available', '₹6,900/mo', 'Triple'), ('Premium single', 'Private bath · Workspace', '₹15,900/mo', 'Premium')],
            'features': ['Verified listings', 'Move-in ready', 'Transparent pricing'],
        },
        'hostel': {
            'nav': ['Rooms', 'Facilities', 'Mess', 'Resident portal'],
            'hero_kicker': 'Student living',
            'hero_cta': 'Explore rooms', 'hero_alt': 'Resident login',
            'section': 'Room options',
            'items': [('Single occupancy', 'Study desk · Wi-Fi · Storage', '₹9,500/mo', 'Single'), ('Double occupancy', 'Two beds · Shared bath', '₹6,800/mo', 'Double'), ('Four-bed room', 'Community living · Study zone', '₹4,900/mo', 'Shared'), ('Girls hostel', 'Secure access · Warden support', '₹7,200/mo', 'Hostel')],
            'features': ['24/7 security', 'Study spaces', 'Laundry & dining'],
        },
        'college': {
            'nav': ['Admissions', 'Academics', 'Campus', 'Student portal'],
            'hero_kicker': 'Admissions open · 2026–27',
            'hero_cta': 'Explore programs', 'hero_alt': 'Apply now',
            'section': 'Programs & departments',
            'items': [('Computer Science', 'Engineering, software and AI', 'B.Tech', 'Engineering'), ('Business Studies', 'Management, finance and strategy', 'BBA', 'Management'), ('Design', 'Product, visual and digital design', 'B.Des', 'Design'), ('Data Science', 'Statistics, ML and analytics', 'B.Sc', 'Science')],
            'features': ['Modern campus', 'Industry projects', 'Student support'],
        },
        'jobs': {
            'nav': ['Find jobs', 'Companies', 'Career advice', 'My profile'],
            'hero_kicker': 'Thousands of roles · Updated daily',
            'hero_cta': 'Search jobs', 'hero_alt': 'Create profile',
            'section': 'In-demand roles',
            'items': [('Software Engineer', 'Build products with modern engineering teams', '₹8–18 LPA', 'Technology'), ('Data Analyst', 'Turn business data into decisions', '₹5–12 LPA', 'Data'), ('UI/UX Designer', 'Design digital products people enjoy', '₹6–14 LPA', 'Design'), ('HVAC Technician', 'Technical service and installation roles', '₹3–7 LPA', 'Skilled trades')],
            'features': ['Smart search', 'Saved jobs', 'Application tracking'],
        },
        'healthcare': {
            'nav': ['Doctors', 'Appointments', 'Departments', 'Patient portal'],
            'hero_kicker': 'Care when you need it',
            'hero_cta': 'Find a doctor', 'hero_alt': 'Book appointment',
            'section': 'Care services',
            'items': [('General Medicine', 'Everyday health and preventive care', 'BOOK', 'Department'), ('Cardiology', 'Heart and cardiovascular care', 'BOOK', 'Department'), ('Diagnostics', 'Labs, imaging and reports', 'VIEW', 'Department'), ('Pharmacy', 'Prescriptions and medicine support', 'OPEN', 'Service')],
            'features': ['Doctor search', 'Appointment booking', 'Digital reports'],
        },
        'banking': {
            'nav': ['Accounts', 'Cards', 'Loans', 'Net banking'],
            'hero_kicker': 'Everyday banking, simplified',
            'hero_cta': 'Open an account', 'hero_alt': 'Login',
            'section': 'Banking products',
            'items': [('Savings account', 'Digital account with everyday banking', 'From 3.0%', 'Account'), ('Credit cards', 'Rewards and flexible payment options', 'Explore', 'Card'), ('Personal loans', 'Simple application and clear terms', 'From 10.5%', 'Loan'), ('Fixed deposits', 'Plan savings with fixed returns', 'Explore', 'Deposit')],
            'features': ['Secure login', 'Clear statements', '24/7 support'],
        },
        'fintech': {
            'nav': ['Send money', 'Cards', 'Bills', 'Wallet'],
            'hero_kicker': 'Move money in seconds',
            'hero_cta': 'Get started', 'hero_alt': 'Explore features',
            'section': 'Money tools',
            'items': [('UPI payments', 'Fast everyday payments', 'SEND', 'Payments'), ('Bills', 'Track and pay recurring bills', 'PAY', 'Bills'), ('Wallet', 'Keep a simple spending balance', 'OPEN', 'Wallet'), ('Cards', 'Digital and physical card controls', 'VIEW', 'Cards')],
            'features': ['Instant transfers', 'Spending insights', 'Secure controls'],
        },
        'booking': {
            'nav': ['Search', 'Categories', 'Bookings', 'Account'],
            'hero_kicker': 'Search · compare · reserve',
            'hero_cta': 'Start searching', 'hero_alt': 'View bookings',
            'section': 'Popular bookings',
            'items': [('Doctor appointment', 'Find a specialist and available slot', 'BOOK', 'Healthcare'), ('Hotel stay', 'Compare rooms and dates', 'BOOK', 'Hotels'), ('Salon appointment', 'Choose service and time', 'BOOK', 'Beauty'), ('Experience', 'Activities, events and local tours', 'BOOK', 'Experiences')],
            'features': ['Live availability', 'Instant confirmation', 'Easy cancellation'],
        },
        'government': {
            'nav': ['Services', 'Applications', 'Certificates', 'Help'],
            'hero_kicker': 'Citizen services',
            'hero_cta': 'Find a service', 'hero_alt': 'Track application',
            'section': 'Popular services',
            'items': [('Certificates', 'Birth, income and residence services', 'OPEN', 'Certificates'), ('Applications', 'Submit and track public applications', 'START', 'Applications'), ('Payments', 'Fees, taxes and public payments', 'PAY', 'Payments'), ('Complaints', 'Register and track grievances', 'HELP', 'Support')],
            'features': ['Accessible services', 'Application tracking', 'Help center'],
        },
        'news': {
            'nav': ['Latest', 'India', 'Business', 'Technology'],
            'hero_kicker': 'Updated throughout the day',
            'hero_cta': 'Read latest', 'hero_alt': 'Browse sections',
            'section': 'Top stories',
            'items': [('Markets open higher', 'A concise market briefing and what to watch', '01', 'Business'), ('New technology trends', 'The tools changing how teams work', '02', 'Technology'), ('City updates', 'What is happening locally today', '03', 'India'), ('Weekend guide', 'Places, events and culture worth knowing', '04', 'Lifestyle')],
            'features': ['Live updates', 'Saved stories', 'Topic feeds'],
        },
        'social': {
            'nav': ['Home', 'Explore', 'Messages', 'Profile'],
            'hero_kicker': 'A calmer community feed',
            'hero_cta': 'Explore feed', 'hero_alt': 'Create profile',
            'section': 'Community highlights',
            'items': [('Design community', 'Share work, feedback and ideas', 'JOIN', 'Community'), ('Tech circle', 'Discuss tools, projects and careers', 'JOIN', 'Community'), ('Travel stories', 'Trips, photos and local tips', 'JOIN', 'Community'), ('Creators', 'Discover independent creators', 'JOIN', 'Community')],
            'features': ['Profiles', 'Messaging', 'Community moderation'],
        },
        'automotive': {
            'nav': ['New cars', 'Used cars', 'Compare', 'Dealers'],
            'hero_kicker': 'Find your next drive',
            'hero_cta': 'Explore cars', 'hero_alt': 'Book a test drive',
            'section': 'Featured vehicles',
            'items': [('Urban EV', 'Electric · 400 km range · Automatic', '₹14.9L', 'EV'), ('City SUV', '5 seats · Petrol · Automatic', '₹13.5L', 'SUV'), ('Executive Sedan', 'Premium cabin · Hybrid', '₹24.8L', 'Sedan'), ('Adventure 4x4', 'AWD · Turbo · Off-road ready', '₹28.2L', 'SUV')],
            'features': ['Compare models', 'Test drives', 'Verified dealers'],
        },
        'salon': {
            'nav': ['Services', 'Stylists', 'Packages', 'Book'],
            'hero_kicker': 'Beauty & wellness · By appointment',
            'hero_cta': 'Book appointment', 'hero_alt': 'View services',
            'section': 'Popular services',
            'items': [('Hair styling', 'Cut, style and finish', '₹899', 'Hair'), ('Skin facial', 'Glow-focused facial treatment', '₹1,499', 'Skin'), ('Spa ritual', 'Relaxing full-body treatment', '₹2,199', 'Spa'), ('Bridal package', 'Consultation, trial and event styling', '₹8,999', 'Bridal')],
            'features': ['Verified stylists', 'Online booking', 'Memberships'],
        },
        'gym': {
            'nav': ['Classes', 'Trainers', 'Memberships', 'Progress'],
            'hero_kicker': 'Train stronger · Live better',
            'hero_cta': 'View memberships', 'hero_alt': 'Book a class',
            'section': 'Training options',
            'items': [('Strength', 'Progressive strength and conditioning', '₹2,999/mo', 'Training'), ('HIIT', 'High-intensity group sessions', '₹2,499/mo', 'Class'), ('Yoga', 'Mobility, breath and recovery', '₹1,999/mo', 'Class'), ('Personal training', 'One-to-one coaching and programming', '₹4,999/mo', 'Training')],
            'features': ['Certified trainers', 'Progress tracking', 'Flexible plans'],
        },
        'cinema': {
            'nav': ['Movies', 'Showtimes', 'Offers', 'My bookings'],
            'hero_kicker': 'Now showing · Book your seats',
            'hero_cta': 'Browse movies', 'hero_alt': 'View showtimes',
            'section': 'Now showing',
            'items': [('The Last Horizon', 'Sci-fi · 2h 18m · UA', 'From ₹220', 'Movie'), ('Midnight Run', 'Thriller · 2h 04m · A', 'From ₹180', 'Movie'), ('Paper Skies', 'Drama · 1h 56m · U', 'From ₹160', 'Movie'), ('Neon City', 'Action · 2h 22m · UA', 'From ₹240', 'Movie')],
            'features': ['Seat selection', 'Multiple formats', 'Easy booking'],
        },
        'business': {
            'nav': ['Solutions', 'Services', 'About', 'Contact'],
            'hero_kicker': 'Built around your goals',
            'hero_cta': 'Explore solutions',
            'hero_alt': 'Contact us',
            'section': 'How we help',
            'items': [
                ('Strategy', 'Turn priorities into a focused plan', '01', 'Service'),
                ('Implementation', 'Bring the plan to life with care', '02', 'Service'),
                ('Growth', 'Measure what matters and iterate', '03', 'Service'),
            ],
            'features': ['Clear plans', 'Senior expertise', 'Measurable outcomes'],
        },
    }[kind]

    items_js = json.dumps([list(x) for x in data['items']], ensure_ascii=False)
    request_js = json.dumps(req, ensure_ascii=False)
    brand_h, tagline_h = esc(brand), esc(tagline)
    nav_html = ''.join(f'<a href="#{esc(n.lower().replace(" ", "-"))}">{esc(n)}</a>' for n in data['nav'][:4])
    mobile_nav_html = ''.join(f'<a href="#{esc(n.lower().replace(" ", "-"))}" onclick="toggleMobileNav()">{esc(n)}</a>' for n in data['nav'][:4])
    feature_html = ''.join(f'<span class="chip">{esc(x)}</span>' for x in data['features'])
    cart_display = 'inline-flex' if kind == 'ecommerce' else 'none'

    shell = '''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{brand_h} — __TAGLINE__</title>
<meta name="description" content="__TAGLINE__"><meta name="theme-color" content="__ACCENT__">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='16' fill='__INK__'/><circle cx='32' cy='32' r='15' fill='none' stroke='__ACCENT__' stroke-width='6'/></svg>">
<style>
:root{{--bg:__BG__;--ink:__INK__;--accent:__ACCENT__;--surface:{surface};--muted:#697386;--line:rgba(17,24,39,.12);--shadow:0 24px 70px rgba(15,23,42,.12)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.5}}body.modal-open{{overflow:hidden}}a{{color:inherit;text-decoration:none}}button,input,select,textarea{{font:inherit}}button{{cursor:pointer}}
.nav{{position:sticky;top:0;z-index:30;background:color-mix(in srgb,var(--bg) 90%,transparent);backdrop-filter:blur(18px);border-bottom:1px solid var(--line)}}.nav-in{{max-width:1220px;margin:auto;padding:18px 24px;display:flex;align-items:center;gap:28px}}.logo{{font-size:21px;font-weight:850;letter-spacing:-.04em;margin-right:auto}}.links{{display:flex;gap:22px;color:#637084;font-size:14px;font-weight:600}}.nav-actions{{display:flex;gap:8px;align-items:center}}.icon-btn,.menu-btn{{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;padding:9px 13px}}.menu-btn{{display:none}}
.hero{{max-width:1220px;margin:auto;padding:84px 24px 58px;display:grid;grid-template-columns:1.02fr .98fr;gap:55px;align-items:center}}.eyebrow{{color:var(--accent);font-size:12px;font-weight:850;letter-spacing:.14em;text-transform:uppercase}}h1{{font-size:clamp(56px,7.6vw,104px);line-height:.9;letter-spacing:-.075em;margin:16px 0 24px;max-width:800px}}.hero-copy{{font-size:19px;color:var(--muted);max-width:650px}}.actions{{display:flex;gap:12px;flex-wrap:wrap;margin-top:30px}}.btn{{border:0;border-radius:999px;padding:14px 21px;background:var(--ink);color:var(--bg);font-weight:800}}.btn.alt{{background:transparent;color:var(--ink);border:1px solid var(--line)}}
.hero-card{{min-height:470px;border-radius:38px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent) 82%,white),color-mix(in srgb,var(--ink) 92%,var(--accent)));box-shadow:var(--shadow);position:relative;overflow:hidden}}.hero-orb{{position:absolute;width:330px;height:330px;border-radius:50%;right:-80px;top:-40px;background:rgba(255,255,255,.20)}}.hero-grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.07) 1px,transparent 1px);background-size:32px 32px;mask-image:linear-gradient(to bottom,black,transparent)}}.hero-card-inner{{position:absolute;left:26px;right:26px;bottom:26px;padding:24px;border-radius:24px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.3);backdrop-filter:blur(18px);color:#fff}}.hero-card-inner strong{{display:block;font-size:25px;letter-spacing:-.035em;margin-bottom:5px}}.hero-card-inner span{{opacity:.82}}
.section{{max-width:1220px;margin:auto;padding:68px 24px}}.section-head{{display:flex;justify-content:space-between;align-items:end;gap:24px;margin-bottom:28px}}.section h2{{font-size:clamp(35px,4.6vw,62px);line-height:.96;letter-spacing:-.06em;margin:0}}.section-head p{{color:var(--muted);max-width:470px;margin:0}}.chips{{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 20px}.chip{{border:1px solid var(--line);background:rgba(255,255,255,.42);padding:8px 12px;border-radius:999px;color:#5e6978;font-size:13px;font-weight:700}}
.search-row{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}}.search{{flex:1;min-width:220px;border:1px solid var(--line);background:var(--surface);border-radius:15px;padding:13px 15px;outline:none}}.select{{border:1px solid var(--line);background:var(--surface);border-radius:15px;padding:13px 15px;min-width:150px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.card{{border:1px solid var(--line);background:var(--surface);border-radius:24px;padding:22px;min-height:235px;display:flex;flex-direction:column;transition:transform .22s,box-shadow .22s;box-shadow:0 7px 30px rgba(15,23,42,.04)}}.card:hover{{transform:translateY(-4px);box-shadow:var(--shadow)}}.card-visual{{height:130px;border-radius:18px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent) 26%,var(--surface)),color-mix(in srgb,var(--ink) 10%,var(--surface)));margin:-3px -3px 17px;display:grid;place-items:center;font-size:33px;font-weight:900;color:var(--accent);letter-spacing:.04em}}.card-meta{{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--accent);font-weight:850;margin-bottom:8px}}.card h3{{font-size:23px;letter-spacing:-.04em;margin:0 0 7px}}.card p{{color:var(--muted);font-size:14px;margin:0 0 15px}}.card-row{{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:auto}}.price{{font-weight:850;font-size:17px}}.small-btn{{border:1px solid var(--line);background:transparent;border-radius:999px;padding:9px 13px;font-weight:800;color:var(--ink)}}
.info-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.info{{padding:22px;border-radius:22px;border:1px solid var(--line);background:rgba(255,255,255,.34)}}.info strong{{display:block;font-size:18px;margin-bottom:6px}}.info span{{color:var(--muted);font-size:14px}}
.cta{{max-width:1220px;margin:0 auto 74px;padding:44px 24px;border-radius:34px;background:var(--ink);color:var(--bg);display:flex;justify-content:space-between;align-items:center;gap:24px}}.cta h2{{font-size:clamp(31px,4vw,52px);line-height:.96;letter-spacing:-.05em;margin:0}}footer{{border-top:1px solid var(--line);padding:28px 24px;color:var(--muted)}}.foot{{max-width:1220px;margin:auto;display:flex;justify-content:space-between;gap:16px}}
.menu-tabs{{display:flex;gap:8px;overflow:auto;padding-bottom:5px;margin-bottom:18px}}.tab{{white-space:nowrap;border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:9px 14px;font-weight:750}}.tab.active{{background:var(--ink);color:var(--bg)}}
.cart-drawer{{position:fixed;right:0;top:0;height:100%;width:min(420px,92vw);background:var(--surface);z-index:60;transform:translateX(110%);transition:.25s;box-shadow:-24px 0 80px rgba(15,23,42,.18);padding:24px;display:flex;flex-direction:column}}.cart-drawer.open{{transform:translateX(0)}}.cart-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}}.cart-list{{overflow:auto;display:grid;gap:10px}}.cart-item{{border:1px solid var(--line);border-radius:16px;padding:13px}}.cart-footer{{margin-top:auto;padding-top:18px;border-top:1px solid var(--line)}}
.modal-wrap{{position:fixed;inset:0;background:rgba(5,10,20,.48);z-index:70;display:none;place-items:center;padding:18px}}.modal-wrap.open{{display:grid}}.modal{{width:min(620px,100%);max-height:90vh;overflow:auto;background:var(--surface);border-radius:26px;padding:24px;box-shadow:0 30px 100px rgba(0,0,0,.22)}}.modal-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:17px}}.modal h3{{font-size:28px;letter-spacing:-.04em;margin:0}}.close{{border:1px solid var(--line);background:transparent;border-radius:50%;width:36px;height:36px}}.form{{display:grid;gap:12px}}.form label{{font-size:13px;font-weight:800}}.form input,.form select,.form textarea{{width:100%;border:1px solid var(--line);background:var(--bg);border-radius:13px;padding:12px 13px;outline:none}}.form textarea{{min-height:110px;resize:vertical}}.form-row{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.notice{{padding:12px 14px;border-radius:14px;background:color-mix(in srgb,var(--accent) 12%,var(--surface));font-size:13px;color:var(--muted)}}
.metric-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.metric{{background:var(--surface);border:1px solid var(--line);padding:20px;border-radius:20px}}.metric span{{display:block;color:var(--muted);font-size:13px}}.metric strong{{font-size:30px;letter-spacing:-.05em;display:block;margin:4px 0}}.up{{color:#12845d;font-weight:800}}.bars{{height:220px;display:flex;align-items:end;gap:10px;padding:20px;background:var(--surface);border:1px solid var(--line);border-radius:22px}}.bar{{flex:1;background:linear-gradient(to top,var(--accent),color-mix(in srgb,var(--accent) 35%,white));border-radius:8px 8px 2px 2px;min-height:16px}}
.chat{{border:1px solid var(--line);background:var(--surface);border-radius:24px;overflow:hidden;box-shadow:var(--shadow)}}.chat-log{{height:360px;overflow:auto;padding:20px;display:grid;align-content:start;gap:12px}}.bubble{{max-width:78%;padding:12px 14px;border-radius:18px;background:rgba(100,116,139,.10)}}.bubble.me{{justify-self:end;background:var(--ink);color:var(--bg)}}.chat-box{{display:flex;gap:8px;padding:12px;border-top:1px solid var(--line)}}.chat-box input{{flex:1;border:1px solid var(--line);background:var(--bg);border-radius:13px;padding:12px}}
.cinematic-gate.not-needed{display:none}.cinematic-gate{position:fixed;inset:0;z-index:9999;background:#050608;display:grid;place-items:center;overflow:hidden;perspective:1400px;transition:visibility .2s}.cinematic-gate.hide{visibility:hidden;pointer-events:none}.gate-light{position:absolute;width:60vw;height:60vw;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.10),transparent 62%);filter:blur(8px)}.gate-title{position:relative;z-index:3;text-align:center;color:#fff;letter-spacing:.16em;text-transform:uppercase;text-shadow:0 0 35px rgba(255,255,255,.18)}.gate-title strong{display:block;font-size:clamp(22px,4vw,48px);font-weight:800}.gate-title span{display:block;margin-top:18px;font-size:12px;letter-spacing:.42em;opacity:.62}.gate-enter{margin-top:30px;border:1px solid rgba(255,255,255,.28);background:rgba(255,255,255,.08);color:#fff;padding:13px 28px;border-radius:999px;backdrop-filter:blur(18px);font-weight:800;cursor:pointer}.gate-panel{position:absolute;top:0;width:51%;height:100%;background:linear-gradient(120deg,rgba(255,255,255,.11),rgba(255,255,255,.025) 45%,rgba(255,255,255,.09));border:1px solid rgba(255,255,255,.18);backdrop-filter:blur(22px);box-shadow:inset 0 0 80px rgba(255,255,255,.025),0 0 60px rgba(0,0,0,.5);transition:transform 1.25s cubic-bezier(.77,0,.18,1)}.gate-left{left:-1%;transform-origin:left center}.gate-right{right:-1%;transform-origin:right center}.cinematic-gate.open .gate-left{transform:translateX(-100%) rotateY(-10deg)}.cinematic-gate.open .gate-right{transform:translateX(100%) rotateY(10deg)}.gate-reflection{position:absolute;inset:0;background:linear-gradient(110deg,transparent 30%,rgba(255,255,255,.14) 46%,transparent 60%);transform:translateX(-100%);transition:transform 1.1s ease}.cinematic-gate.open .gate-reflection{transform:translateX(100%)}body.gate-lock{overflow:hidden}.cinematic-gate.open .gate-title,.cinematic-gate.open .gate-enter{opacity:0;transition:opacity .35s}.cinematic-gate.open{background:#050608;transition:background .7s 0s,visibility .2s 1.3s}.cinematic-gate.open .gate-panel{transition-duration:1.25s}@media(max-width:600px){.gate-panel{width:51%}.gate-title{padding:20px}.gate-title strong{font-size:22px}.gate-title span{font-size:9px;letter-spacing:.28em}}
@media(max-width:900px){{.links{{display:none}}.menu-btn{{display:block}}.hero{{grid-template-columns:1fr;padding-top:54px;gap:30px}}.hero-card{{min-height:330px}}.grid{{grid-template-columns:1fr 1fr}}.metric-grid{{grid-template-columns:1fr 1fr}}.info-grid{{grid-template-columns:1fr}}.section-head{{align-items:flex-start;flex-direction:column}}}}
@media(max-width:600px){{.nav-in{{padding:14px 16px}}.hero,.section{{padding-left:16px;padding-right:16px}}h1{{font-size:clamp(48px,16vw,72px)}}.hero-copy{{font-size:17px}}.grid{{grid-template-columns:1fr}}.metric-grid{{grid-template-columns:1fr 1fr}}.form-row{{grid-template-columns:1fr}}.cta{{margin-left:16px;margin-right:16px;padding:32px 20px;align-items:flex-start;flex-direction:column}}.foot{{flex-direction:column}}}}
@media(prefers-reduced-motion:reduce){{*{{scroll-behavior:auto!important;transition:none!important}}}}
</style></head>
<body class="gate-lock">
<div class="cinematic-gate __CINEMATIC_GATE_CLASS__" id="cinematicGate" aria-label="Welcome entrance">
  <div class="gate-light"></div><div class="gate-reflection"></div>
  <div class="gate-panel gate-left"></div><div class="gate-panel gate-right"></div>
  <div class="gate-title"><strong>FARHAN &amp; CHATGPT CO.</strong><span>RESTAURANT · WELCOME</span><button class="gate-enter" onclick="openCinematicGate()">ENTER</button></div>
</div>
<nav class="nav"><div class="nav-in"><a class="logo" href="#top">{brand_h}</a><div class="links">__NAV__</div><div class="nav-actions"><button class="icon-btn" id="cartBtn" style="display:__CART__">Cart <b id="cartCount">0</b></button><button class="menu-btn" onclick="toggleMobileNav()">Menu</button></div></div></nav>
<div id="mobileNav" style="display:none;background:var(--surface);border-bottom:1px solid var(--line);padding:12px 16px"><div style="max-width:1220px;margin:auto;display:grid;gap:8px">__MOBILE_NAV__</div></div>
<main id="top">
<section class="hero"><div><div class="eyebrow">__KICKER__</div><h1>{brand_h}</h1><p class="hero-copy">__TAGLINE__</p><p class="hero-copy" style="font-size:14px;margin-top:10px">Request: __REQUEST__</p><div class="actions"><button class="btn" onclick="primaryAction()">__HERO_CTA__</button><button class="btn alt" onclick="secondaryAction()">__HERO_ALT__</button></div></div><div class="hero-card"><div class="hero-orb"></div><div class="hero-grid"></div><div class="hero-card-inner"><strong>__SECTION__</strong><span>Real content, clear actions and a responsive local experience.</span></div></div></section>
'''
    shell = (shell.replace('{brand_h}', brand_h).replace('__TAGLINE__', tagline_h)
             .replace('__ACCENT__', accent).replace('__INK__', ink).replace('__BG__', bg)
             .replace('__CART__', cart_display).replace('__NAV__', nav_html).replace('__MOBILE_NAV__', mobile_nav_html)
             .replace('__KICKER__', esc(data['hero_kicker'])).replace('__SECTION__', esc(data['section']))
             .replace('__REQUEST__', esc(req[:220])).replace('__HERO_CTA__', esc(data['hero_cta'])).replace('__HERO_ALT__', esc(data['hero_alt']))
             .replace('__CINEMATIC_GATE_CLASS__', 'show' if cinematic_glass else 'not-needed')
             .replace('{surface}', surface)
             .replace('{{', '{').replace('}}', '}'))

    if kind == 'restaurant':
        body = f'''<section class="section" id="menu"><div class="section-head"><div><div class="eyebrow">From the kitchen</div><h2>Tonight's menu</h2></div><p>Browse the menu, filter dishes and reserve a table. Ordering remains local/demo until a real payment or restaurant backend is connected.</p></div><div class="menu-tabs"><button class="tab active" onclick="filterCards('all',this)">All</button><button class="tab" onclick="filterCards('Small plates',this)">Small plates</button><button class="tab" onclick="filterCards('Pasta',this)">Pasta</button><button class="tab" onclick="filterCards('Mains',this)">Mains</button><button class="tab" onclick="filterCards('Dessert',this)">Dessert</button></div><div class="search-row"><input id="menuSearch" class="search" placeholder="Search the menu…" oninput="renderRestaurant()"></div><div id="cards" class="grid"></div></section><section class="section" id="reserve"><div class="section-head"><div><div class="eyebrow">Your table</div><h2>Reserve a table</h2></div><p>Choose a date, time and guest count. The local form validates your request and confirms it on screen.</p></div><button class="btn" onclick="openModal('reservation')">Book a table</button></section><section class="section" id="about"><div class="info-grid">{''.join(f'<div class="info"><strong>{esc(x)}</strong><span>Part of the {brand_h} experience.</span></div>' for x in data['features'])}</div></section><section class="section" id="contact"><div class="notice">Open daily · 12:00–23:00 · +91 90000 00000 · hello@aurelia.example</div></section>'''
    elif kind == 'ecommerce':
        body = f'''<section class="section" id="shop"><div class="section-head"><div><div class="eyebrow">Fresh picks</div><h2>Popular this week</h2></div><p>Search, filter, add products to cart, adjust quantities and walk through a local checkout flow.</p></div><div class="search-row"><input id="storeSearch" class="search" placeholder="Search products…" oninput="renderStore()"><select id="storeFilter" class="select" onchange="renderStore()"><option value="all">All categories</option><option>Produce</option><option>Dairy</option><option>Bakery</option><option>Beverages</option><option>Snacks</option><option>Pantry</option></select></div><div class="grid" id="cards"></div></section><section class="section" id="categories"><div class="chips">{feature_html}</div></section><section class="section" id="wishlist"><div class="notice"><b>Wishlist:</b> Use the ♡ button on any product to save it locally. Wishlist count persists while the page is open.</div></section><section class="section" id="contact"><div class="notice">Delivery: 7am–10pm · Bengaluru · Freshness promise on every order.</div></section><aside class="cart-drawer" id="cartDrawer"><div id="cart"><div class="cart-head"><h3 style="margin:0">Your cart</h3><button class="close" onclick="toggleCart(false)">×</button></div><div id="cartList" class="cart-list"></div><div class="cart-footer"><div style="display:flex;justify-content:space-between;margin-bottom:12px"><b>Total</b><b id="cartTotal">₹0</b></div><button class="btn" style="width:100%" onclick="openModal('checkout')">Checkout</button></div></div></aside>'''
    elif kind == 'hotel':
        body = f'''<section class="section" id="rooms"><div class="section-head"><div><div class="eyebrow">Rooms & suites</div><h2>Stay your way</h2></div><p>Compare room types and open a booking form with dates and guests.</p></div><div class="grid" id="cards"></div></section><section class="section" id="experiences"><div class="info-grid">{''.join(f'<div class="info"><strong>{esc(x)}</strong><span>Included or available on request.</span></div>' for x in data['features'])}</div></section><section class="section" id="dining"><div class="notice">Breakfast: 7–11am · Restaurant: 12–11pm · Rooftop drinks until midnight.</div></section><section class="section" id="contact"><div class="notice">Central Bengaluru · +91 90000 00000 · stay@aurelia.example</div></section>'''
    elif kind == 'realestate':
        body = f'''<section class="section" id="buy"><div class="section-head"><div><div class="eyebrow">Homes & apartments</div><h2>Featured properties</h2></div><p>Filter by city and open a local property detail card. Contact actions use the demo enquiry form.</p></div><div class="search-row"><input id="propertySearch" class="search" placeholder="Search properties or city…" oninput="renderProperty()"><select id="propertyFilter" class="select" onchange="renderProperty()"><option value="all">All locations</option><option>Bengaluru</option><option>Pune</option><option>Mumbai</option></select></div><div class="grid" id="cards"></div></section><section class="section" id="rent"><div class="notice">Rentals and off-market opportunities can use the same listing engine when backend data is connected.</div></section><section class="section" id="projects"><div class="info-grid">{''.join(f'<div class="info"><strong>{esc(x)}</strong><span>Human support and private viewings available.</span></div>' for x in data['features'])}</div></section><section class="section" id="agents"><button class="btn" onclick="openModal('enquiry')">Talk to an agent</button></section>'''
    elif kind == 'dashboard':
        body = f'''<section class="section" id="overview"><div class="metric-grid" id="metrics"></div></section><section class="section" id="analytics"><div class="section-head"><div><div class="eyebrow">Last 7 days</div><h2>Performance</h2></div><button class="btn alt" onclick="toast('Report exported locally')">Export report</button></div><div class="bars">{''.join(f'<div class="bar" style="height:{h}%" title="Day {i+1}"></div>' for i,h in enumerate([42,58,50,77,66,84,93]))}</div></section><section class="section" id="customers"><div class="info-grid"><div class="info"><strong>1,284 recent orders</strong><span>Search and filtering can be connected to your backend data source.</span></div><div class="info"><strong>96% successful payments</strong><span>Operational status summary for the demo environment.</span></div><div class="info"><strong>18,942 active customers</strong><span>Account and retention views ready for integration.</span></div></div></section><section class="section" id="settings"><button class="btn" onclick="openModal('settings')">Open settings</button></section>'''
    elif kind == 'ai':
        body = f'''<section class="section" id="workspace"><div class="section-head"><div><div class="eyebrow">Local workspace</div><h2>Ask JARVIS</h2></div><p>This local chat demonstrates the interaction surface. Your actual assistant backend can be connected to the existing bridge/model layer.</p></div><div class="chat"><div id="chatLog" class="chat-log"><div class="bubble">Hi Boss. What should we work on?</div></div><div class="chat-box"><input id="chatInput" placeholder="Ask something…" onkeydown="if(event.key==='Enter')sendChat()"><button class="btn" onclick="sendChat()">Send</button></div></div></section><section class="section" id="models"><div class="grid">{''.join(f'<article class="card"><div class="card-visual">{esc(x.split()[0][:4].upper())}</div><div class="card-meta">AI TOOL</div><h3>{esc(x)}</h3><p>{esc(y)}</p><div class="card-row"><span class="price">Ready</span><button class="small-btn" onclick="toast(\'Opened {esc(x)}\')">Open</button></div></article>' for x,y,_,_ in data['items'])}</div></section><section class="section" id="automations"><div class="chips">{feature_html}</div></section><section class="section" id="settings"><div class="notice">Local-first setup · No secrets embedded · Connect your real model/API through your existing application layer.</div></section>'''
    else:
        first_id = data['nav'][0].lower().replace(' ','-')
        second_id = data['nav'][1].lower().replace(' ','-')
        last_id = data['nav'][-1].lower().replace(' ','-')
        body = f'''<section class="section" id="{first_id}"><div class="section-head"><div><div class="eyebrow">Built for the job</div><h2>__SECTION__</h2></div><p>__TAGLINE__ Every card below is a real interactive local component, not a dead visual block.</p></div><div class="grid" id="cards"></div></section><section class="section" id="{second_id}"><div class="info-grid">{''.join(f'<div class="info"><strong>{esc(x)}</strong><span>Designed as part of the {brand_h} experience.</span></div>' for x in data['features'])}</div></section><section class="section" id="{last_id}"><div class="notice">Use the action below to open a validated local contact form.</div><div style="margin-top:14px"><button class="btn" onclick="openModal('contact')">Start a conversation</button></div></section>'''

    if kind == 'saas':
        body += '''<section class="section" id="pricing"><div class="section-head"><div><div class="eyebrow">Simple pricing</div><h2>Choose your plan</h2></div><p>Local pricing UI with signup flow.</p></div><div class="grid"><article class="card"><div class="card-meta">STARTER</div><h3>Free</h3><p>For trying the workspace.</p><div class="card-row"><span class="price">₹0</span><button class="small-btn" onclick="openModal('signup')">Start</button></div></article><article class="card"><div class="card-meta">GROWTH</div><h3>Pro</h3><p>For teams shipping every week.</p><div class="card-row"><span class="price">₹1,499/mo</span><button class="small-btn" onclick="openModal('signup')">Start</button></div></article><article class="card"><div class="card-meta">SCALE</div><h3>Enterprise</h3><p>For governance and support.</p><div class="card-row"><span class="price">Custom</span><button class="small-btn" onclick="openModal('contact')">Talk</button></div></article></div></section>'''
    elif kind == 'portfolio':
        body += '''<section class="section" id="experience"><div class="info-grid"><div class="info"><strong>2024–26 · Product Designer</strong><span>Led end-to-end product work for complex workflows.</span></div><div class="info"><strong>2022–24 · Frontend Engineer</strong><span>Built responsive interfaces and design systems.</span></div><div class="info"><strong>Earlier · Independent</strong><span>Brand, web and interaction projects.</span></div></div></section>'''
    elif kind == 'education':
        body += '''<section class="section" id="learning-paths"><div class="notice">Learning paths combine multiple courses into a structured route. Enrollment is local/demo until connected to your student backend.</div></section>'''
    elif kind == 'agency':
        body += '''<section class="section" id="case-studies"><div class="grid"><article class="card"><div class="card-visual">01</div><div class="card-meta">CASE STUDY</div><h3>Fintech launch</h3><p>Reframed a dense financial product around a clearer customer journey.</p><button class="small-btn" onclick="openModal('case')">View case study</button></article><article class="card"><div class="card-visual">02</div><div class="card-meta">CASE STUDY</div><h3>Hospitality rebrand</h3><p>Created a flexible visual language across web and physical touchpoints.</p><button class="small-btn" onclick="openModal('case')">View case study</button></article><article class="card"><div class="card-visual">03</div><div class="card-meta">CASE STUDY</div><h3>AI product site</h3><p>Balanced futuristic visuals with a clear enterprise conversion path.</p><button class="small-btn" onclick="openModal('case')">View case study</button></article></div></section>'''
    elif kind == 'event':
        body += '''<section class="section" id="sessions"><div class="info-grid"><div class="info"><strong>Day 1 · Main stage</strong><span>Keynotes and product stories.</span></div><div class="info"><strong>Day 2 · Workshops</strong><span>Hands-on sessions with working teams.</span></div><div class="info"><strong>Day 3 · Community</strong><span>Small-group conversations and dinner.</span></div></div></section><section class="section" id="register"><button class="btn" onclick="openModal('ticket')">Register now</button></section>'''

    cta_label = {'restaurant':'Reserve a table','ecommerce':'Continue shopping','hotel':'Check availability','realestate':'Request a viewing','saas':'Start free','portfolio':"Let's work together",'education':'Find a course','agency':'Start a project','event':'Get your pass','ai':'Open workspace','dashboard':'Open analytics','business':'Get started','flight':'Search flights','train':'Search trains','bus':'Search buses','travel':'Explore trips','portal':'Open portal','pg':'Find a room','hostel':'Explore rooms','college':'Explore programs','jobs':'Search jobs','healthcare':'Find a doctor','banking':'Open an account','fintech':'Get started','booking':'Start searching','government':'Find a service','news':'Read latest','social':'Explore feed','automotive':'Explore cars','salon':'Book appointment','gym':'View memberships','cinema':'Browse movies'}[kind]

    javascript = '''<script>
const KIND=__JS_KIND__; const BRAND=__JS_BRAND__; const ITEMS=__JS_ITEMS__; const REQUEST=__JS_REQUEST__;
let selectedCategory='all', cart=[], wishlist=new Set();
function toggleMobileNav(){{const e=document.getElementById('mobileNav');e.style.display=e.style.display==='none'?'block':'none'}}
function toast(message){{const old=document.getElementById('toast');if(old)old.remove();const el=document.createElement('div');el.id='toast';el.textContent=message;el.style.cssText='position:fixed;left:50%;bottom:24px;transform:translate(-50%,20px);opacity:0;background:var(--ink);color:var(--bg);padding:12px 18px;border-radius:999px;z-index:100;transition:.25s';document.body.appendChild(el);requestAnimationFrame(()=>{{el.style.opacity='1';el.style.transform='translate(-50%,0)'}});setTimeout(()=>{{el.style.opacity='0';el.style.transform='translate(-50%,20px)';setTimeout(()=>el.remove(),250)}},2200)}}
function openModal(type){{const wrap=document.getElementById('modal'),title=document.getElementById('modalTitle'),body=document.getElementById('modalBody');let html='';
if(type==='hotelBooking'){{title.textContent='Check availability';html=`<form class="form" onsubmit="submitForm(event,'Booking request received. We will confirm availability.')"><div class="form-row"><div><label>Check-in</label><input type="date" required></div><div><label>Check-out</label><input type="date" required></div></div><div class="form-row"><div><label>Guests</label><input type="number" min="1" max="8" value="2" required></div><div><label>Room</label><select><option>Garden King</option><option>Terrace Suite</option><option>Heritage Room</option></select></div></div><div><label>Name</label><input required placeholder="Guest name"></div><div><label>Email</label><input type="email" required placeholder="you@example.com"></div><button class="btn">Check availability</button></form>`}}
else if(type==='reservation'){{title.textContent='Reserve a table';html=`<form class="form" onsubmit="submitForm(event,'Table request received. We will confirm availability.')"><div class="form-row"><div><label>Date</label><input type="date" required></div><div><label>Time</label><select required><option value="">Select</option><option>18:00</option><option>19:30</option><option>21:00</option></select></div></div><div><label>Guests</label><input type="number" min="1" max="12" value="2" required></div><div><label>Name</label><input required placeholder="Your name"></div><div><label>Email</label><input type="email" required placeholder="you@example.com"></div><button class="btn">Confirm reservation</button></form>`}}
else if(type==='checkout'){{title.textContent='Checkout';html=`<form class="form" onsubmit="submitForm(event,'Order placed locally. Connect your payment backend for real checkout.')"><div class="notice">Your local cart is ready. No real payment is processed in this demo.</div><div><label>Delivery address</label><textarea required placeholder="House / street / locality"></textarea></div><div><label>Phone</label><input required></div><button class="btn">Place order</button></form>`}}
else if(type==='enquiry'){{title.textContent='Talk to an agent';html=`<form class="form" onsubmit="submitForm(event,'Enquiry sent. An agent can follow up.')"><div><label>Name</label><input required></div><div><label>Email</label><input type="email" required></div><div><label>Property or location</label><input required placeholder="e.g. Bengaluru, Whitefield"></div><div><label>Message</label><textarea required></textarea></div><button class="btn">Send enquiry</button></form>`}}
else if(type==='signup'){{title.textContent='Create your workspace';html=`<form class="form" onsubmit="submitForm(event,'Account details captured locally.')"><div><label>Name</label><input required></div><div><label>Work email</label><input type="email" required></div><div><label>Password</label><input type="password" minlength="8" required></div><button class="btn">Create account</button></form>`}}
else if(type==='ticket'){{title.textContent='Get your pass';html=`<form class="form" onsubmit="submitForm(event,'Your registration request is confirmed locally.')"><div class="form-row"><div><label>Name</label><input required></div><div><label>Tickets</label><input type="number" min="1" max="8" value="1" required></div></div><div><label>Email</label><input type="email" required></div><button class="btn">Reserve pass</button></form>`}}
else if(type==='case'){{title.textContent='Case study';html=`<div class="notice"><b>Challenge:</b> Make a complex product feel clear.<br><br><b>Approach:</b> Tighten information hierarchy, reduce friction, ship the core journey first.<br><br><b>Outcome:</b> A coherent interface system with measurable conversion opportunities.</div>`}}
else if(type==='settings'){{title.textContent='Settings';html=`<form class="form" onsubmit="submitForm(event,'Settings saved locally.')"><div><label>Theme</label><select><option>System</option><option>Light</option><option>Dark</option></select></div><div><label>Email notifications</label><select><option>Enabled</option><option>Disabled</option></select></div><button class="btn">Save settings</button></form>`}}
else {{title.textContent='Contact';html=`<form class="form" onsubmit="submitForm(event,'Message sent locally.')"><div><label>Name</label><input required></div><div><label>Email</label><input type="email" required></div><div><label>Message</label><textarea required></textarea></div><button class="btn">Send message</button></form>`}}
body.innerHTML=html;wrap.classList.add('open');document.body.classList.add('modal-open')}}
function closeModal(){{document.getElementById('modal').classList.remove('open');document.body.classList.remove('modal-open')}}
document.getElementById('modal').addEventListener('click',e=>{{if(e.target.id==='modal')closeModal()}});
function submitForm(e,msg){{e.preventDefault();closeModal();toast(msg)}}
function primaryAction(){{const map={{restaurant:()=>document.getElementById('menu')?.scrollIntoView({{behavior:'smooth'}}),ecommerce:()=>document.getElementById('shop')?.scrollIntoView({{behavior:'smooth'}}),hotel:()=>document.getElementById('rooms')?.scrollIntoView({{behavior:'smooth'}}),realestate:()=>document.getElementById('buy')?.scrollIntoView({{behavior:'smooth'}}),saas:()=>openModal('signup'),portfolio:()=>document.getElementById('work')?.scrollIntoView({{behavior:'smooth'}}),education:()=>document.getElementById('courses')?.scrollIntoView({{behavior:'smooth'}}),agency:()=>document.getElementById('work')?.scrollIntoView({{behavior:'smooth'}}),event:()=>openModal('ticket'),ai:()=>document.getElementById('workspace')?.scrollIntoView({{behavior:'smooth'}}),dashboard:()=>document.getElementById('analytics')?.scrollIntoView({{behavior:'smooth'}}),business:()=>openModal('contact')}};(map[KIND]||map.business)()}}
function secondaryAction(){{if(KIND==='ecommerce')toggleCart(true);else if(KIND==='restaurant')openModal('reservation');else if(KIND==='hotel')openModal('hotelBooking');else if(KIND==='realestate')openModal('enquiry');else if(KIND==='event')document.getElementById('schedule')?.scrollIntoView({{behavior:'smooth'}});else toast('Action ready in this local build.')}}
function filterCards(cat,btn){{selectedCategory=cat;document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));btn.classList.add('active');renderRestaurant()}}
function renderRestaurant(){{const target=document.getElementById('cards');if(!target)return;const q=(document.getElementById('menuSearch')?.value||'').toLowerCase();const filtered=ITEMS.filter(x=>(selectedCategory==='all'||x[3]===selectedCategory)&&(!q||x[0].toLowerCase().includes(q)||x[1].toLowerCase().includes(q)));target.innerHTML=filtered.map(x=>`<article class="card"><div class="card-visual">${x[0].slice(0,1)}</div><div class="card-meta">${x[3]}</div><h3>${x[0]}</h3><p>${x[1]}</p><div class="card-row"><span class="price">${x[2]}</span><button class="small-btn" onclick="openModal('contact')">Order</button></div></article>`).join('')||'<div class="notice">No dishes match your search.</div>'}}
function renderStore(){{const target=document.getElementById('cards');if(!target)return;const q=(document.getElementById('storeSearch')?.value||'').toLowerCase();const cat=document.getElementById('storeFilter')?.value||'all';const filtered=ITEMS.filter(x=>(cat==='all'||x[3]===cat)&&(!q||x[0].toLowerCase().includes(q)||x[1].toLowerCase().includes(q)));target.innerHTML=filtered.map((x,i)=>`<article class="card"><div class="card-visual">${x[0].slice(0,2).toUpperCase()}</div><div class="card-meta">${x[3]}</div><h3>${x[0]}</h3><p>${x[1]}</p><div class="card-row"><span class="price">${x[2]}</span><div style="display:flex;gap:7px"><button class="small-btn" onclick="toggleWish(${i})">${wishlist.has(i)?'♥':'♡'}</button><button class="small-btn" onclick="addCart(${i})">Add</button></div></div></article>`).join('')||'<div class="notice">No products match your search.</div>'}}
function toggleWish(i){{wishlist.has(i)?wishlist.delete(i):wishlist.add(i);renderStore();toast(wishlist.has(i)?'Added to wishlist':'Removed from wishlist')}}
function addCart(i){{cart.push(i);updateCart();toast(ITEMS[i][0]+' added to cart')}}
function updateCart(){{document.getElementById('cartCount').textContent=cart.length;const list=document.getElementById('cartList');if(!list)return;list.innerHTML=cart.length?cart.map((i,pos)=>`<div class="cart-item"><b>${ITEMS[i][0]}</b><div style="display:flex;justify-content:space-between;align-items:center"><span>${ITEMS[i][2]}</span><button class="small-btn" onclick="cart.splice(${pos},1);updateCart()">Remove</button></div></div>`).join(''):'<div class="notice">Your cart is empty.</div>';const total=cart.reduce((sum,i)=>sum+(parseInt(ITEMS[i][2].replace(/[^0-9]/g,''))||0),0);document.getElementById('cartTotal').textContent='₹'+total.toLocaleString('en-IN')}}
function toggleCart(open){{document.getElementById('cartDrawer')?.classList.toggle('open',open);updateCart()}}
document.getElementById('cartBtn')?.addEventListener('click',()=>toggleCart(true));
function renderGeneric(){{const target=document.getElementById('cards');if(!target)return;target.innerHTML=ITEMS.map(x=>{{let action='Explore';let handler=`toast('opened')`;if(KIND==='education'){{action='Enroll';handler="openModal('signup')"}}else if(KIND==='portfolio'){{action='View case study';handler="openModal('case')"}}else if(KIND==='event'){{action='Add to schedule';handler="toast('Added to schedule')"}}return `<article class="card"><div class="card-visual">${x[2]}</div><div class="card-meta">${x[3]}</div><h3>${x[0]}</h3><p>${x[1]}</p><div class="card-row"><span class="price">${KIND==='education'?x[2]:'Ready'}</span><button class="small-btn" onclick="${handler}">${action}</button></div></article>`}}).join('')}}
function renderHotel(){{const target=document.getElementById('cards');if(!target)return;target.innerHTML=ITEMS.map(x=>`<article class="card"><div class="card-visual">ROOM</div><div class="card-meta">${x[3]}</div><h3>${x[0]}</h3><p>${x[1]}</p><div class="card-row"><span class="price">${x[2]}/night</span><button class="small-btn" onclick="openModal('reservation')">Book</button></div></article>`).join('')}}
function renderProperty(){{const target=document.getElementById('cards');if(!target)return;const q=(document.getElementById('propertySearch')?.value||'').toLowerCase();const cat=document.getElementById('propertyFilter')?.value||'all';const filtered=ITEMS.filter(x=>(cat==='all'||x[3]===cat)&&(!q||x[0].toLowerCase().includes(q)||x[1].toLowerCase().includes(q)||x[3].toLowerCase().includes(q)));target.innerHTML=filtered.map(x=>`<article class="card"><div class="card-visual">HOME</div><div class="card-meta">${x[3]}</div><h3>${x[0]}</h3><p>${x[1]}</p><div class="card-row"><span class="price">${x[2]}</span><button class="small-btn" onclick="openModal('enquiry')">Enquire</button></div></article>`).join('')||'<div class="notice">No properties found.</div>'}}
function renderDashboard(){{const target=document.getElementById('metrics');if(!target)return;target.innerHTML=ITEMS.map(x=>`<div class="metric"><span>${x[0]}</span><strong>${x[1]}</strong><div class="up">${x[2]}</div></div>`).join('')}}
function sendChat(){{const input=document.getElementById('chatInput'),log=document.getElementById('chatLog');const value=input.value.trim();if(!value)return;const safe=value.replace(/[&<>]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[m]));log.innerHTML+=`<div class="bubble me">${safe}</div>`;input.value='';setTimeout(()=>{{log.innerHTML+=`<div class="bubble">I received: “${safe}” — connect this interface to your JARVIS model layer for live answers.</div>`;log.scrollTop=log.scrollHeight}},350)}}
function openCinematicGate(){const gate=document.getElementById('cinematicGate');if(!gate)return;gate.classList.add('open');document.body.classList.remove('gate-lock');setTimeout(()=>gate.classList.add('hide'),1450);toast('Welcome to Farhan & ChatGPT Co. Restaurant');}
if(KIND==='restaurant')renderRestaurant();else if(KIND==='ecommerce'){{renderStore();updateCart()}}else if(KIND==='hotel')renderHotel();else if(KIND==='realestate')renderProperty();else if(KIND==='dashboard')renderDashboard();else if(['saas','portfolio','education','agency','event','business','flight','train','bus','travel','portal','pg','hostel','college','jobs','healthcare','banking','fintech','booking','government','news','social','automotive','salon','gym','cinema'].includes(KIND))renderGeneric();
</script>'''
    javascript = (javascript.replace('__JS_KIND__', json.dumps(kind))
                  .replace('__JS_BRAND__', json.dumps(brand))
                  .replace('__JS_ITEMS__', items_js)
                  .replace('__JS_REQUEST__', request_js).replace('{{', '{').replace('}}', '}'))

    tail = f'''<section class="cta"><h2>Ready to take the next step?</h2><button class="btn" onclick="primaryAction()">{esc(cta_label)} →</button></section></main><footer><div class="foot"><span>© 2026 {brand_h}</span><span>Built locally by JARVIS · Fast, responsive, interactive</span></div></footer>
<div class="modal-wrap" id="modal"><div class="modal"><div class="modal-head"><h3 id="modalTitle">Action</h3><button class="close" onclick="closeModal()">×</button></div><div id="modalBody"></div></div></div>
{javascript}</body></html>'''
    html = shell + body + tail
    (folder / 'index.html').write_text(html, encoding='utf-8')
    return 1
def create_website(request):
    """Fast reliable new-site path: one self-contained HTML file, no AI code-generation loop."""
    kind = _site_kind(request)
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", f"{kind}-{request}").strip("-_")[:70] or "jarvis-website"
    ROOT.mkdir(parents=True, exist_ok=True)
    folder = ROOT / safe_name
    if folder.exists():
        backup(folder)
        shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True, exist_ok=True)

    written = _render_static_site(request, folder)
    ok, issues = validate_project(folder)
    if not ok:
        return False, "Boss, deterministic website validation failed: " + "; ".join(issues[:8])

    launched, runtime_message = launch_project(folder)
    if not launched:
        return False, "Boss, website files ban gaye lekin local run verify nahi hua: " + runtime_message
    return True, f"{folder.name} website bana diya ({written} file). {runtime_message}"


def edit_latest(request):
    folder = latest_project()
    if not folder:
        return False, "Boss, koi existing Jarvis website nahi mila."
    index, css, js = read_project(folder)
    paths = ([index] if index else []) + css + js
    if (folder / "package.json").exists():
        paths.append(folder / "package.json")
    current = {}
    for path in paths:
        try:
            current[str(path.relative_to(folder)).replace("\\", "/")] = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    # Large visual redesigns should never depend on a long LLM full-project rewrite.
    # Rebuild the deterministic site when the request asks for cinematic/glass/3D entrance work.
    lower_request = str(request or '').lower()
    large_visual = any(k in lower_request for k in (
        'black glass', 'glass gate', 'glass portal', '3d glass', 'cinematic entrance',
        'welcome gate', 'gate open', 'full redesign', 'complete redesign', 'rebuild the website'
    ))
    if large_visual and _site_kind(request) == 'restaurant':
        backup(folder)
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True, exist_ok=True)
        written = _render_static_site(request, folder)
        ok, issues = validate_project(folder)
        if not ok:
            return False, "Boss, cinematic rebuild validation failed: " + "; ".join(issues[:8])
        launched, runtime = launch_project(folder)
        if not launched:
            return False, "Boss, cinematic rebuild files ban gaye lekin local run verify nahi hua: " + runtime
        return True, f"Cinematic restaurant redesign complete. {runtime}"

    system = CAPABILITIES_PROMPT + "\n\nYou are EDITING an existing website. Apply the user's request while preserving everything else that already works."
    prompt = f"""
USER REQUEST:
{request}

CURRENT PROJECT:
{_dump_files(current)}

Return the complete resulting project using PROJECT_NAME + ### FILE blocks.
"""
    try:
        _, files = ai_files(system, prompt, NUM_PREDICT_EDIT)
    except Exception as error:
        return False, f"Boss, website edit output invalid: {error}"
    backup(folder)
    _write_files(folder, files)
    ok, issues = validate_project(folder)
    if not ok:
        return False, "Boss, edit ke baad validation failed: " + "; ".join(issues[:8])
    launched, runtime = launch_project(folder)
    if not launched:
        return False, "Boss, edit ho gaya lekin local run verify nahi hua: " + runtime
    return True, f"Website update complete. {runtime}"


def build_website(request):
    text = str(request or "").lower()
    edit_words = [
        "edit", "change", "modify", "update", "improve", "fix", "add", "remove", "replace",
        "kar do", "change karo", "add karo", "fix karo", "improve karo", "responsive karo",
        "professional karo", "redesign", "revamp", "rebuild", "make it", "animation",
    ]
    site_words = [
        "website", "webpage", "web page", "portfolio", "site", "landing page", "web app",
        "webapp", "ecommerce", "e-commerce", "online store", "dashboard", "navbar", "hero",
        "contact section", "pricing", "checkout", "booking",
    ]
    if any(x in text for x in edit_words) and any(x in text for x in site_words):
        return edit_latest(request)
    return create_website(request)
