from adaptive.optimizer.OptimizerFactory import OptimizerParameters
from adaptive.optimizer.OptimizerTypes import OptimizerTypes
from adaptive.statistics.StatisticsCollectorFactory import StatisticsCollectorParameters
from adaptive.statistics.StatisticsTypes import StatisticsTypes
from plan.multi.MultiPatternTreePlanMergeApproaches import MultiPatternTreePlanMergeApproaches
from plan.multi.local_search.LocalSearchFactory import TabuSearchLocalSearchParameters
from test.testUtils import *
from datetime import timedelta
from condition.Condition import Variable, TrueCondition, BinaryCondition, SimpleCondition
from condition.CompositeCondition import AndCondition
from condition.BaseRelationCondition import EqCondition, GreaterThanCondition, GreaterThanEqCondition, \
    SmallerThanEqCondition, SmallerThanCondition
from base.PatternStructure import AndOperator, SeqOperator, PrimitiveEventStructure, NegationOperator
from base.Pattern import Pattern

LOCAL_EVALUATION_MECHANISM_SETTINGS = \
    TreeBasedEvaluationMechanismParameters(
        optimizer_params=OptimizerParameters(
                                             statistics_collector_params=StatisticsCollectorParameters(
                                                             statistics_types=[StatisticsTypes.ARRIVAL_RATES]),
                                             opt_type=OptimizerTypes.TRIVIAL_OPTIMIZER,
                                             tree_plan_params=TreePlanBuilderParameters(
                                                 builder_type=TreePlanBuilderTypes.TRIVIAL_LEFT_DEEP_TREE,
                                                 cost_model_type=TreeCostModels.INTERMEDIATE_RESULTS_TREE_COST_MODEL,
                                                 tree_plan_merger_type=MultiPatternTreePlanMergeApproaches.TREE_PLAN_LOCAL_SEARCH)),
        storage_params=TreeStorageParameters(sort_storage=False, clean_up_interval=10,
                                             prioritize_sorting_by_timestamp=True),
        local_search_params=TabuSearchLocalSearchParameters(
            neighborhood_vertex_size=2, time_limit=10, steps_threshold=100,
            capacity=10000, neighborhood_size=100))

def localSearchTest(createTestFile=False, eval_mechanism_params=LOCAL_EVALUATION_MECHANISM_SETTINGS,
                          test_name = "FirstMultiPattern"):

    pattern1 = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a")),
        GreaterThanCondition(Variable("a", lambda x: x["Peak Price"]), 135),
        timedelta(minutes=5)
    )
    pattern1.set_statistics(
        {StatisticsTypes.ARRIVAL_RATES: [0.0159, 0.0076]})  # {"AAPL": 460, "LOCM": 219}

    pattern2 = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a"), PrimitiveEventStructure("AMZN", "b"),
                    PrimitiveEventStructure("GOOG", "c")),
        AndCondition(
            GreaterThanCondition(Variable("a", lambda x: x["Opening Price"]),
                                 Variable("b", lambda x: x["Opening Price"])),
            GreaterThanCondition(Variable("a", lambda x: x["Peak Price"]), 135),
            SmallerThanCondition(Variable("b", lambda x: x["Opening Price"]),
                                 Variable("c", lambda x: x["Opening Price"]))),
        timedelta(minutes=5)
    )
    pattern2.set_statistics(
        {StatisticsTypes.ARRIVAL_RATES: [0.0159, 0.0076, 0.0159]})  # {"AAPL": 460, "LOCM": 219}

    runMultiTest("Test1", [pattern1, pattern2], createTestFile, eval_mechanism_params)

# todo: tests pass
def localSearchTest2(createTestFile=False, eval_mechanism_params=LOCAL_EVALUATION_MECHANISM_SETTINGS,
                          test_name = "FirstMultiPattern"):

    pattern1 = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a"), PrimitiveEventStructure("AMZN", "b")),
        GreaterThanCondition(Variable("a", lambda x: x["Peak Price"]), 135),
        timedelta(minutes=5)
    )
    pattern1.set_statistics(
        {StatisticsTypes.ARRIVAL_RATES: [0.0159, 0.0076]})  # {"AAPL": 460, "LOCM": 219}

    pattern2 = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a"), PrimitiveEventStructure("AMZN", "b"), PrimitiveEventStructure("GOOG", "c")),
        AndCondition(GreaterThanCondition(Variable("a", lambda x: x["Peak Price"]), 135),
                     SmallerThanCondition(Variable("b", lambda x: x["Opening Price"]),
                                 Variable("c", lambda x: x["Opening Price"]))),
        timedelta(minutes=5)
    )
    pattern2.set_statistics(
        {StatisticsTypes.ARRIVAL_RATES: [0.0159, 0.0076, 0.0159]})  # {"AAPL": 460, "LOCM": 219}

    runMultiTest("TestCheck", [pattern1, pattern2], createTestFile, eval_mechanism_params)

subtree_sharing_eval_mechanism_params = TreeBasedEvaluationMechanismParameters(
    optimizer_params=OptimizerParameters(opt_type=OptimizerTypes.TRIVIAL_OPTIMIZER,
                                         tree_plan_params=
                                         TreePlanBuilderParameters(builder_type=TreePlanBuilderTypes.TRIVIAL_LEFT_DEEP_TREE,
                              cost_model_type=TreeCostModels.INTERMEDIATE_RESULTS_TREE_COST_MODEL,
                              tree_plan_merger_type=MultiPatternTreePlanMergeApproaches.TREE_PLAN_SUBTREES_UNION)),
    storage_params=TreeStorageParameters(sort_storage=False, clean_up_interval=10, prioritize_sorting_by_timestamp=True))
def localSearchTest3(createTestFile=False, eval_mechanism_params=LOCAL_EVALUATION_MECHANISM_SETTINGS,
                          test_name = "FirstMultiPattern"):

    pattern1 = Pattern(
        SeqOperator(PrimitiveEventStructure("MSFT", "d"), PrimitiveEventStructure("AAPL", "a")),
        GreaterThanCondition(Variable("a", lambda x: x["Peak Price"]), 135),
        timedelta(minutes=5)
    )
    pattern1.set_statistics(
        {StatisticsTypes.ARRIVAL_RATES: [0.0076, 0.0159]})  # {"AAPL": 460, "LOCM": 219}

    pattern2 = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a"), PrimitiveEventStructure("AMZN", "b"), PrimitiveEventStructure("GOOG", "c")),
        AndCondition(GreaterThanCondition(Variable("a", lambda x: x["Peak Price"]), 135),
                     SmallerThanCondition(Variable("b", lambda x: x["Opening Price"]),
                                 Variable("c", lambda x: x["Opening Price"]))),
        timedelta(minutes=5)
    )
    pattern2.set_statistics(
        {StatisticsTypes.ARRIVAL_RATES: [0.0159, 0.0076, 0.0159]})  # {"AAPL": 460, "LOCM": 219}

    runMultiTest("abcccc", [pattern1, pattern2], createTestFile, subtree_sharing_eval_mechanism_params)


def localSearchTest4(createTestFile=False, eval_mechanism_params=LOCAL_EVALUATION_MECHANISM_SETTINGS,
                          test_name = "FirstMultiPattern"):

    pattern1 = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a")),
        GreaterThanCondition(Variable("a", lambda x: x["Peak Price"]), 135),
        timedelta(minutes=5)
    )
    pattern1.set_statistics(
        {StatisticsTypes.ARRIVAL_RATES: [0.0076, 0.0159]})  # {"AAPL": 460, "LOCM": 219}

    pattern2 = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a"), PrimitiveEventStructure("AMZN", "b"), PrimitiveEventStructure("GOOG", "c")),
        AndCondition(GreaterThanCondition(Variable("a", lambda x: x["Peak Price"]), 135),
                     SmallerThanCondition(Variable("b", lambda x: x["Opening Price"]),
                                 Variable("c", lambda x: x["Opening Price"]))),
        timedelta(minutes=5)
    )
    pattern2.set_statistics(
        {StatisticsTypes.ARRIVAL_RATES: [0.0159, 0.0076, 0.0159]})  # {"AAPL": 460, "LOCM": 219}

    runMultiTest("APAPAPAP", [pattern1, pattern2], createTestFile, eval_mechanism_params)