
"""
 Data parallel algoritms
"""
from abc import ABC
from stream.Stream import InputStream, OutputStream
from stream.DataParallelStream import *
from stream.Stream import Stream
import math

from typing import List
from base.Pattern import Pattern
from evaluation.EvaluationMechanismFactory import EvaluationMechanismParameters, EvaluationMechanismFactory
from base.DataFormatter import DataFormatter
from queue import Queue
from datetime import timedelta, datetime
from base.Event import Event
from datetime import datetime
import threading

from base.Event import Event
from base.PatternMatch import *

def _make_tree(patterns: Pattern or List[Pattern],
               eval_mechanism_params: EvaluationMechanismParameters):
    if isinstance(patterns, Pattern):
        patterns = [patterns]
    if len(patterns) > 1:
        tree = EvaluationMechanismFactory.build_multi_pattern_eval_mechanism(
            eval_mechanism_params,
            patterns)
    else:
        tree = EvaluationMechanismFactory.build_single_pattern_eval_mechanism(
            eval_mechanism_params,
            patterns[0])

    return tree




class DataParallelAlgorithm(ABC):
    """
        An abstract base class for all  data parallel evaluation algorithms.
        """

    def __init__(self, numthreads, patterns: Pattern or List[Pattern],
                 eval_mechanism_params: EvaluationMechanismParameters, platform):
        self._platform = platform
        self._numThreads = numthreads
        self._threads = []
        self._trees = []
        self._events = None
        self._events_list = []
        self._stream_thread = platform.create_parallel_execution_unit(unit_id=self._numThreads - 1, callback_function=self._stream_divide)
        self._matches = None
        self._patterns = patterns

        for i in range(0, self._numThreads - 1):
            self._trees.append(_make_tree(patterns, eval_mechanism_params))
            self._events_list.append(Stream())

        """ 
        self._matches_list = []

        for i in range(numthreads):
            self._matches_list.append(Stream())
        """

    def eval_algorithm(self, events: InputStream, matches: OutputStream, data_formatter: DataFormatter):
        self._events = events
        self._data_formatter = data_formatter
        self._matches = matches
        self._stream_thread.start()
        for i in range(self._numThreads - 1):
            t = self._platform.create_parallel_execution_unit(unit_id=i, callback_function=self._eval_thread, thread_id=i, data_formatter=data_formatter)
            self._threads.append(t)
            t.start()

    def get_structure_summary(self):
        return self._trees[0].get_structure_summary()

class Algorithm1(DataParallelAlgorithm):
    def __init__(self, threadsNum, patterns: Pattern or List[Pattern],
                 eval_mechanism_params: EvaluationMechanismParameters, platform, key: str):
        super().__init__(threadsNum, patterns, eval_mechanism_params, platform)
        self.key = key

    def eval_algorithm(self, events: InputStream, matches: OutputStream, data_formatter: DataFormatter):
        event = Event(events.first(),data_formatter)
        key_val = event.payload[self.key]
        if not isinstance(key_val, (int, float)):
            raise Exception("key %s has no numeric value" % (self.key,))
        super().eval_algorithm(events, matches, data_formatter)

        for t in self._threads:
            t.wait()

        self._matches.close()


    def _stream_divide(self):
        file = open("C:/Users/tomer/Desktop/CEPproject/OpenCEP/test/strems.txt", 'w')

        for event_raw in self._events:
            event = Event(event_raw, self._data_formatter)
            index = int(event.payload[self.key] % (self._numThreads - 1))
            self._events_list[index].add_item(event_raw)

            file.write("%s " %index)
            file.write("%s\n" %event.payload[self.key])

        for stream in self._events_list:
            stream.close()
    def _eval_thread(self, thread_id: int, data_formatter: DataFormatter):

        self._trees[thread_id].eval(self._events_list[thread_id], self._matches, data_formatter, False)


class Algorithm2(DataParallelAlgorithm):

    def __init__(self, numthreads, patterns: Pattern or List[Pattern],
                 eval_mechanism_params: EvaluationMechanismParameters, platform):

        super().__init__(numthreads, patterns, eval_mechanism_params, platform)
        self._eval_mechanism_params = eval_mechanism_params
        self._matches_handler = Stream()
        self._init_time = None

        if isinstance(patterns, Pattern):
            patterns = [patterns]
        max_window = patterns[0].window
        for k in range(1, len(patterns)):
            if patterns[k].window > max_window:
                max_window = patterns[k].window
        self.time_slot = 3 * max_window
        self.shared_time = max_window
        self.start_list = [Stream() for j in range(self._numThreads - 1)]
        self.start_queue = Queue()
        self.streams_queue = Queue()
        self.thread_pool = Queue()
        self.base_year = 0

        for i in range(numthreads - 1):
            self.thread_pool.put(i)

        self._mutex = Queue()

    def _stream_divide(self):
        count1 = 0
        count_total = 0
        count_shared = 0
        count_used = 0
        try:
            event_raw = self._events.get_item()
            cur_event = Event(event_raw, self._data_formatter)
        except StopIteration:
            raise Exception("Stream has no data")

        curr_time = start_time = cur_event.timestamp
        end_time = start_time + self.time_slot
        stream_s = Stream()
        check_data = True

        while check_data:
            count_shared += stream_s.count()
            stream = stream_s.duplicate()
            stream_s = Stream()
            while curr_time <= end_time and check_data:
                stream.add_item(event_raw)
                if curr_time >= end_time - self.shared_time:
                    stream_s.add_item(event_raw)
                try:
                    event_raw = self._events.get_item()
                    cur_event = Event(event_raw, self._data_formatter)
                    curr_time = cur_event.timestamp
                except:
                    check_data = False
            stream.close()
            if stream.count() > 0:
                self.streams_queue.put_nowait(stream.duplicate())
                self.start_queue.put_nowait(start_time)
            start_time = end_time - self.shared_time
            end_time = start_time + self.time_slot
            ##########
            while not self.thread_pool.empty() and not self.streams_queue.empty():
                id = self.thread_pool.get()
                self._events_list[id] = self.streams_queue.get_nowait().duplicate()  # stream of input data
                self.start_list[id].add_item(self.start_queue.get_nowait())

        while not self.streams_queue.empty():
            id = self.thread_pool.get()
            self._events_list[id] = self.streams_queue.get_nowait().duplicate()  # stream of input data
            self.start_list[id].add_item(self.start_queue.get_nowait())

        # finished to divide the data
        for i in range(0, self._numThreads - 1):
            self.start_list[i].close()

        while self._mutex.qsize() < self._numThreads-1:
            pass


        self._matches_handler.close()


    def _eval_thread(self, thread_id: int, data_formatter: DataFormatter):

        for start_time in self.start_list[thread_id]:
            shared_time1 = start_time + self.shared_time
            shared_time2 = start_time + self.time_slot - self.shared_time
            #print(start_time, shared_time1, shared_time2)
            self._trees[thread_id].eval_parallel(self._events_list[thread_id], self._matches_handler, data_formatter, shared_time1, shared_time2)
            self._trees[thread_id] = _make_tree(self._patterns, self._eval_mechanism_params)
            self.thread_pool.put(thread_id)
        self._mutex.put(1)


    def _match_to_output(self):
        duplicated = set()
        for match, flag in self._matches_handler:
            if flag:
                if match in duplicated:
                    duplicated.remove(match)
                else:
                    self._matches.add_item(match)
                    duplicated.add(match)
            else:
                self._matches.add_item(match)


    def eval_algorithm(self, events: InputStream, matches: OutputStream, data_formatter: DataFormatter):

        super().eval_algorithm(events, matches, data_formatter)
        # for t in self._threads:
        #     t.wait()
        count = 0
        check_duplicated = list()


        for match, is_duplicated in self._matches_handler:
            count+=1
            if is_duplicated: #duplicated
                if match.__str__() in check_duplicated:
                    check_duplicated.remove(match.__str__())
                else:
                    self._matches.add_item(match)
                    check_duplicated.append(match.__str__())
            else:
                self._matches.add_item(match)

        self._matches.close()






class Algorithm3(DataParallelAlgorithm):
    def __init__(self, threadsNum, patterns: Pattern or List[Pattern],
                 eval_mechanism_params: EvaluationMechanismParameters, platform, attributes_dict: dict):
        super().__init__(threadsNum, patterns, eval_mechanism_params, platform)
        self.attributes_dict = attributes_dict
        self.keys_list = list(self.attributes_dict.keys())
        self.groups_num = math.ceil(self._numThreads**(1/len(attributes_dict)))
        self._matches_handler = Stream()


    def eval_algorithm(self, events: InputStream, matches: OutputStream, data_formatter: DataFormatter):
        """
        event = Event(events.first(), data_formatter)
        event_type = event.type
        event_attribute = self.attributes_dict[event_type]
        attribute_val = event.payload[event_attribute]
        print(self.keys_list)
        for key in self.keys_list:
            key_val = event.payload[key]
            if not isinstance(key_val, (int, float)):
                raise Exception("key %s has no numeric value" % (self.key,))
        """
        super().eval_algorithm(events, matches, data_formatter)
        for t in self._threads:
            t.wait()
        self._matches.close()


    def _stream_divide(self):
        print("here")
        file = open("C:/Users/tomer/Desktop/CEPproject/OpenCEP/test/strems.txt", 'w')

        for event_raw in self._events:
            event = Event(event_raw, self._data_formatter)
            event_type = event.type
            event_attribute = self.attributes_dict[event_type]
            attribute_val = event.payload[event_attribute]
            group_index = int(attribute_val % (self.groups_num))
            leg_size = self.groups_num**self.keys_list.index(event_type)
            print(leg_size)
            new_start = (group_index)*leg_size
            jump = leg_size*(self.groups_num-1)+1
            j = new_start

            while j < self._numThreads:
                if j==26:
                    self._events_list[1].add_item(event_raw)
                    print(event_raw)
                self._events_list[j].add_item(event_raw)
                file.write("%s " % j)
                file.write("%s " % event.type)
                file.write("%s\n " % attribute_val)
                file.write("%s " % event_raw)
                file.write("%s\n" % event.payload[event_attribute])
                leg_size-=1
                if leg_size == 0:
                    j+=jump
                    leg_size = self.groups_num ** self.keys_list.index(event_type)
                else:
                    j+=1


        for stream in self._events_list:
            stream.close()

    def _eval_thread(self, thread_id: int, data_formatter: DataFormatter):
        self._trees[thread_id].eval(self._events_list[thread_id], self._matches,self._matches_handler,data_formatter, False)
