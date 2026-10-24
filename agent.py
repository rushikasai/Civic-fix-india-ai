"""CivicFix India AI: ASI:One interactive civic complaint cards."""
import json
import logging
import os
import re
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage, ChatAcknowledgement, TextContent,
    MetadataContent, chat_protocol_spec,
)

ISSUES = {
    "potholes": ("Potholes & damaged roads", "Municipal road engineering division or relevant road owner", "Road inspection and repair"),
    "waterlogging": ("Waterlogging & flooding", "Municipal storm-water drainage or road authority", "Drainage inspection and clearance"),
    "cracks": ("Cracks, rutting & road settlement", "Road-owning engineering or maintenance authority", "Road safety inspection and repairs"),
    "edges": ("Broken road edges & shoulders", "Road-owning engineering or maintenance authority", "Inspect and repair damaged road edges"),
    "surface": ("Peeling asphalt & slippery roads", "Road-owning engineering or maintenance authority", "Inspect and restore road surface"),
    "garbage": ("Garbage & construction debris", "Municipal sanitation or solid-waste department", "Remove waste and clean the area"),
    "encroachment": ("Footpath obstruction & encroachment", "Municipal ward office or competent enforcement authority", "Inspect obstruction and take lawful action"),
    "signage": ("Missing road signs & markings", "Road-owning authority or traffic engineering division", "Inspect and restore signs or markings"),
    "streetlights": ("Broken streetlights", "Municipal electrical or streetlight department", "Inspect and repair streetlights"),
    "drainage": ("Blocked drains & damaged drain covers", "Municipal drainage or storm-water department", "Inspect and clear drains or repair covers"),
    "overloading": ("Suspected overloaded commercial vehicles", "State transport or motor vehicle enforcement authority", "Assess the report through authorised enforcement"),
    "other": ("Other road safety or civic issue", "Relevant local authority (to be determined)", "Inspect and take appropriate action"),
}

REQUIRED = ("state", "district", "city", "locality", "description")
OPTIONAL = ("impact", "duration", "citizen_name")

agent = Agent(
    name="civicfix_india_interactive",
    seed=os.getenv("AGENT_SEED", "civicfix-development-seed-replace-before-production"),
    mailbox=True,
)
chat = Protocol(spec=chat_protocol_spec)


def outgoing(text, kind=None, payload=None, terminal=False):
    content = [TextContent(type="text", text=text)]
    if kind is not None:
        metadata = {
            "card_protocol_version": "1",
            "requires_card_interaction": "false" if terminal else "true",
            "card_kind": kind,
            "card_payload": json.dumps(payload, ensure_ascii=False),
            "preferred_drawer_width_px": "600",
        }
        if terminal:
            metadata["is_terminal"] = "true"
        content.append(MetadataContent(type="metadata", metadata=metadata))
    return ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(), content=content)


def welcome_card():
    return {"root": {"type": "section", "title": "CivicFix India AI",
        "subtitle": "Your voice. Better neighbourhoods.", "children": [
            {"type": "badge", "label": "SMART CIVIC ASSISTANT", "variant": "info"},
            {"type": "heading", "value": "Let's improve your neighbourhood", "level": 2},
            {"type": "text", "value": "Choose a civic problem, enter its location, review the details and generate a ready-to-copy complaint letter."},
            {"type": "divider"},
            {"type": "heading", "value": "Choose a problem", "level": 3},
            {"type": "choice_grid", "name": "category", "choices": [
                {"value": key, "label": value[0]} for key, value in ISSUES.items()
            ]},
            {"type": "button", "label": "Continue", "primary": True,
             "action": {"selection": {"action": "choose_issue"}}},
        ]}}


def issue_carousel():
    return {"title": "Explore civic problems", "subtitle": "Select a category to start a report", "items": [
        {"id": key, "title": info[0], "subtitle": info[2],
         "badges": [{"label": "Civic issue", "variant": "info"}],
         "primary_cta": {"label": "Report issue", "selection": {"action": "choose_issue", "category": key}}}
        for key, info in ISSUES.items()
    ]}


def report_form(category):
    return {"title": "Report: " + ISSUES[category][0], "fields": [
        {"name": "state", "kind": "text", "label": "State / Union Territory", "required": True},
        {"name": "district", "kind": "text", "label": "District", "required": True},
        {"name": "city", "kind": "text", "label": "City / town / village", "required": True},
        {"name": "locality", "kind": "text", "label": "Road / locality / landmark", "required": True},
        {"name": "description", "kind": "text", "label": "Describe the problem", "required": True},
        {"name": "impact", "kind": "text", "label": "Reported impact (optional)"},
        {"name": "duration", "kind": "text", "label": "How long has this existed? (optional)"},
        {"name": "citizen_name", "kind": "text", "label": "Your name (optional)"},
    ], "submit_cta": {"label": "Review complaint", "selection": {"action": "review_issue", "category": category}}}


def place(data):
    return ", ".join(data[k] for k in ("locality", "city", "district", "state"))


def review_card(data):
    issue, office, _ = ISSUES[data["category"]]
    rows = [
        {"label": "Issue", "value": issue},
        {"label": "Location", "value": place(data)},
        {"label": "Description", "value": data["description"]},
        {"label": "Likely office (unverified)", "value": office},
    ]
    for key, label in (("impact", "Reported impact"), ("duration", "Duration")):
        if data.get(key):
            rows.append({"label": label, "value": data[key]})
    return {"title": "Review your civic complaint", "summary_rows": rows,
        "approve_cta": {"label": "Generate complaint letter", "primary": True,
                        "selection": {"action": "generate_letter"}},
        "reject_cta": {"label": "Edit details", "selection": {"action": "edit_details"}}}


def draft_letter(data):
    issue, office, action = ISSUES[data["category"]]
    extra = ""
    if data.get("impact"):
        extra += "\nReported impact: " + data["impact"]
    if data.get("duration"):
        extra += "\nReported duration: " + data["duration"]
    name = data.get("citizen_name") or "[Citizen name, if desired]"
    return (
        "CIVICFIX INDIA AI - CIVIC COMPLAINT\n\n"
        f"To,\nThe {office}\n(Provisional office type; verify jurisdiction)\n\n"
        f"Subject: Request for inspection and resolution of {issue.lower()} at {place(data)}\n\n"
        "Respected Sir/Madam,\n\n"
        f"I wish to report a civic infrastructure problem at {place(data)}.\n\n"
        f"Issue category: {issue}\nLocation: {place(data)}\n"
        f"Description: {data['description']}{extra}\n\n"
        f"Requested action: {action}. I kindly request the competent authority "
        "to inspect the location and take appropriate corrective action. "
        "Please acknowledge this complaint and advise on the follow-up procedure.\n\n"
        f"Thank you for your attention.\n\nYours faithfully,\n{name}"
    )


async def generate_letter(data, ctx):
    draft = draft_letter(data)
    api_key = os.getenv("ASI1_API_KEY") or os.getenv("ASI_ONE_API_KEY") or os.getenv("ASI_API_KEY")
    if not api_key:
        return draft
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=os.getenv("ASI1_BASE_URL", "https://api.asi1.ai/v1").rstrip("/"),
            timeout=35.0,
        )
        result = await client.chat.completions.create(
            model=os.getenv("ASI_MODEL", "asi1"),
            messages=[
                {"role": "system", "content": (
                    "You are CivicFix India AI. Polish the supplied Indian civic complaint letter "
                    "into clear, respectful English. Preserve every reported fact. "
                    "Do not invent technical causes, evidence, official names, contacts, "
                    "jurisdiction verification, complaint IDs or submission status. "
                    "Return only the complete letter."
                )},
                {"role": "user", "content": draft},
            ],
            temperature=0.2,
            max_tokens=1300,
        )
        answer = result.choices[0].message.content
        return answer.strip() if isinstance(answer, str) and answer.strip() else draft
    except Exception:
        ctx.logger.exception("ASI1 letter generation unavailable; using safe template")
        return draft


def parse_selection(raw, state):
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    except (ValueError, TypeError):
        pass
    low = raw.lower().strip()
    # The ASI:One planner can forward a card click in natural-language prose.
    category = next((key for key in ISSUES if re.search(r"\b" + re.escape(key) + r"\b", low)), None)
    if not category:
        category = next((key for key, info in ISSUES.items() if info[0].lower() in low), None)
    if "review_issue" in low or "review complaint" in low:
        action = "review_issue"
    elif "generate_letter" in low or "generate complaint" in low or "confirm" in low:
        action = "generate_letter"
    elif "edit_details" in low or "edit details" in low:
        action = "edit_details"
    elif "restart" in low or "new complaint" in low:
        action = "restart"
    elif "show_categories" in low or "browse categories" in low:
        action = "show_categories"
    elif "choose_issue" in low or "report issue" in low or category:
        action = "choose_issue"
    else:
        action = None
    return {"action": action, "category": category}


@chat.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    try:
        await ctx.send(sender, ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
    except Exception:
        ctx.logger.warning("Acknowledgement failed")

    raw = (msg.text() or "").strip()
    state = ctx.storage.get(sender) or {}
    if not raw or raw.lower() in {"hi", "hello", "start", "menu", "help"}:
        ctx.storage.set(sender, {})
        await ctx.send(sender, outgoing(
            "Welcome to CivicFix India AI! Choose a civic issue below.", "custom", welcome_card()))
        return

    selected = parse_selection(raw, state)
    action = selected.get("action")

    if action == "restart":
        ctx.storage.set(sender, {})
        await ctx.send(sender, outgoing("Let's prepare another complaint.", "custom", welcome_card()))
        return

    if action == "show_categories":
        await ctx.send(sender, outgoing("Browse civic issues below.", "carousel", issue_carousel()))
        return

    if action == "choose_issue":
        category = selected.get("category")
        if category not in ISSUES:
            await ctx.send(sender, outgoing("Please select a category.", "custom", welcome_card()))
            return
        ctx.storage.set(sender, {"category": category})
        await ctx.send(sender, outgoing("Now enter the location and problem details.", "form", report_form(category)))
        return

    if action == "review_issue":
        category = selected.get("category") or state.get("category")
        if category not in ISSUES:
            await ctx.send(sender, outgoing("Choose an issue first.", "custom", welcome_card()))
            return
        data = {"category": category}
        for key in REQUIRED + OPTIONAL:
            data[key] = str(selected.get(key) or "").strip()[:1500]
        missing = [key for key in REQUIRED if not data[key]]
        if missing:
            await ctx.send(sender, outgoing(
                "Please complete these fields: " + ", ".join(missing), "form", report_form(category)))
            return
        ctx.storage.set(sender, data)
        await ctx.send(sender, outgoing("Check the details before generating the letter.", "review", review_card(data)))
        return

    if action == "edit_details":
        category = state.get("category")
        if category in ISSUES:
            await ctx.send(sender, outgoing("Update the complaint details.", "form", report_form(category)))
        else:
            await ctx.send(sender, outgoing("Choose an issue first.", "custom", welcome_card()))
        return

    if action == "generate_letter":
        if state.get("category") not in ISSUES or any(not state.get(key) for key in REQUIRED):
            await ctx.send(sender, outgoing("Complete your report first.", "custom", welcome_card()))
            return
        letter = await generate_letter(state, ctx)
        issue, office, _ = ISSUES[state["category"]]
        detail = {"title": "Complaint draft ready", "summary_rows": [
            {"label": "Issue", "value": issue},
            {"label": "Location", "value": place(state)},
            {"label": "Likely office (unverified)", "value": office},
            {"label": "Status", "value": "Draft only - NOT submitted"},
        ], "ctas": [
            {"label": "New complaint", "primary": True, "selection": {"action": "restart"}},
            {"label": "Browse issue categories", "selection": {"action": "show_categories"}},
        ]}
        await ctx.send(sender, outgoing(
            "YOUR COMPLAINT LETTER\n\n" + letter + "\n\n"
            "STATUS: Draft only; no complaint has been submitted. "
            "Verify jurisdiction and find the official submission channel through the relevant "
            "local government website. CPGRAMS may be suitable for eligible grievances: "
            "https://pgportal.gov.in/\n\n"
            "If the issue presents immediate danger, stay away and alert the appropriate authority.",
            "detail", detail))
        return

    await ctx.send(sender, outgoing(
        "Please use the issue selection card, or send START.", "custom", welcome_card()))


@chat.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.debug("Acknowledgement received")


agent.include(chat, publish_manifest=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Starting CivicFix India AI with ASI:One Interactive Cards...")
    agent.run()