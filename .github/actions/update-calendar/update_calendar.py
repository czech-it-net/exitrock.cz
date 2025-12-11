#! /bin/env python
"""Get calendar from ICAL URL and update content between marks in given file."""

import argparse
import re
import urllib.request
from collections import defaultdict
from datetime import date
from os import environ

from icalendar import Calendar, Component

DEFAULT_MARK_START = "<!-- Calendar start -->"
DEFAULT_MARK_END = "<!-- Calendar end -->"


def get_parser() -> argparse.ArgumentParser:
    """CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="calendar",
        description="Replace content between start and end marks, output to stdout",
    )
    parser.add_argument("filename", help="Source filename")
    parser.add_argument(
        "--ics_url",
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

    with urllib.request.urlopen(url, timeout=3) as resp:
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

        summary = event.decoded("SUMMARY").decode().strip()
        summary = re.sub("Exit - |Exit ", "", summary)  # Strip unnecessary info

        if "?" in summary:  # Don't add tentative
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

    args = get_parser().parse_args()
    calendar = load_calendar(args.ics_url)
    events = pull_events(calendar, future_only=True)
    print(replace_content(args.filename, events, args.start, args.end))


if __name__ == "__main__":
    main()
