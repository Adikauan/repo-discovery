from zoneinfo import available_timezones


class ListScheduleTimezones:
    def execute(self) -> list[str]:
        return sorted(available_timezones())
