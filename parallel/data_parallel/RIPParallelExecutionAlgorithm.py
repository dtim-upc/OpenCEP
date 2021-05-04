from abc import ABC
from parallel.data_parallel.DataParallelExecutionAlgorithm import DataParallelExecutionAlgorithm, \
    DataParallelExecutionUnit
from base.Pattern import Pattern
from evaluation.EvaluationMechanismFactory import \
    EvaluationMechanismParameters
from base.DataFormatter import DataFormatter
from base.PatternMatch import *
from stream.Stream import *
from datetime import datetime, timedelta


class RIPParallelExecutionAlgorithm(DataParallelExecutionAlgorithm, ABC):
    """
    Implements the RIP algorithm.
    """
    def __init__(self, units_number, patterns: Pattern or List[Pattern],
                 eval_mechanism_params: EvaluationMechanismParameters,
                 platform, multiple: timedelta):
        super().__init__(units_number, patterns, eval_mechanism_params, platform)
        self.interval = multiple
        if isinstance(patterns, list):
            self.time_delta = max(pattern.window for pattern in patterns)  # check willingness
        else:
            self.time_delta = patterns.window
        self.filters = []
        self.start_time = None

    def eval(self, events: InputStream, matches: OutputStream, data_formatter: DataFormatter):
        """
        Activates the actual parallel algorithm.
        """
        self._check_legal_input(events, data_formatter)
        execution_units = list()
        self.filters = [RIPFilterStream(interval=self.interval,
                                        time_delta=self.time_delta,
                                        matches=matches,
                                        data_formatter=data_formatter) for _ in range(self.units_number)]

        for unit_id, evaluation_manager in enumerate(self.evaluation_managers):
            execution_unit = DataParallelExecutionUnit(self.platform,
                                                       unit_id,
                                                       evaluation_manager,
                                                       self.filters[unit_id],
                                                       data_formatter)
            execution_unit.start()
            execution_units.append(execution_unit)

        for raw_event in events:
            if not self.start_time:
                event = Event(raw_event, data_formatter)
                self.start_time = event.timestamp
            for unit_id in self._classifier(raw_event, data_formatter):
                execution_units[unit_id].add_event(raw_event)

        for execution_unit in execution_units:
            execution_unit.wait()

    # todo check about time_deltas the span over a few intervals - 3/4/5...
    def _classifier(self, raw_event: str, data_formatter: DataFormatter):
        event = Event(raw_event, data_formatter)
        event_time = event.timestamp
        unit_id1 = self._calcUnitNumber(event_time)
        unit_id2 = self._calcUnitNumber(event_time, self.time_delta)

        if unit_id1 != unit_id2:
            if event_time - self.start_time > self.interval:  # updates start_time when needed
                self.filters[unit_id2].update_start_time(event_time)
            return [unit_id1, unit_id2]
        return unit_id1

    def _calcUnitNumber(self, cur_time, time_delta=timedelta(seconds=0)):
        event_time = cur_time + time_delta
        if self.start_time is None:
            raise Exception("start_time in RIP is not initialized")
        diff_time = event_time - self.start_time
        unit_id = int((diff_time/self.interval) % self.units_number)
        return unit_id  # result is zero based


class RIPFilterStream(Stream):
    def __init__(self, interval: timedelta, time_delta: timedelta,
                 matches: OutputStream, data_formatter: DataFormatter):
        super().__init__()
        self.interval = interval
        self.time_delta = time_delta
        self.data_formatter = data_formatter
        self.matches = matches
        self.start_time = None

    def update_start_time(self, start_time: datetime):
        self.start_time = start_time

    def add_item(self, item: object):
        if self.skip_item(item):
            return
        else:
            self.matches.add_item(item)

    def skip_item(self, item):
        if not self.start_time:
            raise Exception("start_time is not initialized")
        parsed_item = self.data_formatter.parse_event(item)
        item_time = self.data_formatter.get_event_timestamp(parsed_item)
        window_start = self.start_time + self.time_delta
        window_end = window_start + self.interval
        return not (window_start < item_time < window_end)
