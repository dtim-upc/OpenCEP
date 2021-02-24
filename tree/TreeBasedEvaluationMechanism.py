from typing import Dict
from base.DataFormatter import DataFormatter
from base.Event import Event
from misc.Statistics import calculate_selectivity_matrix
from plan.TreePlan import TreePlan
from stream.Stream import InputStream, OutputStream
from misc.Utils import *
from tree.nodes.LeafNode import LeafNode
from tree.PatternMatchStorage import TreeStorageParameters
from evaluation.EvaluationMechanism import EvaluationMechanism
from misc.ConsumptionPolicy import *
from plan.multi.MultiPatternEvaluationParameters import MultiPatternEvaluationParameters
from tree.MultiPatternTree import MultiPatternTree
from statistics_collector import StatisticsCollector
from tree.Tree import Tree
from datetime import timedelta
from optimizer import Optimizer


class TreeBasedEvaluationMechanism(EvaluationMechanism):
    """
    An implementation of the tree-based evaluation mechanism.
    """

    def __init__(self, pattern_to_tree_plan_map: Dict[Pattern, TreePlan],
                 storage_params: TreeStorageParameters,
                 statistics_collector: StatisticsCollector,
                 optimizer: Optimizer,
                 statistics_update_time_window: timedelta,
                 multi_pattern_eval_params: MultiPatternEvaluationParameters = MultiPatternEvaluationParameters()):

        self.__is_multi_pattern_mode = len(pattern_to_tree_plan_map) > 1
        if self.__is_multi_pattern_mode:
            self._tree = MultiPatternTree(pattern_to_tree_plan_map, storage_params, multi_pattern_eval_params)
        else:
            self._tree = Tree(list(pattern_to_tree_plan_map.values())[0],
                              list(pattern_to_tree_plan_map)[0], storage_params)

        self.__storage_params = storage_params
        self.__statistics_collector = statistics_collector
        self.__optimizer = optimizer

        self._event_types_listeners = {}
        self.__statistics_update_time_window = statistics_update_time_window

        # The remainder of the initialization process is only relevant for the freeze map feature. This feature can
        # only be enabled in single-pattern mode.
        self._pattern = list(pattern_to_tree_plan_map)[0] if not self.__is_multi_pattern_mode else None
        self.__freeze_map = {}
        self.__active_freezers = []

        if not self.__is_multi_pattern_mode and self._pattern.consumption_policy is not None and \
                self._pattern.consumption_policy.freeze_names is not None:
            self.__init_freeze_map()

    def eval(self, events: InputStream, matches: OutputStream, data_formatter: DataFormatter):
        """
        Activates the tree evaluation mechanism on the input event stream and reports all found pattern matches to the
        given output stream.
        """
        self._event_types_listeners = self._register_event_listeners(self._tree)
        statistics_update_start_time = None
        count = 0

        for raw_event in events:
            event = Event(raw_event, data_formatter)
            if event.type not in self._event_types_listeners.keys():
                continue
            self.__remove_expired_freezers(event)
            count += 1
            if not self.__is_multi_pattern_mode:  # Note: multi-pattern does not yet support adaptive-CEP,
                # this condition is necessary for the multi-pattern tests and nothing more
                # TODO: evaluation mechanism factory needs to support multi-pattern mode
                self.__statistics_collector.event_handler(event)
                if not statistics_update_start_time or event.timestamp - statistics_update_start_time >= self.__statistics_update_time_window:
                    if self._is_need_new_statistics():
                        new_statistics = self.__statistics_collector.get_statistics()
                        if self.__optimizer.is_need_optimize(new_statistics, self._pattern):
                            new_tree_plan = self.__optimizer.build_new_tree_plan(new_statistics, self._pattern)
                            new_tree = Tree(new_tree_plan, self._pattern, self.__storage_params)
                            self._tree_update(new_tree, event.timestamp)
                    # re-initialize statistics window start time
                    statistics_update_start_time = event.timestamp

            self._play_new_event_on_tree(event, matches)
            self._get_matches(matches)
            # print(count)

        self._get_last_matches(matches)
        matches.close()

    def _get_last_matches(self, matches):
        raise NotImplementedError("Must override")

    @staticmethod
    def _collect_pending_matches(tree, matches):
        """
        Now that we finished the input stream, if there were some pending matches somewhere in the tree, we will
        collect them now
        """
        for match in tree.get_last_matches():
            matches.add_item(match)

    def _play_new_event(self, event: Event, event_types_listeners):
        """
        Lets the tree handle the event
        """
        for leaf in event_types_listeners[event.type]:
            if self.__should_ignore_events_on_leaf(leaf, event_types_listeners):
                continue
            self.__try_register_freezer(event, leaf)
            leaf.handle_event(event)

    def _get_matches(self, matches: OutputStream):
        for match in self._tree.get_matches():
            matches.add_item(match)
            self._remove_matched_freezers(match.events)

    def _tree_update(self, new_tree: Tree, event: Event):
        raise NotImplementedError("Must override")

    def _is_need_new_statistics(self):
        raise NotImplementedError("Must override")

    def _play_new_event_on_tree(self, event: Event, matches: OutputStream):
        raise NotImplementedError("Must override")

    @staticmethod
    def _register_event_listeners(tree: Tree):
        """
        Given tree, register leaf listeners for event types.
        """
        event_types_listeners = {}
        for leaf in tree.get_leaves():
            event_type = leaf.get_event_type()
            if event_type in event_types_listeners.keys():
                event_types_listeners[event_type].append(leaf)
            else:
                event_types_listeners[event_type] = [leaf]

        return event_types_listeners

    def __init_freeze_map(self):
        """
        For each event type specified by the user to be a 'freezer', that is, an event type whose appearance blocks
        initialization of new sequences until it is either matched or expires, this method calculates the list of
        leaves to be disabled.
        """
        sequences = self._pattern.extract_flat_sequences()
        for freezer_event_name in self._pattern.consumption_policy.freeze_names:
            current_event_name_set = set()
            for sequence in sequences:
                if freezer_event_name not in sequence:
                    continue
                for name in sequence:
                    current_event_name_set.add(name)
                    if name == freezer_event_name:
                        break
            if len(current_event_name_set) > 0:
                self.__freeze_map[freezer_event_name] = current_event_name_set

    def __should_ignore_events_on_leaf(self, leaf: LeafNode, event_types_listeners):
        """
        If the 'freeze' consumption policy is enabled, checks whether the given event should be dropped based on it.
        """
        if len(self.__freeze_map) == 0:
            # freeze option disabled
            return False
        for freezer in self.__active_freezers:
            for freezer_leaf in event_types_listeners[freezer.type]:
                if freezer_leaf.get_event_name() not in self.__freeze_map:
                    continue
                if leaf.get_event_name() in self.__freeze_map[freezer_leaf.get_event_name()]:
                    return True
        return False

    def __try_register_freezer(self, event: Event, leaf: LeafNode):
        """
        Check whether the current event is a freezer event, and, if positive, register it.
        """
        if leaf.get_event_name() in self.__freeze_map.keys():
            self.__active_freezers.append(event)

    def _remove_matched_freezers(self, match_events: List[Event]):
        """
        Removes the freezers that have been matched.
        """
        if len(self.__freeze_map) == 0:
            # freeze option disabled
            return False
        self.__active_freezers = [freezer for freezer in self.__active_freezers if freezer not in match_events]

    def __remove_expired_freezers(self, event: Event):
        """
        Removes the freezers that have been expired.
        """

        if len(self.__freeze_map) == 0:
            # freeze option disabled
            return False
        self.__active_freezers = [freezer for freezer in self.__active_freezers
                                  if event.timestamp - freezer.timestamp <= self._pattern.window]

    def get_structure_summary(self):
        return self._tree.get_structure_summary()

    def __repr__(self):
        return self.get_structure_summary()





