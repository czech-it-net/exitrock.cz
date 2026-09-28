#! /bin/env python
"""Get calendar from ICAL URL and update content between marks in given file."""

import argparse
import re
import urllib.request
from collections import defaultdict
from datetime import date
from os import environ
from pathlib import Path

from icalendar import Calendar, Component

DEFAULT_MARK_START = "<!-- Calendar start -->"
DEFAULT_MARK_END = "<!-- Calendar end -->"
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = (REPO_ROOT / "src").resolve()
ALLOWED_ICS_URL_PREFIXES = ("https://calendar.google.com/calendar/ical/",)


def validate_filename(filename: str) -> Path:
    """Resolve a filename and ensure it stays inside the repository src subtree."""

    path = Path(filename)
    if not path.is_absolute():
        path = REPO_ROOT / path
    path = path.resolve()

    if not path.is_relative_to(SRC_ROOT):
        raise ValueError("Filename must point to a file inside the repository src directory")

    return path


def validate_ics_url(url: str | None) -> str:
    """Ensure the calendar URL uses an approved Google Calendar iCal prefix."""

    if url is None or not url.startswith(ALLOWED_ICS_URL_PREFIXES):
        prefixes = ", ".join(ALLOWED_ICS_URL_PREFIXES)
        raise ValueError(f"Calendar URL must start with one of: {prefixes}")

    return url


class CalendarRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Only follow redirects to approved calendar URLs."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith(ALLOWED_ICS_URL_PREFIXES):
            raise ValueError("Calendar URL redirected to an unsupported address")

        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get_parser() -> argparse.ArgumentParser:
    """CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="calendar",
        description="Replace content between start and end marks, output to stdout",
    )
    parser.add_argument("filename", help="Source filename")
    parser.add_argument(
        "--ics-url",
        help="Source calendar url (ICAL) [CALENDAR_URL env var]",
        default=environ.get("CALENDAR_URL"),
    )
    parser.add_argument(
        "--start", help=f"Start mark [{DEFAULT_MARK_START}]", default=DEFAULT_MARK_START
    )
    parser.add_argument("--end", help=f"End mark [{DEFAULT_MARK_END}]", default=DEFAULT_MARK_END)
    return parser


def load_calendar(url: str) -> Component | None:
    """Load calendar from given URL."""

    calendar = None

    opener = urllib.request.build_opener(CalendarRedirectHandler())
    with opener.open(url, timeout=3) as resp:
        calendar = Calendar.from_ical(resp.read())

    return calendar


def pull_events(calendar: Component | None, future_only: bool = True) -> dict[date, list]:
    """Pull events from calendar.

    Filter and alter the events as needed.

    Args:
        calendar: Calendar component
        future_only: Whether to include only future events

    Returns:
        Dictionary of events keyed by date
    """
    if calendar is None:
        return {}

    events = defaultdict(list)
    today = date.today()

    for event in calendar.walk("VEVENT"):
        dt_start = event.decoded("DTSTART")

        if future_only and dt_start < today:
            continue

        summary = event.decoded("SUMMARY", "").strip()
        summary = re.sub("Exit - |Exit ", "", summary)  # Strip unnecessary info

        if not summary:
            continue

        if "?" in summary:  # Don't add tentative
            continue

        description = event.decoded("DESCRIPTION", "").strip()

        if "[noweb]" in description:  # Don't add events marked as "no web"
            continue

        events[dt_start].append(summary)
        events[dt_start].sort()

    events = dict(sorted(events.items()))
    return events


def replace_content(filename: str, events: dict[date, list], mark_start: str, mark_end: str) -> str:
    """Replace content between start and end marks in given file.

    Args:
        filename: Source filename
        events: Events to insert
        mark_start: Start mark
        mark_end: End mark

    Returns:
        Updated file content
    """
    content = ""

    with open(filename, encoding="utf-8") as fd:
        content = fd.read()

    calendar_content: list[str] = ["<table id='calendar'>"]
    if events:
        for event_date, summary_list in events.items():
            for summary in summary_list:
                # Remove [1], [2],.. used to sort events
                summary = re.sub(r"\[\d\] ", "", summary)
                calendar_content.append(
                    f"<tr><td class='date'>{event_date.strftime('%-d.%-m.%Y')}</td>"
                    f"<td>{summary}</td></tr>"
                )
    else:
        calendar_content.append("<tr><td>Zatím žádné akce</td></tr>")

    calendar_content.append("</table>")
    calendar_content_str = "\n".join(calendar_content)

    output = re.sub(
        f"({mark_start}).*({mark_end})",
        r"\1\n" + calendar_content_str + r"\n\2\n",
        content,
        flags=re.DOTALL,
    )
    return output


def main() -> None:
    """Load calendar, pull events, replace content and output to stdout."""

    parser = get_parser()
    args = parser.parse_args()
    try:
        filename = validate_filename(args.filename)
        ics_url = validate_ics_url(args.ics_url)
    except ValueError as error:
        parser.error(str(error))

    calendar = load_calendar(ics_url)
    events = pull_events(calendar, future_only=True)
    print(replace_content(str(filename), events, args.start, args.end))


if __name__ == "__main__":
    main()
