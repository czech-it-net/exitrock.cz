#! /bin/env python

import argparse
import re
import urllib.request
from datetime import date
from os import environ
from pprint import pprint

from _collections import defaultdict
from icalendar import Calendar

DEFAULT_MARK_START = "<!-- Calendar start -->"
DEFAULT_MARK_END = "<!-- Calendar end -->"


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calendar",
        description=f"Replace content between start and end marks, output to stdout",
    )
    parser.add_argument("filename", help="Source filename")
    parser.add_argument(
        "--ics_url",
        help="Source calendar url (ICAL) [CALENDAR_URL env var]",
        default=environ.get("CALENDAR_URL"),
    )
    parser.add_argument("--start", help=f"Start mark [{DEFAULT_MARK_START}]", default=DEFAULT_MARK_START)
    parser.add_argument("--end", help=f"End mark [{DEFAULT_MARK_END}]", default=DEFAULT_MARK_END)
    return parser


def load_calendar(url: str) -> Calendar | None:
    calendar = None

    with urllib.request.urlopen(url, timeout=3) as resp:
        calendar = Calendar.from_ical(resp.read())

    return calendar


def pull_events(calendar: Calendar | None, future_only: bool = True) -> dict[date, list]:
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
    content = ""

    with open(filename) as fd:
        content = fd.read()

    calendar_content = "<table id='calendar'>\n"
    if events:
        for date, summary_list in events.items():
            for summary in summary_list:
                # Remove [1], [2],.. used to sort events
                summary = re.sub(r"\[\d\] ", "", summary)
                calendar_content += (
                    f"<tr><td class='date'>{date.strftime('%-d.%-m.%Y')}</td><td>{summary}</td></tr>\n"
                )
    else:
        calendar_content += "<tr><td>Zatím žádné akce</td></tr>\n"

    calendar_content += "</table>"

    output = re.sub(
        f"({mark_start}).*({mark_end})", r"\1\n" + calendar_content + r"\n\2\n", content, flags=re.DOTALL
    )
    return output


def main():
    args = get_parser().parse_args()
    calendar = load_calendar(args.ics_url)
    events = pull_events(calendar, future_only=True)
    print(replace_content(args.filename, events, args.start, args.end))


if __name__ == "__main__":
    main()
