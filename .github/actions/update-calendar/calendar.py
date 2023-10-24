#! /bin/env python

import argparse
from datetime import date
from os import environ
from pprint import pprint
import re
import urllib.request

from icalendar import Calendar


DEFAULT_MARK_START = "<!-- Calendar start -->"
DEFAULT_MARK_END = "<!-- Calendar end -->"


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calendar",
        description=f"Replace content between start and end marks",
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


def pull_events(calendar: Calendar | None, future_only: bool = True) -> dict[date, str]:
    if calendar is None:
        return {}

    events = {}
    today = date.today()

    for event in calendar.walk("VEVENT"):
        dt_start = event.decoded("DTSTART")

        if future_only and dt_start < today:
            continue

        summary = event.decoded("SUMMARY").decode()
        summary = re.sub("Exit - |Exit ", "", summary)  # Strip unnecessary info

        events[dt_start] = summary

    events = dict(sorted(events.items()))
    return events


def replace_content(filename: str, events: dict[date, str], mark_start: str, mark_end: str) -> str:
    content = ""

    with open(filename) as fd:
        content = fd.read()

    calendar_content = (
        "<table id='calendar'>\n"
        + "\n".join(
            f"<tr><td class='date'>{date.strftime('%-d.%-m.%Y')}</td><td>{summary}</td></tr>"
            for date, summary in events.items()
        )
        + "\n</table>"
    )

    output = re.sub(
        f"({mark_start}).*({mark_end})", r"\1\n" + calendar_content + r"\n\2\n", content, flags=re.DOTALL
    )
    return output


def main():
    args = get_parser().parse_args()
    calendar = load_calendar(args.ics_url)
    events = pull_events(calendar, future_only=True)
    print(events)
    print(replace_content(args.filename, events, args.start, args.end))


if __name__ == "__main__":
    main()
